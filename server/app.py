from flask import Flask, render_template, jsonify
from pymongo import MongoClient
import datetime

app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')

# Kết nối MongoDB
db_client = MongoClient("mongodb://localhost:27017/")
db = db_client["SmartParking"]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    # Lấy dữ liệu doanh thu từ MongoDB để vẽ biểu đồ
    data = list(db.history.find({}, {"_id": 0}))
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)