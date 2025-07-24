from flask import Flask, render_template, request
import sqlite3
import subprocess
import os

app = Flask(__name__)

# Διαδρομή στη βάση δεδομένων
DB_PATH = "/home/anna/health_database/health_data.db"

# Βασικός φάκελος για τα scripts
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MCP9808_SCRIPT  = os.path.join(BASE_DIR, 'temp_project',   'mcp9808_read_db.py')
ECG_SCRIPT      = os.path.join(BASE_DIR, 'ecg_project',    'spicheck_print_values_db.py')
MAX30102_SCRIPT = os.path.join(BASE_DIR, 'pox_project',    'max30102_only_spo2_db.py')

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"DB connection error: {e}")
        return None

def get_latest_date(table):
    conn = get_db_connection()
    if not conn:
        return None
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT MAX(timestamp) AS latest FROM {table}")
        row = cur.fetchone()
        conn.close()
        if row and row['latest']:
            return row['latest'].split(' ')[0]  # YYYY‑MM‑DD
        return None
    except sqlite3.Error as e:
        print(f"Error getting latest date: {e}")
        conn.close()
        return None

def get_data(table, selected_date=None):
    """
    Επιστρέφει list of dicts:
      - για temp_data: keys 'id', 'timestamp', 'temp'
      - για άλλους πίνακες: απλό dict(row) (θα φτιάξουμε μετά)
    """
    conn = get_db_connection()
    if not conn:
        return []
    cur = conn.cursor()

    if table == 'temp_data':
        # aliased column ώστε στο template να χρησιμοποιούμε {{ row.temp }}
        col_sql = 'temperature AS temp'
    else:
        # για τους υπόλοιπους, φέρνουμε όλα τα πεδία όπως είναι
        col_sql = '*'

    # εκτέλεση query
    if table == 'temp_data':
        if selected_date:
            cur.execute(
                f"SELECT id, timestamp, {col_sql} FROM {table} WHERE date(timestamp)=?",
                (selected_date,)
            )
        else:
            cur.execute(f"SELECT id, timestamp, {col_sql} FROM {table}")
    else:
        if selected_date:
            cur.execute(f"SELECT * FROM {table} WHERE date(timestamp)=?", (selected_date,))
        else:
            cur.execute(f"SELECT * FROM {table}")

    rows = cur.fetchall()
    conn.close()

    if table == 'temp_data':
        # Επιστρέφουμε dicts με κλειδιά id, timestamp, temp
        return [
            {
                'id':        row['id'],
                'timestamp': row['timestamp'],
                'temp':      row['temp']
            }
            for row in rows
        ]
    else:
        # προσωρινό: απλό dict για άλλους πίνακες
        return [dict(row) for row in rows]

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