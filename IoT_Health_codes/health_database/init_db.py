import os
import sys
from dotenv import load_dotenv
import sqlite3

# Ensure parent directory is on path to find utils package
def add_parent_to_path():
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
add_parent_to_path()

from utils.encryption_utils import encrypt_field

# Load environment variables
load_dotenv()

# Path to the SQLite database (can override via env)
PARENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(PARENT_DIR, 'health_database', 'health_data.db')
)

def get_columns(cursor, table_name: str) -> list:
    """Return list of column names for given table."""
    cursor.execute(f"PRAGMA table_info({table_name});")
    return [row[1] for row in cursor.fetchall()]


def migrate_table(cursor, table: str, cols: list):
    """
    Migrate plaintext columns to encrypted BLOB columns for a specific table.
    cols: list of tuples (plain_col, encrypted_col)
    """
    old_table = f"{table}_old"
    new_table = table

    # Drop any leftover old_table from failed runs
    if cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (old_table,)).fetchone():
        cursor.execute(f"DROP TABLE {old_table};")

    # Get existing columns of new_table
    if cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (new_table,)).fetchone():
        existing = get_columns(cursor, new_table)
    else:
        existing = []

    # Determine if migration is needed (plain columns exist)
    plain_cols = [pc for pc, _ in cols]
    if not any(pc in existing for pc in plain_cols):
        print(f"Skipping {new_table}: no plaintext columns to migrate.")
        return

    # Rename current table to old
    cursor.execute(f"ALTER TABLE {new_table} RENAME TO {old_table};")

    # Create new schema with encrypted BLOB columns
    create_cols = ["id INTEGER PRIMARY KEY", "timestamp TEXT NOT NULL"] + [f"{enc} BLOB" for _, enc in cols]
    cursor.execute(f"CREATE TABLE {new_table} ({', '.join(create_cols)});")

    # Migrate and encrypt data
    sel_cols = ", ".join(plain_cols)
    cursor.execute(f"SELECT id, timestamp, {sel_cols} FROM {old_table};")
    for row in cursor.fetchall():
        id_, timestamp, *values = row
        enc_values = []
        for val, (pc, enc_col) in zip(values, cols):
            enc_values.append(encrypt_field(str(val).encode()) if val is not None else None)
        placeholders = ', '.join(['?'] * (2 + len(enc_values)))
        enc_cols_list = ', '.join([enc for _, enc in cols])
        cursor.execute(
            f"INSERT INTO {new_table} (id, timestamp, {enc_cols_list}) VALUES ({placeholders});",
            (id_, timestamp, *enc_values)
        )

    # Drop old table
    cursor.execute(f"DROP TABLE {old_table};")
    print(f"Migrated and encrypted table: {new_table}")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Define tables and columns for migration
    tables_to_migrate = {
        'temp_data': [('temp', 'enc_temp')],
        'ecg_data':  [('ecg',  'enc_ecg')],
        'spo2_data': [('spo2','enc_spo2')],
    }

    for table, cols in tables_to_migrate.items():
        migrate_table(cursor, table, cols)

    conn.commit()()
    conn.close()
    print("All migrations complete.")

if __name__ == '__main__':
    main()
