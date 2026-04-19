"""
Statistics Controller - Thống kê
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.database import get_database
from app.utils.serializers import serialize_list

router = APIRouter()


@router.get("")
async def get_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get general statistics"""
    # Count documents
    total_customers = await db.customers.count_documents({})
    total_vehicles = await db.vehicles.count_documents({})
    total_sessions = await db.sessions.count_documents({})
    active_sessions = await db.sessions.count_documents({"status": "in_progress"})
    
    # Get today's data
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_entries = await db.sessions.count_documents({"entry_time": {"$gte": today_start}})
    today_exits = await db.sessions.count_documents({
        "exit_time": {"$gte": today_start},
        "status": "completed"
    })
    
    # Calculate today's revenue
    today_transactions = await db.transactions.find({
        "created_at": {"$gte": today_start},
        "transaction_type": "parking_fee"
    }).to_list(length=10000)
    today_revenue = sum(t["amount"] for t in today_transactions)
    
    # Get available slots
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
            "occupancy_rate": round((active_sessions / total_slots * 100), 1) if total_slots > 0 else 0
        }
    }


@router.get("/revenue")
async def get_revenue_stats(
    days: int = Query(7, ge=1, le=365),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get revenue statistics"""
    # Get transactions for the last N days
    start_date = datetime.now() - timedelta(days=days)
    
    transactions = await db.transactions.find({
        "created_at": {"$gte": start_date},
        "transaction_type": {"$in": ["parking_fee", "package_purchase"]}
    }).to_list(length=100000)
    
    # Group by date
    daily_revenue = defaultdict(float)
    for t in transactions:
        date_key = t["created_at"].strftime("%Y-%m-%d")
        daily_revenue[date_key] += t["amount"]
    
    # Format for chart
    chart_data = []
    for i in range(days):
        date = datetime.now() - timedelta(days=days - i - 1)
        date_key = date.strftime("%Y-%m-%d")
        chart_data.append({
            "date": date_key,
            "revenue": daily_revenue.get(date_key, 0)
        })
    
    # Calculate totals
    total_revenue = sum(daily_revenue.values())
    avg_daily_revenue = total_revenue / days if days > 0 else 0
    
    # Get revenue by type
    parking_fee_revenue = sum(t["amount"] for t in transactions if t["transaction_type"] == "parking_fee")
    package_revenue = sum(t["amount"] for t in transactions if t["transaction_type"] == "package_purchase")
    
    return {
        "success": True,
        "data": {
            "period_days": days,
            "total_revenue": total_revenue,
            "avg_daily_revenue": avg_daily_revenue,
            "parking_fee_revenue": parking_fee_revenue,
            "package_revenue": package_revenue,
            "chart_data": chart_data,
            "revenue_by_type": [
                {"type": "Phí đỗ xe", "amount": parking_fee_revenue},
                {"type": "Gói cước", "amount": package_revenue}
            ]
        }
    }


@router.get("/dashboard")
async def get_dashboard_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get dashboard statistics"""
    # Count documents
    total_customers = await db.customers.count_documents({})
    total_vehicles = await db.vehicles.count_documents({})
    active_sessions = await db.sessions.count_documents({"status": "in_progress"})
    
    # Get today's revenue
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_transactions = await db.transactions.find({
        "created_at": {"$gte": today_start},
        "transaction_type": "parking_fee"
    }).to_list(length=10000)
    today_revenue = sum(t["amount"] for t in today_transactions)
    
    # Get slots info
    total_slots = await db.parking_slots.count_documents({})
    available_slots = await db.parking_slots.count_documents({"status": "available"})
    occupied_slots = await db.parking_slots.count_documents({"status": "occupied"})
    
    # Get recent sessions
    recent_sessions = await db.sessions.find().sort("entry_time", -1).limit(10).to_list(length=10)
    
    # Get active sessions with details
    active_sessions_list = await db.sessions.find({"status": "in_progress"}).to_list(length=100)
    
    # Enrich with customer and vehicle info
    for session in active_sessions_list:
        customer = await db.customers.find_one({"customer_id": session["customer_id"]})
        vehicle = await db.vehicles.find_one({"vehicle_id": session["vehicle_id"]})
        session["customer_name"] = customer["name"] if customer else "Unknown"
        session["vehicle_plate"] = vehicle["plate_number"] if vehicle else "Unknown"
    
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
            "active_sessions_list": serialize_list(active_sessions_list)
        }
    }


@router.get("/occupancy")
async def get_occupancy_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get occupancy statistics for chart"""
    total_slots = await db.parking_slots.count_documents({})
    occupied = await db.parking_slots.count_documents({"status": "occupied"})
    available = await db.parking_slots.count_documents({"status": "available"})
    
    # If no slots initialized, return default
    if total_slots == 0:
        return {
            "success": True,
            "data": {
                "occupied": 0,
                "available": 20,
                "total": 20
            }
        }
    
    return {
        "success": True,
        "data": {
            "occupied": occupied,
            "available": available,
            "total": total_slots
        }
    }


@router.get("/revenue-summary")
async def get_revenue_summary(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get revenue summary for revenue page"""
    now = datetime.now()
    
    # Today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_txs = await db.transactions.find({
        "created_at": {"$gte": today_start},
        "transaction_type": {"$in": ["parking_fee", "package_purchase"]}
    }).to_list(length=10000)
    today_revenue = sum(t["amount"] for t in today_txs)
    
    # This week
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_txs = await db.transactions.find({
        "created_at": {"$gte": week_start},
        "transaction_type": {"$in": ["parking_fee", "package_purchase"]}
    }).to_list(length=10000)
    week_revenue = sum(t["amount"] for t in week_txs)
    
    # This month
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_txs = await db.transactions.find({
        "created_at": {"$gte": month_start},
        "transaction_type": {"$in": ["parking_fee", "package_purchase"]}
    }).to_list(length=10000)
    month_revenue = sum(t["amount"] for t in month_txs)
    
    # Total
    all_txs = await db.transactions.find({
        "transaction_type": {"$in": ["parking_fee", "package_purchase"]}
    }).to_list(length=100000)
    total_revenue = sum(t["amount"] for t in all_txs)
    
    return {
        "success": True,
        "data": {
            "today": today_revenue,
            "week": week_revenue,
            "month": month_revenue,
            "total": total_revenue
        }
    }


@router.get("/revenue-by-package")
async def get_revenue_by_package(db: AsyncIOMotorDatabase = Depends(get_database)):
    """Get revenue breakdown by package type"""
    # Get all transactions
    transactions = await db.transactions.find({
        "transaction_type": {"$in": ["parking_fee", "package_purchase"]}
    }).to_list(length=100000)
    
    # Count by type
    per_use = sum(t["amount"] for t in transactions if t.get("transaction_type") == "parking_fee")
    daily = 0
    monthly = 0
    
    # Get package purchases
    packages = await db.packages.find({}).to_list(length=10000)
    for pkg in packages:
        if pkg.get("package_type") == "daily":
            daily += pkg.get("price", 50000)
        elif pkg.get("package_type") == "monthly":
            monthly += pkg.get("price", 500000)
    
    return {
        "success": True,
        "data": {
            "labels": ["Theo lượt", "Theo ngày", "Theo tháng"],
            "values": [per_use, daily, monthly]
        }
    }


@router.get("/recent-transactions")
async def get_recent_transactions(
    limit: int = Query(10, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Get recent transactions"""
    transactions = await db.transactions.find().sort("created_at", -1).limit(limit).to_list(length=limit)
    
    # Enrich with customer info
    for tx in transactions:
        customer = await db.customers.find_one({"customer_id": tx.get("customer_id")})
        tx["customer_name"] = customer.get("name") if customer else "N/A"
    
    return {
        "success": True,
        "data": serialize_list(transactions)
    }



