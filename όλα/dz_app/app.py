from flask import Flask, render_template, request
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB_PATH = "/home/anna/health_database/health_data.db"

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_latest_date(table):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT MAX(timestamp) as latest FROM {table}")
        result = cursor.fetchone()
        conn.close()
        return result['latest'].split(' ')[0] if result['latest'] else None
    except sqlite3.Error as e:
        print(f"Error getting latest date from {table}: {e}")
        conn.close()
        return None

def get_data(table, date=None):
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    try:
        # Check if table and column exist
        column = table.split('_')[0]
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [info[1] for info in cursor.fetchall()]
        if column not in columns:
            print(f"Column '{column}' not found in table '{table}'")
            conn.close()
            return []

        # Check if table has any data
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        if cursor.fetchone()['count'] == 0:
            print(f"No data found in table '{table}'")
            conn.close()
            return []

        # Execute query
        if date:
            query = f"SELECT * FROM {table} WHERE date(timestamp) = ? ORDER BY timestamp"
            cursor.execute(query, (date,))
        else:
            query = f"SELECT * FROM {table} WHERE date(timestamp) = (SELECT MAX(date(timestamp)) FROM {table}) ORDER BY timestamp"
            cursor.execute(query)
        data = cursor.fetchall()
        print(f"Data from {table} (date: {date or 'latest'}): {[dict(row) for row in data]}")
        conn.close()
        if not data:
            print(f"No data found for {table} on date {date or 'latest'}")
            return []
        return [{'id': row['id'], 'timestamp': row['timestamp'], column: row[column]} for row in data]
    except sqlite3.Error as e:
        print(f"Error fetching data from {table}: {e}")
        conn.close()
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/temperature', methods=['GET'])
def temperature():
    selected_date = request.args.get('date')
    data = get_data('temp_data', selected_date)
    latest_date = get_latest_date('temp_data')
    return render_template('temperature.html', data=data, selected_date=selected_date, latest_date=latest_date)

@app.route('/spo2', methods=['GET'])
def spo2():
    selected_date = request.args.get('date')
    data = get_data('spo2_data', selected_date)
    latest_date = get_latest_date('spo2_data')
    return render_template('spo2.html', data=data, selected_date=selected_date, latest_date=latest_date)

@app.route('/ecg', methods=['GET'])
def ecg():
    selected_date = request.args.get('date')
    data = get_data('ecg_data', selected_date)
    latest_date = get_latest_date('ecg_data')
    return render_template('ecg.html', data=data, selected_date=selected_date, latest_date=latest_date)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)