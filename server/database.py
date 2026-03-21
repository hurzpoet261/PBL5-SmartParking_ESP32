from pymongo import MongoClient
import datetime

class Database:
    def __init__(self):
        self.client = MongoClient("mongodb://localhost:27017/")
        self.db = self.client["SmartParking"]
        self.collection = self.db["parking_history"]

    def log_entry(self, card_id):
        data = {
            "card_id": card_id,
            "timestamp": datetime.datetime.now(),
            "action": "IN",
            "fee": 5000
        }
        self.collection.insert_one(data)

    def get_all_logs(self):
        return list(self.collection.find({}, {"_id": 0}))

    def get_revenue_stats(self):
        # Thống kê tổng tiền
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$fee"}}}]
        result = list(self.collection.aggregate(pipeline))
        return result[0]['total'] if result else 0