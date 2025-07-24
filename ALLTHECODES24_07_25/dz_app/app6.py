#!/usr/bin/env python3
from flask import Flask, render_template, request
import sqlite3
from datetime import datetime
import subprocess
import os

app = Flask(__name__)
DB_PATH = "/home/anna/health_database/health_data.db"

# Paths to sensor scripts
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MCP9808_SCRIPT   = os.path.join(BASE_DIR, 'temp_project',      'mcp9808_read_db.py')
ECG_SCRIPT       = os.path.join(BASE_DIR, 'ecg_project',       'spicheck_print_values_db.py')
MAX30102_SCRIPT  = os.path.join(BASE_DIR, 'pox_project',       'max30102_only_spo2_db.py')

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
            # Επιστρέφουμε μόνο την ημερομηνία (YYYY‑MM‑DD)
            return row['latest'].split(' ')[0]
        return None
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
        # Ορισμός ονόματος στήλης βάσει πίνακα
        column = 'value'
        if table == 'ecg_data':
            column = 'ecg_value'
        elif table == 'spo2_data':
            column = 'spo2'
        else:
            column = 'temperature'

        # Εκτέλεση query
        if date:
            cursor.execute(f"SELECT * FROM {table} WHERE date(timestamp) = ?", (date,))
        else:
            cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        conn.close()

        # Επιστροφή λίστας από dicts με id, timestamp και την αντίστοιχη στήλη
        return [
            {'id': row['id'], 'timestamp': row['timestamp'], column: row[column]}
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
    data         = get_data('temp_data', selected_date)
    latest_date  = get_latest_date('temp_data')
    return render_template(
        'temperature.html',
        data=data,
        selected_date=selected_date,
        latest_date=latest_date
    )

@app.route('/spo2')
def spo2():
    selected_date = request.args.get('date')
    data         = get_data('spo2_data', selected_date)
    latest_date  = get_latest_date('spo2_data')
    return render_template(
        'spo2.html',
        data=data,
        selected_date=selected_date,
        latest_date=latest_date
    )

@app.route('/ecg')
def ecg():
    selected_date = request.args.get('date')
    data         = get_data('ecg_data', selected_date)
    latest_date  = get_latest_date('ecg_data')
    return render_template(
        'ecg.html',
        data=data,
        selected_date=selected_date,
        latest_date=latest_date
    )

# ---- Sensor endpoints: μπλοκάρουν μέχρι να ολοκληρωθεί η μέτρηση ----

@app.route('/run_mcp9808', methods=['POST'])
def run_mcp9808():
    try:
        subprocess.run(['python3', MCP9808_SCRIPT], check=True)
        return ('', 204)
    except subprocess.CalledProcessError as e:
        print(f"MCP9808 measurement failed: {e}")
        return ('Measurement error', 500)

@app.route('/run_ecg', methods=['POST'])
def run_ecg_script():
    try:
        subprocess.run(['python3', ECG_SCRIPT], check=True)
        return ('', 204)
    except subprocess.CalledProcessError as e:
        print(f"ECG measurement failed: {e}")
        return ('Measurement error', 500)

@app.route('/run_max30102', methods=['POST'])
def run_max_script():
    try:
        subprocess.run(['python3', MAX30102_SCRIPT], check=True)
        return ('', 204)
    except subprocess.CalledProcessError as e:
        print(f"MAX30102 measurement failed: {e}")
        return ('Measurement error', 500)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
