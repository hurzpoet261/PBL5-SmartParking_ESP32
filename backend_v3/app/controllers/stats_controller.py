"""
Statistics Controller - Thống kê
"""
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict

from app.database import get_database

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
    # Get general stats
    general_stats = await get_stats(db)
    
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
            **general_stats["data"],
            "recent_sessions": recent_sessions,
            "active_sessions_list": active_sessions_list
        }
    }
