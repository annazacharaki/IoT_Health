import sqlite3

# Connect (or create) the database
conn = sqlite3.connect("/home/anna/health_database/health_data.db")

cursor = conn.cursor()

# Create a table for sensor measurements
cursor.execute("""
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    temperature REAL,
    bpm INTEGER,
    spo2 REAL
)
""")

conn.commit()
conn.close()
print("Database and table created successfully.")
