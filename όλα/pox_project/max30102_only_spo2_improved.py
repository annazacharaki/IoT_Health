import time
import numpy as np
from max30102 import MAX30102
from scipy.signal import butter, lfilter
from collections import deque

# ---------- SENSOR SETUP ----------
Fs = 100  # Sampling rate (Hz)
try:
    sensor = MAX30102()
except Exception as e:
    print(f"Error initializing MAX30102: {e}")
    exit(1)

# ---------- FILTER SETUP ----------
nyq = 0.5 * Fs
low_cutoff = 5.0 / nyq  # Low-pass filter cutoff frequency (5 Hz)
b, a = butter(2, low_cutoff, btype='low')

def apply_lowpass(signal):
    return lfilter(b, a, signal)

# ---------- SIGNAL QUALITY CHECK ----------
def check_signal_quality(ir_data, red_data, min_variation=500, min_value=10000):
    """Check if IR and Red signals are valid with enough variation."""
    if len(ir_data) < 5 or len(red_data) < 5:
        return False
    ir_variation = np.max(ir_data) - np.min(ir_data)
    red_variation = np.max(red_data) - np.min(red_data)
    ir_mean = np.mean(ir_data)
    red_mean = np.mean(red_data)
    return (ir_variation > min_variation and red_variation > min_variation and
            ir_mean > min_value and red_mean > min_value)

# ---------- SpO2 CALCULATION ----------
def calculate_spo2(red_data, ir_data):
    """Calculate SpO2 using the ratio of ratios method."""
    red_filtered = apply_lowpass(red_data)
    ir_filtered = apply_lowpass(ir_data)

    ac_red = np.max(red_filtered) - np.min(red_filtered)
    dc_red = np.mean(red_filtered)
    ac_ir = np.max(ir_filtered) - np.min(ir_filtered)
    dc_ir = np.mean(ir_filtered)

    if dc_red == 0 or dc_ir == 0 or ac_ir == 0:
        return None

    R = (ac_red / dc_red) / (ac_ir / dc_ir)
    spo2 = 109 - 9 * R
    spo2 = min(100, max(90, spo2))  # Clamp between 90% and 100%
    return round(spo2, 1)

# ---------- MAIN LOOP ----------
print("Place your finger on the sensor. Collecting samples...")

window_size = 30  # 30 samples (0.3 sec real time if Fs=100Hz)
ir_data = deque(maxlen=window_size)
red_data = deque(maxlen=window_size)

try:
    start_time = time.time()

    while True:
        red, ir = sensor.read_sequential()
        if ir is not None and len(ir) > 0 and red is not None and len(red) > 0:
            ir_data.append(ir[-1])
            red_data.append(red[-1])

            print(f"Collecting data... {len(ir_data)}/{window_size} samples", end='\r')

        if len(ir_data) >= window_size and len(red_data) >= window_size:
            print("\nFinished collecting samples.")

            if check_signal_quality(list(ir_data), list(red_data)):
                spo2 = calculate_spo2(list(red_data), list(ir_data))
                if spo2:
                    print(f"✅ SpO₂: {spo2}%")
                else:
                    print("⚠️ Could not calculate SpO₂ reliably. Try again.")
            else:
                print("⚠️ Poor signal quality. Please adjust your finger and retry.")

            break  # Exit after 1 measurement

        time.sleep(0.05)  # Slight pause for smoother reading

except KeyboardInterrupt:
    print("\nMeasurement stopped by user.")
finally:
    sensor.shutdown()
