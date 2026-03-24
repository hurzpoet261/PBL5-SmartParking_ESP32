from pymongo import MongoClient
import datetime

class Database:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["SmartParking"]
        self.collection = self.db["parking_history"]
        self.alert_collection = self.db["parking_alerts"]

    def log_entry(self, card_id, action="IN", fee=5000):
        data = {
            "card_id": card_id,
            "timestamp": datetime.datetime.now(),
            "action": action,
            "fee": fee
        }
        self.collection.insert_one(data)

    def get_all_logs(self):
        return list(self.collection.find({}, {"_id": 0}))

    def get_revenue_stats(self):
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$fee"}}}]
        result = list(self.collection.aggregate(pipeline))
        return result[0]["total"] if result else 0

    def get_usage_stats(self):
        pipeline = [
            {"$group": {"_id": "$action", "count": {"$sum": 1}}}
        ]
        result = list(self.collection.aggregate(pipeline))
        return {item["_id"]: item["count"] for item in result}

    def log_alert(self, message):
        data = {
            "message": message,
            "timestamp": datetime.datetime.now()
        }
        self.alert_collection.insert_one(data)

    def get_alerts(self, limit=20):
        return list(self.alert_collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))