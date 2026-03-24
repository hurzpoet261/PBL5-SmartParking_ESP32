from flask import Flask, render_template, jsonify
from database import Database

app = Flask(__name__, template_folder='../web/templates', static_folder='../web/static')

# Sử dụng class Database chung với mqtt_handler.py
db = Database()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/info')
def info():
    return render_template('info.html')

@app.route('/api/stats')
def stats():
    data = db.get_all_logs()
    return jsonify(data)

@app.route('/api/v1/revenue')
def revenue():
    total = db.get_revenue_stats()
    usage = db.get_usage_stats()
    return jsonify({"total": total, "usage": usage})

@app.route('/api/v1/alerts')
def alerts():
    return jsonify(db.get_alerts(limit=50))

if __name__ == '__main__':
    app.run(debug=True, port=5000)