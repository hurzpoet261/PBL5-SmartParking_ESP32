import asyncio
import copy
import re
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from pydantic import ValidationError
from fastapi import HTTPException


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.controllers import package_controller
from app.controllers import registration_controller
from app.controllers import rfid_controller as controller
from app.database.mongodb import MongoDB
from app.models.package import PackageCreate, PackageType


def matches(document, query):
    for key, expected in query.items():
        if key == "$or":
            if not any(matches(document, condition) for condition in expected):
                return False
            continue

        actual = document.get(key)
        if isinstance(expected, dict):
            for operator, operand in expected.items():
                if operator == "$in" and actual not in operand:
                    return False
                if operator == "$gt" and not (actual is not None and actual > operand):
                    return False
                if operator == "$ne":
                    if isinstance(actual, list) and operand in actual:
                        return False
                    if not isinstance(actual, list) and actual == operand:
                        return False
                if operator == "$exists" and (key in document) != operand:
                    return False
                if operator == "$regex":
                    flags = re.IGNORECASE if expected.get("$options") == "i" else 0
                    if actual is None or not re.search(operand, str(actual), flags):
                        return False
                if operator == "$options":
                    continue
            continue

        if actual != expected:
            return False
    return True


class Result:
    def __init__(self, deleted_count=0):
        self.deleted_count = deleted_count


def apply_update(document, update):
    document.update(copy.deepcopy(update.get("$set", {})))
    for key, increment in update.get("$inc", {}).items():
        document[key] = document.get(key, 0) + increment
    for key, value in update.get("$addToSet", {}).items():
        document.setdefault(key, [])
        if value not in document[key]:
            document[key].append(copy.deepcopy(value))


class FakeCollection:
    def __init__(self, name, documents=None, insert_delay=0, insert_error=None):
        self.name = name
        self.documents = list(documents or [])
        self.insert_delay = insert_delay
        self.insert_error = insert_error
        self.lock = asyncio.Lock()

    def _enforce_unique(self, document):
        if self.name == "sessions":
            for existing in self.documents:
                if (
                    document.get("status") == "in_progress"
                    and existing.get("status") == "in_progress"
                    and (
                        existing.get("card_uid") == document.get("card_uid")
                        or existing.get("vehicle_id") == document.get("vehicle_id")
                    )
                ):
                    raise DuplicateKeyError("duplicate active session")
                if (
                    document.get("checkin_request_id")
                    and existing.get("checkin_request_id") == document.get("checkin_request_id")
                ):
                    raise DuplicateKeyError("duplicate checkin request")

        if self.name == "transactions" and document.get("parking_fee_session_id"):
            for existing in self.documents:
                if existing.get("parking_fee_session_id") == document["parking_fee_session_id"]:
                    raise DuplicateKeyError("duplicate parking fee transaction")

    async def find_one(self, query, sort=None, **kwargs):
        del kwargs
        await asyncio.sleep(0)
        async with self.lock:
            documents = [item for item in self.documents if matches(item, query)]
            if sort:
                key, direction = sort[0]
                documents.sort(key=lambda item: item.get(key), reverse=direction < 0)
            return copy.deepcopy(documents[0]) if documents else None

    async def insert_one(self, document, **kwargs):
        del kwargs
        if self.insert_delay:
            await asyncio.sleep(self.insert_delay)
        async with self.lock:
            if self.insert_error:
                raise self.insert_error
            self._enforce_unique(document)
            self.documents.append(copy.deepcopy(document))
        return Result()

    async def update_one(self, query, update, upsert=False, **kwargs):
        del kwargs
        async with self.lock:
            for document in self.documents:
                if matches(document, query):
                    apply_update(document, update)
                    return Result()

            if upsert:
                document = copy.deepcopy(query)
                document.update(copy.deepcopy(update.get("$setOnInsert", {})))
                self._enforce_unique(document)
                self.documents.append(document)
        return Result()

    async def find_one_and_update(self, query, update, return_document=None, **kwargs):
        del kwargs
        async with self.lock:
            for document in self.documents:
                if matches(document, query):
                    before = copy.deepcopy(document)
                    apply_update(document, update)
                    if return_document == ReturnDocument.AFTER:
                        return copy.deepcopy(document)
                    return before
        return None

    async def delete_many(self, query):
        async with self.lock:
            before = len(self.documents)
            self.documents = [item for item in self.documents if not matches(item, query)]
            return Result(before - len(self.documents))

    async def delete_one(self, query):
        async with self.lock:
            for index, document in enumerate(self.documents):
                if matches(document, query):
                    del self.documents[index]
                    return Result(1)
        return Result()


class FakeDatabase:
    def __init__(self, slots=1, session_insert_delay=0):
        self.pending_scans = FakeCollection("pending_scans")
        self.rfid_cards = FakeCollection("rfid_cards")
        self.customers = FakeCollection("customers")
        self.vehicles = FakeCollection("vehicles")
        self.sessions = FakeCollection("sessions", insert_delay=session_insert_delay)
        self.parking_slots = FakeCollection(
            "parking_slots",
            [
                {
                    "slot_id": f"A{index:02d}",
                    "status": "available",
                    "vehicle_id": None,
                    "session_id": None,
                }
                for index in range(1, slots + 1)
            ],
        )
        self.packages = FakeCollection("packages")
        self.transactions = FakeCollection("transactions")

    def __getitem__(self, collection_name):
        return getattr(self, collection_name)

    def add_vehicle(self, suffix):
        customer_id = f"C{suffix}"
        vehicle_id = f"V{suffix}"
        card_uid = f"card-{suffix}"
        plate_number = f"43A{int(suffix):05d}"
        self.customers.documents.append(
            {"customer_id": customer_id, "name": f"Customer {suffix}", "is_active": True}
        )
        self.vehicles.documents.append(
            {
                "vehicle_id": vehicle_id,
                "customer_id": customer_id,
                "plate_number": plate_number,
                "vehicle_type": "motorbike",
                "is_active": True,
            }
        )
        self.rfid_cards.documents.append(
            {
                "card_uid": card_uid,
                "customer_id": customer_id,
                "vehicle_id": vehicle_id,
                "status": "active",
            }
        )
        return card_uid, plate_number


class FakeIdGenerator:
    def __init__(self):
        self.values = {}
        self.lock = asyncio.Lock()

    async def generate(self, db, collection_name, prefix, *, session=None):
        del db, session
        async with self.lock:
            self.values[collection_name] = self.values.get(collection_name, 0) + 1
            return f"{prefix}{self.values[collection_name]:06d}"


class IndexCollection:
    def __init__(self):
        self.calls = []

    async def create_index(self, keys, **kwargs):
        self.calls.append((keys, kwargs))


class IndexDatabase:
    def __init__(self):
        self.sessions = IndexCollection()
        self.parking_slots = IndexCollection()
        self.packages = IndexCollection()
        self.transactions = IndexCollection()


class MongoIndexTests(unittest.IsolatedAsyncioTestCase):
    async def test_integrity_indexes_cover_active_sessions_slots_and_fees(self):
        original_db = MongoDB.db
        db = IndexDatabase()
        MongoDB.db = db
        try:
            await MongoDB.ensure_indexes()
        finally:
            MongoDB.db = original_db

        session_indexes = {options["name"]: (keys, options) for keys, options in db.sessions.calls}
        transaction_indexes = {
            options["name"]: (keys, options) for keys, options in db.transactions.calls
        }
        self.assertEqual(
            session_indexes["uniq_active_session_card"][0],
            [("card_uid", 1)],
        )
        self.assertEqual(
            session_indexes["uniq_active_session_vehicle"][0],
            [("vehicle_id", 1)],
        )
        self.assertTrue(session_indexes["uniq_active_session_card"][1]["unique"])
        self.assertEqual(
            session_indexes["uniq_active_session_card"][1]["partialFilterExpression"],
            {"status": "in_progress"},
        )
        self.assertTrue(transaction_indexes["uniq_parking_fee_session"][1]["unique"])
        self.assertTrue(transaction_indexes["uniq_parking_fee_session"][1]["sparse"])
        self.assertEqual(len(db.parking_slots.calls), 1)
        self.assertEqual(len(db.packages.calls), 1)


class PackageControllerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_generate_id = package_controller.generate_id
        self.ids = FakeIdGenerator()
        package_controller.generate_id = self.ids.generate

    async def asyncTearDown(self):
        package_controller.generate_id = self.original_generate_id

    async def test_create_package_rejects_vehicle_from_other_customer(self):
        db = FakeDatabase()
        db.add_vehicle("1")
        db.add_vehicle("2")

        with self.assertRaises(HTTPException):
            await package_controller.create_package(
                PackageCreate(
                    customer_id="C1",
                    vehicle_id="V2",
                    package_type=PackageType.MONTHLY,
                ),
                db,
            )

    async def test_create_per_use_package_is_finite_and_priced(self):
        db = FakeDatabase()
        db.add_vehicle("1")

        response = await package_controller.create_package(
            PackageCreate(
                customer_id="C1",
                vehicle_id="V1",
                package_type=PackageType.PER_USE,
                remaining_uses=3,
            ),
            db,
        )

        package = response["data"]
        self.assertEqual(package["remaining_uses"], 3)
        self.assertEqual(package["price"], 15000.0)
        self.assertEqual(package["consumed_session_ids"], [])
        self.assertEqual(db.transactions.documents[0]["amount"], 15000.0)


class FullRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_generate_id = registration_controller.generate_id
        self.ids = FakeIdGenerator()
        registration_controller.generate_id = self.ids.generate

    async def asyncTearDown(self):
        registration_controller.generate_id = self.original_generate_id

    def payload(self, card_uid="0xdeadbeef", package_type=PackageType.MONTHLY):
        package = None
        if package_type:
            package = registration_controller.RegistrationPackage(
                package_type=package_type,
            )
        return registration_controller.FullRegistrationRequest(
            customer={
                "name": "Registration Test",
                "phone": "0900000000",
                "customer_type": "walk_in",
            },
            vehicle={
                "plate_number": "43A-123.45",
                "vehicle_type": "motorbike",
            },
            card_uid=card_uid,
            package=package,
        )

    async def test_full_registration_creates_all_records(self):
        db = FakeDatabase()

        response = await registration_controller.create_full_registration(
            self.payload(),
            db,
        )

        self.assertTrue(response["success"])
        self.assertEqual(len(db.customers.documents), 1)
        self.assertEqual(len(db.vehicles.documents), 1)
        self.assertEqual(db.vehicles.documents[0]["normalized_plate"], "43A12345")
        self.assertEqual(len(db.rfid_cards.documents), 1)
        self.assertEqual(db.rfid_cards.documents[0]["card_uid"], "0xdeadbeef")
        self.assertEqual(len(db.packages.documents), 1)
        self.assertEqual(len(db.transactions.documents), 1)

    async def test_full_registration_rejects_duplicate_uid_without_writes(self):
        db = FakeDatabase()
        db.rfid_cards.documents.append({"card_uid": "DEADBEEF"})

        with self.assertRaises(HTTPException) as error:
            await registration_controller.create_full_registration(
                self.payload(),
                db,
            )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(db.customers.documents), 0)
        self.assertEqual(len(db.vehicles.documents), 0)
        self.assertEqual(len(db.rfid_cards.documents), 1)

    async def test_full_registration_rejects_legacy_formatted_duplicate_plate(self):
        db = FakeDatabase()
        db.vehicles.documents.append({"vehicle_id": "V-legacy", "plate_number": "43A-123.45"})

        with self.assertRaises(HTTPException) as error:
            await registration_controller.create_full_registration(
                self.payload(card_uid="0xabcdef12"),
                db,
            )

        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(db.customers.documents), 0)
        self.assertEqual(len(db.vehicles.documents), 1)
        self.assertEqual(len(db.rfid_cards.documents), 0)

    async def test_package_insert_failure_rolls_back_customer_vehicle_and_card(self):
        db = FakeDatabase()
        db.packages = FakeCollection("packages", insert_error=RuntimeError("package failure"))

        with self.assertRaises(RuntimeError):
            await registration_controller.create_full_registration(
                self.payload(),
                db,
            )

        self.assertEqual(db.customers.documents, [])
        self.assertEqual(db.vehicles.documents, [])
        self.assertEqual(db.rfid_cards.documents, [])
        self.assertEqual(db.packages.documents, [])
        self.assertEqual(db.transactions.documents, [])

    async def test_full_registration_uses_transaction_when_client_supports_it(self):
        class TransactionContext:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, traceback):
                return False

        class ClientSession(TransactionContext):
            def __init__(self):
                self.transaction_started = False

            def start_transaction(self):
                self.transaction_started = True
                return TransactionContext()

        class Client:
            def __init__(self):
                self.session = ClientSession()

            async def start_session(self):
                return self.session

        db = FakeDatabase()
        db.client = Client()

        response = await registration_controller.create_full_registration(
            self.payload(package_type=None),
            db,
        )

        self.assertTrue(response["success"])
        self.assertTrue(db.client.session.transaction_started)

    def test_compatibility_card_schema_rejects_invalid_uid(self):
        with self.assertRaises(ValidationError):
            registration_controller.RegisterCardRequest(
                card_uid="not-a-uid",
                customer_id="C1",
                vehicle_id="V1",
            )


class PackageSchemaTests(unittest.TestCase):
    def test_per_use_requires_positive_remaining_uses(self):
        with self.assertRaises(ValidationError):
            PackageCreate(
                customer_id="C1",
                vehicle_id="V1",
                package_type=PackageType.PER_USE,
            )
        with self.assertRaises(ValidationError):
            PackageCreate(
                customer_id="C1",
                vehicle_id="V1",
                package_type=PackageType.PER_USE,
                remaining_uses=0,
            )

    def test_unlimited_package_rejects_remaining_uses(self):
        with self.assertRaises(ValidationError):
            PackageCreate(
                customer_id="C1",
                vehicle_id="V1",
                package_type=PackageType.MONTHLY,
                remaining_uses=10,
            )


class RFIDAtomicFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_generate_id = controller.generate_id
        self.ids = FakeIdGenerator()
        controller.generate_id = self.ids.generate

    async def asyncTearDown(self):
        controller.generate_id = self.original_generate_id

    def request(self, card_uid, plate_number, batch_id, gate_id=1):
        return controller.RFIDScanWithOCRRequest(
            card_uid=card_uid,
            gate_id=gate_id,
            device_id="esp32-gate-01",
            ocr_plate=plate_number,
            capture_batch_id=batch_id,
        )

    async def test_normal_checkin_and_checkout(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")

        checkin = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-in"),
            db,
        )
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)
        checkout = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertEqual(checkin["action"], "checkin")
        self.assertEqual(checkout["action"], "checkout")
        self.assertEqual(checkout["parking_fee"], 5000.0)
        self.assertEqual(db.parking_slots.documents[0]["status"], "available")
        self.assertEqual(len(db.transactions.documents), 1)

    async def test_full_parking_lot_returns_clear_denial(self):
        db = FakeDatabase(slots=0)
        card_uid, plate = db.add_vehicle("1")

        response = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-full"),
            db,
        )

        self.assertFalse(response["allowed"])
        self.assertEqual(response["reason_code"], "NO_AVAILABLE_SLOT")

    async def test_repeated_checkout_is_idempotent(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        await controller.rfid_scan_with_ocr(self.request(card_uid, plate, "batch-in"), db)
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)

        first = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )
        repeated = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertFalse(first["idempotent"])
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(len(db.transactions.documents), 1)
        self.assertEqual(len(db.sessions.documents), 1)

    async def test_repeated_checkout_repairs_slot_and_missing_transaction(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        db.sessions.documents.append(
            {
                "session_id": "S000001",
                "card_uid": card_uid,
                "customer_id": "C1",
                "vehicle_id": "V1",
                "slot_id": "A01",
                "entry_time": datetime.now() - timedelta(minutes=10),
                "exit_time": datetime.now(),
                "status": "completed",
                "parking_fee": 5000.0,
                "checkout_request_id": "batch-out",
            }
        )
        db.parking_slots.documents[0].update(
            {
                "status": "occupied",
                "vehicle_id": "V1",
                "session_id": "S000001",
            }
        )

        repeated = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertTrue(repeated["idempotent"])
        self.assertEqual(db.parking_slots.documents[0]["status"], "available")
        self.assertEqual(len(db.transactions.documents), 1)
        self.assertEqual(db.transactions.documents[0]["session_id"], "S000001")

    async def test_concurrent_vehicles_never_claim_same_slot(self):
        db = FakeDatabase(slots=2, session_insert_delay=0.01)
        first_card, first_plate = db.add_vehicle("1")
        second_card, second_plate = db.add_vehicle("2")

        responses = await asyncio.gather(
            controller.rfid_scan_with_ocr(
                self.request(first_card, first_plate, "batch-first"),
                db,
            ),
            controller.rfid_scan_with_ocr(
                self.request(second_card, second_plate, "batch-second"),
                db,
            ),
        )

        self.assertTrue(all(response["allowed"] for response in responses))
        self.assertEqual({response["slot_id"] for response in responses}, {"A01", "A02"})

    async def test_concurrent_same_vehicle_creates_one_active_session(self):
        db = FakeDatabase(slots=2, session_insert_delay=0.01)
        card_uid, plate = db.add_vehicle("1")

        responses = await asyncio.gather(
            controller.checkin_vehicle(
                db,
                request=self.request(card_uid, plate, "batch-first"),
                card=db.rfid_cards.documents[0],
                customer=db.customers.documents[0],
                vehicle=db.vehicles.documents[0],
                now=datetime.now(),
            ),
            controller.checkin_vehicle(
                db,
                request=self.request(card_uid, plate, "batch-second"),
                card=db.rfid_cards.documents[0],
                customer=db.customers.documents[0],
                vehicle=db.vehicles.documents[0],
                now=datetime.now(),
            ),
        )

        active_sessions = [
            item for item in db.sessions.documents if item["status"] == "in_progress"
        ]
        occupied_slots = [
            item for item in db.parking_slots.documents if item["status"] == "occupied"
        ]
        self.assertEqual(len(active_sessions), 1)
        self.assertEqual(len(occupied_slots), 1)
        self.assertEqual(sum(response["allowed"] for response in responses), 1)

    async def test_legacy_fee_transaction_is_preserved_and_reused(self):
        db = FakeDatabase()
        db.transactions.documents.append(
            {
                "transaction_id": "T000001",
                "customer_id": "C1",
                "transaction_type": "parking_fee",
                "amount": 5000.0,
                "session_id": "S000001",
            }
        )
        session = {
            "session_id": "S000001",
            "customer_id": "C1",
            "entry_time": datetime.now() - timedelta(minutes=10),
            "exit_time": datetime.now(),
            "parking_fee": 5000.0,
        }

        transaction = await controller.ensure_parking_fee_transaction(
            db,
            completed_session=session,
            now=datetime.now(),
        )

        self.assertEqual(transaction["transaction_id"], "T000001")
        self.assertEqual(len(db.transactions.documents), 1)

    async def test_monthly_package_for_registered_vehicle_is_applied(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        await controller.rfid_scan_with_ocr(self.request(card_uid, plate, "batch-in"), db)
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)
        db.packages.documents.append(
            {
                "package_id": "P000001",
                "customer_id": "C1",
                "vehicle_id": "V1",
                "vehicle_type": "motorbike",
                "package_type": "monthly",
                "status": "active",
                "expire_date": datetime.now() + timedelta(days=10),
            }
        )

        checkout = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertEqual(checkout["parking_fee"], 0.0)
        self.assertTrue(checkout["fee_breakdown"]["package_applied"])
        self.assertEqual(checkout["fee_breakdown"]["package_id"], "P000001")
        self.assertEqual(db.transactions.documents[0]["fee_breakdown"]["final_fee"], 0.0)

    async def test_package_for_other_vehicle_is_not_applied(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        db.add_vehicle("2")
        await controller.rfid_scan_with_ocr(self.request(card_uid, plate, "batch-in"), db)
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)
        db.packages.documents.append(
            {
                "package_id": "P000001",
                "customer_id": "C1",
                "vehicle_id": "V2",
                "package_type": "monthly",
                "status": "active",
                "expire_date": datetime.now() + timedelta(days=10),
            }
        )

        checkout = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertEqual(checkout["parking_fee"], 5000.0)
        self.assertFalse(checkout["fee_breakdown"]["package_applied"])

    async def test_expired_package_is_not_applied(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        await controller.rfid_scan_with_ocr(self.request(card_uid, plate, "batch-in"), db)
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)
        db.packages.documents.append(
            {
                "package_id": "P000001",
                "customer_id": "C1",
                "vehicle_id": "V1",
                "package_type": "monthly",
                "status": "active",
                "expire_date": datetime.now() - timedelta(seconds=1),
            }
        )

        checkout = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertEqual(checkout["parking_fee"], 5000.0)
        self.assertFalse(checkout["fee_breakdown"]["package_applied"])

    async def test_package_for_other_vehicle_type_is_not_applied(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        await controller.rfid_scan_with_ocr(self.request(card_uid, plate, "batch-in"), db)
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)
        db.packages.documents.append(
            {
                "package_id": "P000001",
                "customer_id": "C1",
                "vehicle_id": "V1",
                "vehicle_type": "car",
                "package_type": "monthly",
                "status": "active",
                "expire_date": datetime.now() + timedelta(days=10),
            }
        )

        checkout = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertEqual(checkout["parking_fee"], 5000.0)
        self.assertFalse(checkout["fee_breakdown"]["package_applied"])

    async def test_per_use_package_consumes_one_use_atomically(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        await controller.rfid_scan_with_ocr(self.request(card_uid, plate, "batch-in"), db)
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)
        db.packages.documents.append(
            {
                "package_id": "P000001",
                "customer_id": "C1",
                "vehicle_id": "V1",
                "package_type": "per_use",
                "remaining_uses": 2,
                "consumed_session_ids": [],
                "status": "active",
                "expire_date": datetime.now() + timedelta(days=10),
            }
        )

        first = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )
        repeated = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertEqual(first["parking_fee"], 0.0)
        self.assertTrue(first["fee_breakdown"]["package_applied"])
        self.assertEqual(first["fee_breakdown"]["remaining_uses_after"], 1)
        self.assertEqual(db.packages.documents[0]["remaining_uses"], 1)
        self.assertEqual(db.packages.documents[0]["consumed_session_ids"], ["S000001"])
        self.assertTrue(repeated["idempotent"])
        self.assertEqual(db.packages.documents[0]["remaining_uses"], 1)

    async def test_exhausted_per_use_package_does_not_waive_fee(self):
        db = FakeDatabase()
        card_uid, plate = db.add_vehicle("1")
        await controller.rfid_scan_with_ocr(self.request(card_uid, plate, "batch-in"), db)
        db.sessions.documents[0]["entry_time"] = datetime.now() - timedelta(minutes=10)
        db.packages.documents.append(
            {
                "package_id": "P000001",
                "customer_id": "C1",
                "vehicle_id": "V1",
                "package_type": "per_use",
                "remaining_uses": 0,
                "consumed_session_ids": [],
                "status": "active",
                "expire_date": datetime.now() + timedelta(days=10),
            }
        )

        checkout = await controller.rfid_scan_with_ocr(
            self.request(card_uid, plate, "batch-out", gate_id=2),
            db,
        )

        self.assertEqual(checkout["parking_fee"], 5000.0)
        self.assertFalse(checkout["fee_breakdown"]["package_applied"])
        self.assertEqual(db.packages.documents[0]["remaining_uses"], 0)

    async def test_concurrent_fee_finalizers_consume_per_use_once(self):
        db = FakeDatabase()
        db.add_vehicle("1")
        completed_session = {
            "session_id": "S000001",
            "card_uid": "card-1",
            "customer_id": "C1",
            "vehicle_id": "V1",
            "slot_id": "A01",
            "entry_time": datetime.now() - timedelta(minutes=10),
            "exit_time": datetime.now(),
            "status": "completed",
            "parking_fee": 5000.0,
        }
        db.sessions.documents.append(copy.deepcopy(completed_session))
        db.packages.documents.append(
            {
                "package_id": "P000001",
                "customer_id": "C1",
                "vehicle_id": "V1",
                "vehicle_type": "motorbike",
                "package_type": "per_use",
                "remaining_uses": 2,
                "consumed_session_ids": [],
                "status": "active",
                "expire_date": datetime.now() + timedelta(days=10),
            }
        )

        await asyncio.gather(
            controller.finalize_session_fee(
                db,
                completed_session=copy.deepcopy(completed_session),
                vehicle=db.vehicles.documents[0],
            ),
            controller.finalize_session_fee(
                db,
                completed_session=copy.deepcopy(completed_session),
                vehicle=db.vehicles.documents[0],
            ),
        )

        self.assertEqual(db.packages.documents[0]["remaining_uses"], 1)
        self.assertEqual(db.packages.documents[0]["consumed_session_ids"], ["S000001"])
        self.assertEqual(db.sessions.documents[0]["fee_breakdown"]["final_fee"], 0.0)

    def test_compatibility_fee_wrapper_does_not_waive_unvalidated_package(self):
        entry_time = datetime.now() - timedelta(minutes=10)
        exit_time = datetime.now()

        fee = controller.FeeCalculator.calculate_parking_fee(
            entry_time,
            exit_time,
            "per_use",
        )

        self.assertEqual(fee, 5000.0)


if __name__ == "__main__":
    unittest.main()
