import time
import numpy as np
from max30102 import MAX30102
from scipy.signal import butter, lfilter
from collections import deque
import sqlite3

# ---------- SENSOR SETUP ----------
Fs = 100  # Sampling rate (Hz, based on MAX30102 default)
try:
    sensor = MAX30102()
except Exception as e:
    print(f"Error initializing MAX30102: {e}")
    exit(1)

# ---------- FILTER SETUP ----------
nyq = 0.5 * Fs
low_cutoff = 5.0 / nyq
b, a = butter(2, low_cutoff, btype='low')

def apply_lowpass(signal):
    return lfilter(b, a, signal)

def check_signal_quality(ir_data, red_data, min_variation=1000, min_value=20000):
    if len(ir_data) < 5 or len(red_data) < 5:
        return False
    ir_variation = np.max(ir_data) - np.min(ir_data)
    red_variation = np.max(red_data) - np.min(red_data)
    ir_mean = np.mean(ir_data)
    red_mean = np.mean(red_data)
    return (ir_variation > min_variation and red_variation > min_variation and
            ir_mean > min_value and red_mean > min_value)

def calculate_spo2(red_data, ir_data, window_size=20):
    if len(red_data) < window_size or len(ir_data) < window_size:
        print(f"Debug: Not enough data for SpO2, Red: {len(red_data)}/{window_size}, IR: {len(ir_data)}/{window_size}")
        return None

    if not check_signal_quality(ir_data, red_data):
        print("Debug: Signal invalid (low variation or sensor not on finger)")
        return None

    red_filtered = apply_lowpass(red_data)
    ir_filtered = apply_lowpass(ir_data)

    ac_red = np.max(red_filtered) - np.min(red_filtered)
    dc_red = np.mean(red_filtered)
    ac_ir = np.max(ir_filtered) - np.min(ir_filtered)
    dc_ir = np.mean(ir_filtered)

    if dc_red == 0 or dc_ir == 0 or ac_ir == 0:
        print("Debug: Invalid AC/DC values for SpO2")
        return None

    R = (ac_red / dc_red) / (ac_ir / dc_ir)
    spo2 = 109 - 9 * R
    spo2 = min(100, max(90, spo2))
    return round(spo2, 1)

# ---------- DATABASE SETUP ----------
DB_PATH = "/home/anna/health_database/health_data.db"

def save_spo2(spo2):
    """Αποθηκεύει το SpO2 στον πίνακα spo2_data."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO spo2_data (timestamp, spo2) VALUES (datetime('now'), ?)",
            (spo2,),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Σφάλμα αποθήκευσης SpO2: {e}")

# ---------- DATA STORAGE ----------
window_size = 20
ir_data = deque(maxlen=window_size)
red_data = deque(maxlen=window_size)

# ---------- MAIN LOOP ----------
print("Reading SpO2 from MAX30102... (will stop after 20 samples)")
print("Place the sensor firmly on your finger and keep it steady for 2-3 seconds.")

count = 0
max_samples = 20

try:
    while True:
        red, ir = sensor.read_sequential()
        if ir is not None and len(ir) > 0 and red is not None and len(red) > 0:
            ir_data.append(ir[-1])
            red_data.append(red[-1])

            spo2 = calculate_spo2(list(red_data), list(ir_data), window_size)

            if spo2 is not None:
                print(f"IR: {ir[-1]} | Red: {red[-1]} | SpO2: {spo2}%")
                save_spo2(spo2)
            else:
                print(f"IR: {ir[-1]} | Red: {red[-1]} | ❌ No valid SpO₂")

            count += 1
            if count >= max_samples:
                print(f"\nReached {max_samples} samples — stopping.")
                break

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    sensor.shutdown()
