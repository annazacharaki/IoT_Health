import sqlite3
from datetime import datetime

def insert_measurement(temperature=None, bpm=None, spo2=None):
    """Εισάγει μία μέτρηση στη βάση δεδομένων health_data.db"""
    try:
        conn = sqlite3.connect("/home/anna/health_database/health_data.db")

        cursor = conn.cursor()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO measurements (timestamp, temperature, bpm, spo2)
            VALUES (?, ?, ?, ?)
        """, (timestamp, temperature, bpm, spo2))

        conn.commit()
        conn.close()
        print(f"✅ Inserted: Temp={temperature}, BPM={bpm}, SpO₂={spo2} at {timestamp}")
    except Exception as e:
        print(f"❌ Database insert error: {e}")
