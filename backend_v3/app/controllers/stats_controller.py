"""
Statistics Controller - Thong ke
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from html import escape as html_escape
from typing import Any, Dict, List, Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.utils.serializers import serialize_list
from app.utils.timezone import now_local

router = APIRouter()

REVENUE_TRANSACTION_TYPES = {"parking_fee", "package_purchase", "package_renewal"}
EXPORT_REVENUE_TYPES = {"all", "parking_fee", "package", "package_purchase", "package_renewal"}


def amount_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def parse_report_datetime(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None

    raw = value.strip()
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid date: {value}") from exc

    if len(raw) <= 10:
        if end_of_day:
            return parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed.replace(hour=0, minute=0, second=0, microsecond=0)
    return parsed


def bounded_date_query(field: str, start_date: Optional[datetime], end_date: Optional[datetime]) -> Dict[str, Any]:
    bounds: Dict[str, Any] = {}
    if start_date:
        bounds["$gte"] = start_date
    if end_date:
        bounds["$lte"] = end_date
    return {field: bounds} if bounds else {}


def normalize_revenue_type(revenue_type: Optional[str]) -> str:
    normalized = (revenue_type or "all").strip().lower()
    if normalized not in EXPORT_REVENUE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid revenue_type")
    return normalized


def dt_key(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    try:
        return datetime.fromisoformat(str(value)).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def dt_text(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value or "")


def sort_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return datetime.min


async def load_customer_vehicle_maps(
    db: AsyncIOMotorDatabase,
    customer_ids: Sequence[str],
    vehicle_ids: Sequence[str],
) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    customers = (
        await db.customers.find({"customer_id": {"$in": list(customer_ids)}}).to_list(length=len(customer_ids))
        if customer_ids
        else []
    )
    vehicles = (
        await db.vehicles.find({"vehicle_id": {"$in": list(vehicle_ids)}}).to_list(length=len(vehicle_ids))
        if vehicle_ids
        else []
    )
    return (
        {customer.get("customer_id"): customer for customer in customers},
        {vehicle.get("vehicle_id"): vehicle for vehicle in vehicles},
    )


def session_customer_name(session: Dict[str, Any], customer: Optional[Dict[str, Any]]) -> str:
    if customer:
        return str(customer.get("name") or "N/A")
    return str(session.get("customer_name_snapshot") or "N/A")


def session_plate_number(session: Dict[str, Any], vehicle: Optional[Dict[str, Any]]) -> str:
    if vehicle:
        return str(vehicle.get("plate_number") or "N/A")
    return str(
        session.get("plate_number_snapshot")
        or session.get("exit_plate_ocr")
        or session.get("entry_plate_ocr")
        or "N/A"
    )


async def build_session_fee_records(
    db: AsyncIOMotorDatabase,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {
        "status": "completed",
        "parking_fee": {"$gt": 0},
        "exit_time": {"$ne": None},
    }
    query.update(bounded_date_query("exit_time", start_date, end_date))

    sessions = await db.sessions.find(query).sort("exit_time", -1).to_list(length=100000)
    customer_ids = sorted({session.get("customer_id") for session in sessions if session.get("customer_id")})
    vehicle_ids = sorted({session.get("vehicle_id") for session in sessions if session.get("vehicle_id")})
    customers_by_id, vehicles_by_id = await load_customer_vehicle_maps(db, customer_ids, vehicle_ids)

    records: List[Dict[str, Any]] = []
    for session in sessions:
        session_id = session.get("session_id")
        customer = customers_by_id.get(session.get("customer_id"))
        vehicle = vehicles_by_id.get(session.get("vehicle_id"))
        records.append(
            {
                "transaction_id": session.get("transaction_id") or f"SESSION-{session_id}",
                "record_id": session_id,
                "source": "sessions",
                "transaction_type": "parking_fee",
                "transaction_type_label": "Phi gui xe",
                "amount": amount_value(session.get("parking_fee")),
                "created_at": session.get("exit_time"),
                "session_id": session_id,
                "customer_id": session.get("customer_id"),
                "customer_name": session_customer_name(session, customer),
                "vehicle_id": session.get("vehicle_id"),
                "plate_number": session_plate_number(session, vehicle),
                "payment_method": "cash",
                "package_type": "per_use",
                "description": f"Parking fee - {session_id}",
            }
        )
    return records


async def build_orphan_parking_transaction_records(
    db: AsyncIOMotorDatabase,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    query: Dict[str, Any] = {"transaction_type": "parking_fee"}
    query.update(bounded_date_query("created_at", start_date, end_date))
    transactions = await db.transactions.find(query).sort("created_at", -1).to_list(length=100000)

    session_ids = sorted({tx.get("session_id") for tx in transactions if tx.get("session_id")})
    sessions = (
        await db.sessions.find({"session_id": {"$in": session_ids}}).to_list(length=len(session_ids))
        if session_ids
        else []
    )
    sessions_by_id = {session.get("session_id"): session for session in sessions}
    customer_ids = sorted({tx.get("customer_id") for tx in transactions if tx.get("customer_id")})
    customers_by_id, _ = await load_customer_vehicle_maps(db, customer_ids, [])

    records: List[Dict[str, Any]] = []
    for tx in transactions:
        session = sessions_by_id.get(tx.get("session_id"))
        if session and amount_value(session.get("parking_fee")) > 0:
            continue
        customer = customers_by_id.get(tx.get("customer_id"))
        records.append(
            {
                "transaction_id": tx.get("transaction_id"),
                "record_id": tx.get("transaction_id"),
                "source": "transactions",
                "transaction_type": "parking_fee",
                "transaction_type_label": "Phi gui xe",
                "amount": amount_value(tx.get("amount")),
                "created_at": tx.get("created_at"),
                "session_id": tx.get("session_id"),
                "customer_id": tx.get("customer_id"),
                "customer_name": customer.get("name") if customer else "N/A",
                "vehicle_id": None,
                "plate_number": "N/A",
                "payment_method": tx.get("payment_method") or "cash",
                "package_type": "per_use",
                "description": tx.get("description") or "",
            }
        )
    return records


async def build_package_transaction_records(
    db: AsyncIOMotorDatabase,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    revenue_type: str = "all",
) -> List[Dict[str, Any]]:
    tx_types = ["package_purchase", "package_renewal"]
    if revenue_type in {"package_purchase", "package_renewal"}:
        tx_types = [revenue_type]

    query: Dict[str, Any] = {"transaction_type": {"$in": tx_types}}
    query.update(bounded_date_query("created_at", start_date, end_date))
    transactions = await db.transactions.find(query).sort("created_at", -1).to_list(length=100000)

    customer_ids = sorted({tx.get("customer_id") for tx in transactions if tx.get("customer_id")})
    package_ids = sorted({tx.get("package_id") for tx in transactions if tx.get("package_id")})
    customers_by_id, _ = await load_customer_vehicle_maps(db, customer_ids, [])
    packages = (
        await db.packages.find({"package_id": {"$in": package_ids}}).to_list(length=len(package_ids))
        if package_ids
        else []
    )
    packages_by_id = {package.get("package_id"): package for package in packages}

    records: List[Dict[str, Any]] = []
    for tx in transactions:
        customer = customers_by_id.get(tx.get("customer_id"))
        package = packages_by_id.get(tx.get("package_id"))
        package_type = package.get("package_type") if package else tx.get("package_type") or "unknown"
        records.append(
            {
                "transaction_id": tx.get("transaction_id"),
                "record_id": tx.get("transaction_id"),
                "source": "transactions",
                "transaction_type": tx.get("transaction_type"),
                "transaction_type_label": "Mua goi" if tx.get("transaction_type") == "package_purchase" else "Gia han goi",
                "amount": amount_value(tx.get("amount")),
                "created_at": tx.get("created_at"),
                "session_id": tx.get("session_id"),
                "customer_id": tx.get("customer_id"),
                "customer_name": customer.get("name") if customer else "N/A",
                "vehicle_id": tx.get("vehicle_id") or (package.get("vehicle_id") if package else None),
                "plate_number": "N/A",
                "payment_method": tx.get("payment_method") or "cash",
                "package_id": tx.get("package_id"),
                "package_type": package_type,
                "description": tx.get("description") or "",
            }
        )
    return records


async def build_revenue_records(
    db: AsyncIOMotorDatabase,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    revenue_type: str = "all",
) -> List[Dict[str, Any]]:
    revenue_type = normalize_revenue_type(revenue_type)
    records: List[Dict[str, Any]] = []

    if revenue_type in {"all", "parking_fee"}:
        records.extend(await build_session_fee_records(db, start_date, end_date))
        records.extend(await build_orphan_parking_transaction_records(db, start_date, end_date))

    if revenue_type in {"all", "package", "package_purchase", "package_renewal"}:
        records.extend(await build_package_transaction_records(db, start_date, end_date, revenue_type))

    records.sort(key=lambda item: sort_datetime(item.get("created_at")), reverse=True)
    return records


def sum_records(records: Sequence[Dict[str, Any]]) -> float:
    return sum(amount_value(record.get("amount")) for record in records)


async def revenue_total(
    db: AsyncIOMotorDatabase,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    revenue_type: str = "all",
) -> float:
    return sum_records(await build_revenue_records(db, start_date, end_date, revenue_type))


def records_to_export_rows(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "Ma giao dich": record.get("transaction_id") or record.get("record_id") or "",
            "Nguon": record.get("source") or "",
            "Loai": record.get("transaction_type_label") or record.get("transaction_type") or "",
            "So tien": amount_value(record.get("amount")),
            "Thoi gian": dt_text(record.get("created_at")),
            "Khach hang": record.get("customer_name") or "",
            "Ma khach hang": record.get("customer_id") or "",
            "Bien so": record.get("plate_number") or "",
            "Ma phien": record.get("session_id") or "",
            "Loai goi": record.get("package_type") or "",
            "Mo ta": record.get("description") or "",
        }
        for record in records
    ]


def export_filename(start_date: Optional[datetime], end_date: Optional[datetime], suffix: str) -> str:
    start_text = start_date.strftime("%Y%m%d") if start_date else "all"
    end_text = end_date.strftime("%Y%m%d") if end_date else "all"
    return f"smart_parking_revenue_{start_text}_{end_text}.{suffix}"


@router.get("")
async def get_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get general statistics"""
    total_customers = await db.customers.count_documents({})
    total_vehicles = await db.vehicles.count_documents({})
    total_sessions = await db.sessions.count_documents({})
    active_sessions = await db.sessions.count_documents({"status": "in_progress"})

    today_start = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    today_entries = await db.sessions.count_documents({"entry_time": {"$gte": today_start}})
    today_exits = await db.sessions.count_documents({"exit_time": {"$gte": today_start}, "status": "completed"})
    today_revenue = await revenue_total(db, today_start, None)

    total_slots = await db.parking_slots.count_documents({})
    available_slots = await db.parking_slots.count_documents({"status": "available"})

    return {
        "success": True,
        "data": {
            "total_customers": total_customers,
            "total_vehicles": total_vehicles,
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "today_entries": today_entries,
            "today_exits": today_exits,
            "today_revenue": today_revenue,
            "total_slots": total_slots,
            "available_slots": available_slots,
            "occupancy_rate": round((active_sessions / total_slots * 100), 1) if total_slots > 0 else 0,
        },
    }


@router.get("/revenue")
async def get_revenue_stats(
    days: int = Query(7, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get revenue statistics."""
    now = now_local()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days - 1)
    records = await build_revenue_records(db, start_date, now)

    daily_revenue: Dict[str, float] = {}
    for record in records:
        key = dt_key(record.get("created_at"))
        if not key:
            continue
        daily_revenue[key] = daily_revenue.get(key, 0.0) + amount_value(record.get("amount"))

    chart_data = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_key = date.strftime("%Y-%m-%d")
        chart_data.append({"date": date_key, "revenue": daily_revenue.get(date_key, 0)})

    total_revenue = sum_records(records)
    parking_fee_revenue = sum_records([record for record in records if record.get("transaction_type") == "parking_fee"])
    package_revenue = total_revenue - parking_fee_revenue

    return {
        "success": True,
        "data": {
            "period_days": days,
            "total_revenue": total_revenue,
            "avg_daily_revenue": total_revenue / days if days > 0 else 0,
            "parking_fee_revenue": parking_fee_revenue,
            "package_revenue": package_revenue,
            "chart_data": chart_data,
            "revenue_by_type": [
                {"type": "Phi do xe", "amount": parking_fee_revenue},
                {"type": "Goi cuoc", "amount": package_revenue},
            ],
        },
    }


@router.get("/dashboard")
async def get_dashboard_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get dashboard statistics."""
    total_customers = await db.customers.count_documents({})
    total_vehicles = await db.vehicles.count_documents({})
    active_sessions = await db.sessions.count_documents({"status": "in_progress"})

    today_start = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    today_revenue = await revenue_total(db, today_start, None)

    total_slots = await db.parking_slots.count_documents({})
    available_slots = await db.parking_slots.count_documents({"status": "available"})
    occupied_slots = await db.parking_slots.count_documents({"status": "occupied"})

    recent_sessions = await db.sessions.find().sort("entry_time", -1).limit(10).to_list(length=10)
    active_sessions_list = await db.sessions.find({"status": "in_progress"}).to_list(length=100)

    for session in active_sessions_list:
        customer = await db.customers.find_one({"customer_id": session["customer_id"]})
        vehicle = await db.vehicles.find_one({"vehicle_id": session["vehicle_id"]})
        session["customer_name"] = customer["name"] if customer else session.get("customer_name_snapshot") or "Unknown"
        session["vehicle_plate"] = (
            vehicle["plate_number"]
            if vehicle
            else session.get("plate_number_snapshot") or session.get("entry_plate_ocr") or "Unknown"
        )

    return {
        "success": True,
        "data": {
            "total_customers": total_customers,
            "total_vehicles": total_vehicles,
            "active_sessions": active_sessions,
            "today_revenue": today_revenue,
            "total_slots": total_slots if total_slots > 0 else 20,
            "available_slots": available_slots,
            "occupied_slots": occupied_slots,
            "recent_sessions": serialize_list(recent_sessions),
            "active_sessions_list": serialize_list(active_sessions_list),
        },
    }


@router.get("/occupancy")
async def get_occupancy_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get occupancy statistics for chart."""
    total_slots = await db.parking_slots.count_documents({})
    occupied = await db.parking_slots.count_documents({"status": "occupied"})
    available = await db.parking_slots.count_documents({"status": "available"})

    if total_slots == 0:
        return {"success": True, "data": {"occupied": 0, "available": 20, "total": 20}}

    return {"success": True, "data": {"occupied": occupied, "available": available, "total": total_slots}}


@router.get("/revenue-summary")
async def get_revenue_summary(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get revenue summary for revenue page."""
    now = now_local()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return {
        "success": True,
        "data": {
            "today": await revenue_total(db, today_start, now),
            "week": await revenue_total(db, week_start, now),
            "month": await revenue_total(db, month_start, now),
            "total": await revenue_total(db),
        },
    }


@router.get("/revenue-by-package")
async def get_revenue_by_package(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get revenue breakdown by package type."""
    records = await build_revenue_records(db)
    per_use = sum_records([record for record in records if record.get("transaction_type") == "parking_fee"])
    daily = sum_records([record for record in records if record.get("package_type") == "daily"])
    monthly = sum_records([record for record in records if record.get("package_type") == "monthly"])
    other = sum_records(
        [
            record
            for record in records
            if record.get("transaction_type") != "parking_fee"
            and record.get("package_type") not in {"daily", "monthly"}
        ]
    )

    labels = ["Theo luot", "Theo ngay", "Theo thang"]
    values = [per_use, daily, monthly]
    if other:
        labels.append("Goi khac")
        values.append(other)

    return {"success": True, "data": {"labels": labels, "values": values}}


@router.get("/recent-transactions")
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get recent revenue records from sessions and transactions."""
    records = await build_revenue_records(db)
    return {"success": True, "data": serialize_list(records[:limit])}


@router.get("/revenue-export")
async def export_revenue(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    format: str = Query("csv", pattern="^(csv|excel|xls)$"),
    revenue_type: str = Query("all"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Export revenue records to CSV or Excel-readable XLS."""
    start = parse_report_datetime(start_date)
    end = parse_report_datetime(end_date, end_of_day=True)
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    records = await build_revenue_records(db, start, end, normalize_revenue_type(revenue_type))
    rows = records_to_export_rows(records)

    if format == "csv":
        output = io.StringIO()
        headers = list(rows[0].keys()) if rows else [
            "Ma giao dich",
            "Nguon",
            "Loai",
            "So tien",
            "Thoi gian",
            "Khach hang",
            "Ma khach hang",
            "Bien so",
            "Ma phien",
            "Loai goi",
            "Mo ta",
        ]
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        filename = export_filename(start, end, "csv")
        return Response(
            "\ufeff" + output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    headers = list(rows[0].keys()) if rows else [
        "Ma giao dich",
        "Nguon",
        "Loai",
        "So tien",
        "Thoi gian",
        "Khach hang",
        "Ma khach hang",
        "Bien so",
        "Ma phien",
        "Loai goi",
        "Mo ta",
    ]
    html_rows = "\n".join(
        "<tr>" + "".join(f"<td>{html_escape(str(row.get(header, '')))}</td>" for header in headers) + "</tr>"
        for row in rows
    )
    html_table = (
        "<html><head><meta charset='utf-8'></head><body>"
        "<table border='1'>"
        "<thead><tr>"
        + "".join(f"<th>{html_escape(header)}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + html_rows
        + "</tbody></table></body></html>"
    )
    filename = export_filename(start, end, "xls")
    return Response(
        "\ufeff" + html_table,
        media_type="application/vnd.ms-excel; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
