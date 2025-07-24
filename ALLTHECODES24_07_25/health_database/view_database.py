import sqlite3

def show_all_data():
    conn = sqlite3.connect("/home/anna/health_database/health_data.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM measurements ORDER BY timestamp DESC")
    rows = cursor.fetchall()

    print(" Περιεχόμενο πίνακα 'measurements':")
    print("-" * 60)
    for row in rows:
        print(f" {row[1]} | {row[2]} °C | {row[3]} BPM |🫁 SpO₂: {row[4]}%")

    conn.close()

if __name__ == "__main__":
    show_all_data()
