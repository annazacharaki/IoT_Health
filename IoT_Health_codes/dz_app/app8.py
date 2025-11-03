import os
import sys
import time
from flask import Flask, render_template, request, jsonify
import sqlite3
import subprocess
from dotenv import load_dotenv
from oled_ui import display_message


# === chat_verb (Ollama backend) ===
from chat_verb import (
    postprocess_sql,
    is_safe_readonly,
    run_readonly,
    verbalize_answer,
    generate_sql_ollama,
)

# Ensure project root is on path to find utils
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.encryption_utils import decrypt_field

# Load environment variables from project root
load_dotenv(os.path.join(ROOT, '.env'))

# Δείξε welcome μήνυμα στην OLED με το ξεκίνημα του service
try:
    display_message("IoT_Health", "Welcome!", False)
except Exception as e:
    app.logger.warning(f"Could not display welcome message: {e}")

app = Flask(__name__)

# Warn if encryption key is missing
if not os.getenv('DB_ENC_KEY'):
    app.logger.warning('DB_ENC_KEY is not set in .env — decrypt_field may fail; proceeding with best-effort (values will be None).')

# Prefer DB_PATH from .env; fall back to project default
DB_PATH = os.getenv('DB_PATH', os.path.join(ROOT, 'health_database', 'health_data.db'))

# Paths to sensor scripts
MCP9808_SCRIPT = os.path.join(ROOT, 'temp_project', 'mcp9808_read_db.py')
ECG_SCRIPT     = os.path.join(ROOT, 'ecg_project', 'spicheck_print_values_db.py')
MAX30102_SCRIPT= os.path.join(ROOT, 'pox_project', 'max30102_only_spo2_db_02.py')


# ---- Global JSON error handler (so the UI never gets HTML) ----
@app.errorhandler(Exception)
def _json_errors(e):
    app.logger.exception("Unhandled exception in Flask app")
    return jsonify({"error": "Internal error", "detail": str(e)}), 500


def get_db_connection():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        app.logger.error(f"Database connection error: {e}")
        return None


def get_latest_date(table):
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT MAX(timestamp) as latest FROM {table}")
        result = cursor.fetchone()
        return result['latest'].split(' ')[0] if result['latest'] else None
    except sqlite3.Error as e:
        app.logger.error(f"Error getting latest date from {table}: {e}")
        return None
    finally:
        conn.close()


# Original reader (all rows when date=None)
def get_data_OLD(table, date=None):
    """Fetch and decrypt data from the given table (all rows if date is None)."""
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor()

    if table == 'ecg_data':
        blob_col = 'enc_ecg'
    elif table == 'spo2_data':
        blob_col = 'enc_spo2'
    else:
        blob_col = 'enc_temp'

    try:
        if date:
            cursor.execute(f"SELECT id, timestamp, {blob_col} FROM {table} WHERE date(timestamp)=?", (date,))
        else:
            cursor.execute(f"SELECT id, timestamp, {blob_col} FROM {table}")

        rows = cursor.fetchall()
        result = []
        for row in rows:
            blob = row[blob_col]
            if blob is not None:
                try:
                    pt = decrypt_field(blob)
                    val = float(pt.decode())
                except Exception as ex:
                    app.logger.warning(f"Decrypt/parse failed for {table}: {ex}")
                    val = None
            else:
                val = None
            result.append({'id': row['id'], 'timestamp': row['timestamp'], 'value': val})
        return result
    except sqlite3.Error as e:
        app.logger.error(f"Error fetching data from {table}: {e}")
        return []
    finally:
        conn.close()


# Current reader used by pages (returns selected day or latest-day only)
def get_data(table, date=None, latest_date=None):
    """Fetch and decrypt data for the given table.
       If no date is given, fall back to latest_date (if provided)."""
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor()

    if table == 'ecg_data':
        blob_col = 'enc_ecg'
    elif table == 'spo2_data':
        blob_col = 'enc_spo2'
    else:
        blob_col = 'enc_temp'

    if not date and latest_date:
        date = latest_date

    try:
        if date:
            cursor.execute(f"SELECT id, timestamp, {blob_col} FROM {table} WHERE date(timestamp)=?", (date,))
        else:
            return []

        rows = cursor.fetchall()
        result = []
        for row in rows:
            blob = row[blob_col]
            if blob is not None:
                try:
                    pt = decrypt_field(blob)
                    val = float(pt.decode())
                except Exception as ex:
                    app.logger.warning(f"Decrypt/parse failed for {table}: {ex}")
                    val = None
            else:
                val = None
            result.append({'id': row['id'], 'timestamp': row['timestamp'], 'value': val})
        return result
    except sqlite3.Error as e:
        app.logger.error(f"Error fetching data from {table}: {e}")
        return []
    finally:
        conn.close()


# Small helper for Q&A: get ALL rows (decrypted)
def get_all_data(table):
    return get_data_OLD(table, date=None)


# === In-memory mirror for Q&A (Temperature & SpO2 only) ===

def make_inmemory_conn(temp_rows, spo2_rows):
    """
    Create an in-memory SQLite with two simple tables fed by already-decrypted data.
    IMPORTANT: set PRAGMA query_only=ON *after* creating & populating tables,
    otherwise CREATE/INSERT will fail with 'attempt to write a readonly database'.
    """
    mem = sqlite3.connect(":memory:")

    # 1) CREATE schema (allow writes εδώ)
    mem.execute("""
        CREATE TABLE temp_data (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            temp REAL
        );
    """)
    mem.execute("""
        CREATE TABLE spo2_data (
            id INTEGER PRIMARY KEY,
            timestamp TEXT NOT NULL,
            spo2 REAL
        );
    """)

    # 2) INSERT data
    if temp_rows:
        mem.executemany(
            "INSERT INTO temp_data(id,timestamp,temp) VALUES (?,?,?)",
            [
                (i + 1, r['timestamp'], float(r['value']))
                for i, r in enumerate(temp_rows)
                if r.get('value') is not None
            ],
        )
    if spo2_rows:
        mem.executemany(
            "INSERT INTO spo2_data(id,timestamp,spo2) VALUES (?,?,?)",
            [
                (i + 1, r['timestamp'], float(r['value']))
                for i, r in enumerate(spo2_rows)
                if r.get('value') is not None
            ],
        )
    mem.commit()

    # 3) ΤΩΡΑ κάνε το read-only
    try:
        mem.execute("PRAGMA query_only=ON;")
    except sqlite3.Error:
        pass

    return mem



# ---------- Routes ----------
@app.route('/')
def index():
    return render_template('index26.html')


@app.route('/temperature')
def temperature():
    selected_date = request.args.get('date')
    latest_date = get_latest_date('temp_data')
    data = get_data('temp_data', selected_date, latest_date)
    return render_template('temperature.html', data=data, selected_date=selected_date, latest_date=latest_date)


@app.route('/spo2')
def spo2():
    selected_date = request.args.get('date')
    latest_date = get_latest_date('spo2_data')
    data = get_data('spo2_data', selected_date, latest_date)
    return render_template('spo2.html', data=data, selected_date=selected_date, latest_date=latest_date)


@app.route('/ecg')
def ecg():
    selected_date = request.args.get('date')
    latest_date = get_latest_date('ecg_data')
    data = get_data('ecg_data', selected_date, latest_date)
    return render_template('ecg.html', data=data, selected_date=selected_date, latest_date=latest_date)


# === Q&A UI ===
@app.route('/qa')
def qa_page():
    return render_template('qa.html')

@app.route("/about")
def about():
    return render_template("about.html")

# === Q&A API (Ollama) ===
@app.route('/api/qa', methods=['POST'])
def qa_api():
    display_message("IoT_Health", "MediTaker is thinking...", True)
    
    payload = request.get_json(silent=True) or {}
    question = (payload.get('question') or '').strip()
    if not question:
        return jsonify({"error": "Empty question"}), 400

    # 1) Πάρε ΟΛΑ τα αποκρυπτογραφημένα δεδομένα
    temp_rows = get_all_data('temp_data')   # [{'timestamp','value'}, ...]
    spo2_rows = get_all_data('spo2_data')

    # 2) In-memory SQLite
    conn = make_inmemory_conn(temp_rows, spo2_rows)

    # 3) Κλήση στο Ollama – πιάστο αν σκάσει, και δώσε fallback
    try:
        sql = generate_sql_ollama(question)
    except Exception as e:
        conn.close()
        app.logger.exception("LLM call failed")
        return jsonify({"error": "LLM call failed", "detail": str(e)}), 502

    if not sql:
        q = question.lower()
        if any(k in q for k in ["spo2", "oxygen", "o2", "κορεσ", "οξυγ"]):
            sql = "SELECT timestamp, spo2 FROM spo2_data ORDER BY datetime(timestamp) DESC LIMIT 10;"
        else:
            sql = "SELECT timestamp, temp FROM temp_data ORDER BY datetime(timestamp) DESC LIMIT 10;"

    # 4) Safety + εκτέλεση
    sql = postprocess_sql(sql, question)
    if not is_safe_readonly(sql):
        conn.close()
        return jsonify({"error": "Unsafe SQL generated", "sql": sql}), 400

    try:
        cols, rows, ms = run_readonly(conn, sql)
    except Exception as e:
        conn.close()
        return jsonify({"error": f"SQL error: {e}", "sql": sql}), 400

    # 5) Σύνοψη (το verbalize_answer αγνοεί το 1ο arg)
    try:
        nl = verbalize_answer(None, question, cols, rows)
    except Exception:
        nl = ""

    conn.close()
    
    display_message("IoT_Health", "Finished!", False)

    
    return jsonify({
        "sql": sql,
        "cols": cols,
        "rows": rows[:200],
        "nl": nl,
        "latency_ms": ms,
    })


# ---- Sensor script runners ----
@app.route('/run_mcp9808', methods=['POST'])
def run_mcp9808():
    display_message("IoT_Health", "Measuring Temperature...", True)
    
    subprocess.run(['python3', MCP9808_SCRIPT], check=True)
    
    display_message("IoT_Health", "Finished!", False)
    
    return ('', 200)


@app.route('/run_ecg', methods=['POST'])
def run_ecg_script():
    display_message("IoT_Health", "Measuring ECG signals...", True)
        
    subprocess.run(['python3', ECG_SCRIPT], check=True)
    
    display_message("IoT_Health", "Finished!", False)
    return ('', 200)


@app.route('/run_max30102', methods=['POST'])
def run_max_script():
    display_message("IoT_Health", "Measuring SpO2...", True)
    
    subprocess.run(['python3', MAX30102_SCRIPT], check=True)
    
    display_message("IoT_Health", "Finished!", False)
    return ('', 200)


@app.route('/shutdown', methods=['POST'])
def shutdown():
    display_message("IoT_Health", "Shutting down...", True)
    time.sleep(5)
    
    subprocess.Popen(['python3', '/home/anna/kill_me.py'])
    return 'Το σύστημα κλείνει...'


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
