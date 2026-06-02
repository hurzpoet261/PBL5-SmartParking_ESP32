import asyncio
import copy
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.controllers import rfid_controller as controller
from app.database.mongodb import MongoDB


def matches(document, query):
    for key, expected in query.items():
        if key == "$or":
            if not any(matches(document, condition) for condition in expected):
                return False
            continue

        actual = document.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and actual not in expected["$in"]:
                return False
            if "$gt" in expected and not (actual is not None and actual > expected["$gt"]):
                return False
            continue

        if actual != expected:
            return False
    return True


class Result:
    def __init__(self, deleted_count=0):
        self.deleted_count = deleted_count


class FakeCollection:
    def __init__(self, name, documents=None, insert_delay=0):
        self.name = name
        self.documents = list(documents or [])
        self.insert_delay = insert_delay
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

    async def find_one(self, query, sort=None):
        await asyncio.sleep(0)
        async with self.lock:
            documents = [item for item in self.documents if matches(item, query)]
            if sort:
                key, direction = sort[0]
                documents.sort(key=lambda item: item.get(key), reverse=direction < 0)
            return copy.deepcopy(documents[0]) if documents else None

    async def insert_one(self, document):
        if self.insert_delay:
            await asyncio.sleep(self.insert_delay)
        async with self.lock:
            self._enforce_unique(document)
            self.documents.append(copy.deepcopy(document))
        return Result()

    async def update_one(self, query, update, upsert=False):
        async with self.lock:
            for document in self.documents:
                if matches(document, query):
                    document.update(copy.deepcopy(update.get("$set", {})))
                    return Result()

            if upsert:
                document = copy.deepcopy(query)
                document.update(copy.deepcopy(update.get("$setOnInsert", {})))
                self._enforce_unique(document)
                self.documents.append(document)
        return Result()

    async def find_one_and_update(self, query, update, return_document=None):
        async with self.lock:
            for document in self.documents:
                if matches(document, query):
                    before = copy.deepcopy(document)
                    document.update(copy.deepcopy(update.get("$set", {})))
                    if return_document == ReturnDocument.AFTER:
                        return copy.deepcopy(document)
                    return before
        return None

    async def delete_many(self, query):
        async with self.lock:
            before = len(self.documents)
            self.documents = [item for item in self.documents if not matches(item, query)]
            return Result(before - len(self.documents))


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

    async def generate(self, db, collection_name, prefix):
        del db
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
            [("card_uid", 1), ("status", 1)],
        )
        self.assertEqual(
            session_indexes["uniq_active_session_vehicle"][0],
            [("vehicle_id", 1), ("status", 1)],
        )
        self.assertTrue(session_indexes["uniq_active_session_card"][1]["unique"])
        self.assertEqual(
            session_indexes["uniq_active_session_card"][1]["partialFilterExpression"],
            {"status": "in_progress"},
        )
        self.assertTrue(transaction_indexes["uniq_parking_fee_session"][1]["unique"])
        self.assertTrue(transaction_indexes["uniq_parking_fee_session"][1]["sparse"])
        self.assertEqual(len(db.parking_slots.calls), 1)


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


if __name__ == "__main__":
    unittest.main()
