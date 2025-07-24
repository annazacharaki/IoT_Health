#!/usr/bin/env python3
from flask import Flask, render_template, request
import sqlite3
import subprocess
import os

app = Flask(__name__)

DB_PATH = "/home/anna/health_database/health_data.db"
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MCP9808_SCRIPT  = os.path.join(BASE_DIR, 'temp_project', 'mcp9808_read_db.py')
ECG_SCRIPT      = os.path.join(BASE_DIR, 'ecg_project', 'spicheck_print_values_db.py')
MAX30102_SCRIPT = os.path.join(BASE_DIR, 'pox_project', 'max30102_only_spo2_db.py')

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
        cursor.execute(f"SELECT MAX(timestamp) AS latest FROM {table}")
        row = cursor.fetchone()
        conn.close()
        if row and row['latest']:
            # Βγάζουμε μόνο την ημερομηνία (YYYY‑MM‑DD)
            return row['latest'].split(' ')[0]
        return None
    except sqlite3.Error as e:
        print(f"Error getting latest date from {table}: {e}")
        conn.close()
        return None

def get_data(table, selected_date=None):
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor()
    # Επιλέγουμε το σωστό πεδίο ανά τύπο πίνακα
    if table == 'ecg_data':
        col = 'ecg'
    elif table == 'spo2_data':
        col = 'spo2'
    elif table == 'temperature_data':
        col = 'temp'
    else:
        col = 'value'
    try:
        if selected_date:
            cursor.execute(
                f"SELECT id, timestamp, {col} AS value FROM {table} "
                "WHERE DATE(timestamp)=? ORDER BY timestamp",
                (selected_date,)
            )
        else:
            cursor.execute(
                f"SELECT id, timestamp, {col} AS value FROM {table} "
                "ORDER BY timestamp DESC LIMIT 24"
            )
        rows = cursor.fetchall()
        conn.close()
        # Επιστρέφουμε λίστα dict με keys: id, timestamp, value
        return [
            {'id': row['id'], 'timestamp': row['timestamp'], 'value': row['value']}
            for row in rows
        ]
    except sqlite3.Error as e:
        print(f"Error fetching data from {table}: {e}")
        conn.close()
        return []

@app.route('/')
def index():
    return render_template('index23.html')

@app.route('/temperature')
def temperature():
    selected_date = request.args.get('date')
    data = get_data('temperature_data', selected_date)
    latest_date = get_latest_date('temperature_data')
    return render_template('temperature.html',
                           data=data,
                           selected_date=selected_date,
                           latest_date=latest_date)

@app.route('/spo2')
def spo2():
    selected_date = request.args.get('date')
    data = get_data('spo2_data', selected_date)
    latest_date = get_latest_date('spo2_data')
    return render_template('spo2.html',
                           data=data,
                           selected_date=selected_date,
                           latest_date=latest_date)

@app.route('/ecg')
def ecg():
    selected_date = request.args.get('date')
    data = get_data('ecg_data', selected_date)
    latest_date = get_latest_date('ecg_data')
    return render_template('ecg.html',
                           data=data,
                           selected_date=selected_date,
                           latest_date=latest_date)

# ---- Sensor endpoints ----

@app.route('/run_mcp9808', methods=['POST'])
def run_mcp9808():
    subprocess.run(['python3', MCP9808_SCRIPT], check=True)
    return ('', 200)

@app.route('/run_ecg', methods=['POST'])
def run_ecg_script():
    subprocess.run(['python3', ECG_SCRIPT], check=True)
    return ('', 200)

@app.route('/run_max30102', methods=['POST'])
def run_max_script():
    subprocess.run(['python3', MAX30102_SCRIPT], check=True)
    return ('', 200)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
