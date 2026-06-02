"""Atomic-style full registration workflow with compensating rollback."""
import re
import logging
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator, model_validator
from pymongo.errors import ConfigurationError, DuplicateKeyError, OperationFailure

from app.database import get_database
from app.models.customer import CustomerCreate
from app.models.package import Package, PackageType
from app.models.rfid_card import CardStatus, RFIDCardCreate
from app.models.vehicle import VehicleType
from app.services.fee_calculator import FeeCalculator
from app.utils.id_generator import generate_id
from app.utils.serializers import serialize_mongodb_document

router = APIRouter()
logger = logging.getLogger(__name__)
CARD_UID_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{4,32}$")


def normalize_card_uid(value: str) -> str:
    """Normalize UID while preserving the existing hexadecimal representation."""

    card_uid = (value or "").strip().lower()
    if not CARD_UID_RE.fullmatch(card_uid):
        raise ValueError("card_uid must contain 4-32 hexadecimal characters")
    return card_uid if card_uid.startswith("0x") else f"0x{card_uid}"


def card_uid_variants(card_uid: str) -> List[str]:
    """Match normalized and legacy UID representations during migration."""

    normalized = normalize_card_uid(card_uid)
    uid_hex = normalized[2:]
    return [normalized, uid_hex, normalized.upper(), uid_hex.upper()]


def normalize_plate(value: str) -> str:
    """Normalize plate values before enforcing uniqueness."""

    normalized = re.sub(r"[^0-9A-Z]", "", (value or "").upper())
    if not normalized:
        raise ValueError("plate_number cannot be empty")
    return normalized


def plate_uniqueness_query(plate_number: str) -> dict:
    """Match normalized and legacy formatted plate representations."""

    normalized = normalize_plate(plate_number)
    separator = r"[^0-9A-Z]*"
    legacy_pattern = "^" + separator.join(re.escape(char) for char in normalized) + "$"
    return {
        "$or": [
            {"normalized_plate": normalized},
            {"plate_number": {"$regex": legacy_pattern, "$options": "i"}},
        ]
    }


class RegistrationVehicle(BaseModel):
    """Vehicle details for a newly-created customer."""

    plate_number: str = Field(..., min_length=1)
    vehicle_type: VehicleType = VehicleType.MOTORBIKE
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=30)

    @field_validator("plate_number")
    @classmethod
    def validate_plate(cls, value: str) -> str:
        return normalize_plate(value)


class RegistrationPackage(BaseModel):
    """Optional vehicle package attached during registration."""

    package_type: PackageType
    remaining_uses: Optional[int] = Field(None, ge=0)

    @model_validator(mode="after")
    def validate_remaining_uses(self):
        if self.package_type == PackageType.PER_USE and (
            self.remaining_uses is None or self.remaining_uses <= 0
        ):
            raise ValueError("per_use package requires remaining_uses > 0")
        if (
            self.package_type in {PackageType.DAILY, PackageType.MONTHLY}
            and self.remaining_uses is not None
        ):
            raise ValueError("remaining_uses is only allowed for per_use packages")
        return self


class FullRegistrationRequest(BaseModel):
    """Create customer, vehicle, RFID card and optional package in one request."""

    customer: CustomerCreate
    vehicle: RegistrationVehicle
    card_uid: str
    package: Optional[RegistrationPackage] = None

    @field_validator("card_uid")
    @classmethod
    def validate_card_uid(cls, value: str) -> str:
        return normalize_card_uid(value)


class RegisterCardRequest(RFIDCardCreate):
    """Strict compatibility schema for attaching a card to existing records."""

    customer_id: str = Field(..., min_length=1)
    vehicle_id: str = Field(..., min_length=1)
    status: CardStatus = CardStatus.ACTIVE

    @field_validator("card_uid")
    @classmethod
    def validate_card_uid(cls, value: str) -> str:
        return normalize_card_uid(value)


async def rollback_created_documents(
    db: AsyncIOMotorDatabase,
    created: List[Tuple[str, dict]],
) -> None:
    """Delete only documents created by the failed registration attempt."""

    for collection_name, query in reversed(created):
        try:
            await db[collection_name].delete_one(query)
        except Exception as exc:
            logger.error(
                "Registration rollback failed collection=%s query=%s error=%s",
                collection_name,
                query,
                exc,
            )


def transaction_is_unavailable(exc: Exception) -> bool:
    """Identify topologies that cannot execute multi-document transactions."""

    return isinstance(exc, ConfigurationError) or (
        isinstance(exc, OperationFailure) and exc.code == 20
    )


async def create_registration_documents(
    payload: FullRegistrationRequest,
    db: AsyncIOMotorDatabase,
    *,
    session=None,
    compensate_on_error: bool,
):
    """Create all documents using a transaction session or explicit rollback."""

    card_uid = normalize_card_uid(payload.card_uid)
    plate_number = normalize_plate(payload.vehicle.plate_number)
    session_arg = {"session": session} if session is not None else {}
    if await db.rfid_cards.find_one(
        {"card_uid": {"$in": card_uid_variants(card_uid)}},
        **session_arg,
    ):
        raise HTTPException(status_code=409, detail="RFID card UID already exists")
    if await db.vehicles.find_one(plate_uniqueness_query(plate_number), **session_arg):
        raise HTTPException(status_code=409, detail="Plate number already exists")

    created: List[Tuple[str, dict]] = []
    try:
        now = datetime.now()
        customer_id = await generate_id(db, "customers", "C", session=session)
        customer = {
            "customer_id": customer_id,
            **payload.customer.model_dump(mode="json"),
            "balance": 0.0,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        }
        await db.customers.insert_one(customer, **session_arg)
        created.append(("customers", {"customer_id": customer_id}))

        vehicle_id = await generate_id(db, "vehicles", "V", session=session)
        vehicle = {
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            **payload.vehicle.model_dump(mode="json"),
            "plate_number": plate_number,
            "normalized_plate": plate_number,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        }
        await db.vehicles.insert_one(vehicle, **session_arg)
        created.append(("vehicles", {"vehicle_id": vehicle_id}))

        card = {
            "card_uid": card_uid,
            "customer_id": customer_id,
            "vehicle_id": vehicle_id,
            "status": CardStatus.ACTIVE.value,
            "issued_at": now,
            "expire_at": None,
            "created_at": now,
            "notes": "Registered through full registration workflow",
        }
        await db.rfid_cards.insert_one(card, **session_arg)
        created.append(("rfid_cards", {"card_uid": card_uid}))

        package = None
        if payload.package:
            package_id = await generate_id(db, "packages", "P", session=session)
            package_type = payload.package.package_type
            price = FeeCalculator.get_package_price(
                package_type,
                payload.package.remaining_uses,
            )
            package = {
                "package_id": package_id,
                "customer_id": customer_id,
                "vehicle_id": vehicle_id,
                "vehicle_type": payload.vehicle.vehicle_type.value,
                "package_type": package_type.value,
                "price": price,
                "start_date": now,
                "expire_date": Package.calculate_expire_date(package_type, now),
                "remaining_uses": payload.package.remaining_uses,
                "consumed_session_ids": [],
                "status": "active",
                "created_at": now,
            }
            await db.packages.insert_one(package, **session_arg)
            created.append(("packages", {"package_id": package_id}))

            transaction_id = await generate_id(db, "transactions", "T", session=session)
            transaction = {
                "transaction_id": transaction_id,
                "customer_id": customer_id,
                "transaction_type": "package_purchase",
                "amount": price,
                "package_id": package_id,
                "payment_method": "cash",
                "description": f"Package purchase - {package_type.value}",
                "created_at": now,
            }
            await db.transactions.insert_one(transaction, **session_arg)
            created.append(("transactions", {"transaction_id": transaction_id}))

        return {
            "success": True,
            "message": "Full registration completed successfully",
            "data": {
                "customer": serialize_mongodb_document(customer),
                "vehicle": serialize_mongodb_document(vehicle),
                "rfid_card": serialize_mongodb_document(card),
                "package": serialize_mongodb_document(package) if package else None,
            },
        }
    except HTTPException:
        if compensate_on_error:
            await rollback_created_documents(db, created)
        raise
    except DuplicateKeyError as exc:
        if compensate_on_error:
            await rollback_created_documents(db, created)
        raise HTTPException(
            status_code=409,
            detail="RFID card UID or plate number already exists",
        ) from exc
    except Exception:
        if compensate_on_error:
            await rollback_created_documents(db, created)
        raise


async def create_full_registration(
    payload: FullRegistrationRequest,
    db: AsyncIOMotorDatabase,
):
    """Prefer MongoDB transaction; fall back to compensating rollback."""

    client = getattr(db, "client", None)
    if client is not None and hasattr(client, "start_session"):
        try:
            async with await client.start_session() as session:
                async with session.start_transaction():
                    return await create_registration_documents(
                        payload,
                        db,
                        session=session,
                        compensate_on_error=False,
                    )
        except Exception as exc:
            if not transaction_is_unavailable(exc):
                raise
            logger.warning(
                "MongoDB transactions unavailable; using registration rollback: %s",
                exc,
            )

    return await create_registration_documents(
        payload,
        db,
        compensate_on_error=True,
    )


@router.post("/full")
async def register_full(
    payload: FullRegistrationRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Register a customer and all dependent records in one safe request."""

    return await create_full_registration(payload, db)
