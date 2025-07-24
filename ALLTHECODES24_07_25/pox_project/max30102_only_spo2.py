import time
import numpy as np
from max30102 import MAX30102
from scipy.signal import butter, lfilter
from collections import deque

# ---------- SENSOR SETUP ----------
Fs = 100  # Sampling rate (Hz, based on MAX30102 default)
try:
    sensor = MAX30102()  # Use default I2C address
except Exception as e:
    print(f"Error initializing MAX30102: {e}")
    exit(1)

# ---------- FILTER SETUP ----------
nyq = 0.5 * Fs
low_cutoff = 5.0 / nyq  # Low-pass at 5 Hz
b, a = butter(2, low_cutoff, btype='low')

def apply_lowpass(signal):
    return lfilter(b, a, signal)

# ---------- SIGNAL QUALITY CHECK ----------
def check_signal_quality(ir_data, red_data, min_variation=1000, min_value=20000):
    """Check if IR and Red signals are valid and have enough variation."""
    if len(ir_data) < 5 or len(red_data) < 5:
        return False
    ir_variation = np.max(ir_data) - np.min(ir_data)
    red_variation = np.max(red_data) - np.min(red_data)
    ir_mean = np.mean(ir_data)
    red_mean = np.mean(red_data)
    return (ir_variation > min_variation and red_variation > min_variation and
            ir_mean > min_value and red_mean > min_value)

# ---------- SpO2 CALCULATION ----------
def calculate_spo2(red_data, ir_data, window_size=20):
    """Calculate SpO2 using ratio of ratios method."""
    if len(red_data) < window_size or len(ir_data) < window_size:
        print(f"Debug: Not enough data for SpO2, Red: {len(red_data)}/{window_size}, IR: {len(ir_data)}/{window_size}")
        return None
    
    # Check signal quality
    if not check_signal_quality(ir_data, red_data):
        print("Debug: Signal invalid (low variation or sensor not on finger)")
        return None
    
    # Apply low-pass filter
    red_filtered = apply_lowpass(red_data)
    ir_filtered = apply_lowpass(ir_data)
    
    # Debug: Print signal variation
    ir_variation = np.max(ir_data) - np.min(ir_data)
    red_variation = np.max(red_data) - np.min(red_data)
    print(f"Debug: IR variation: {ir_variation}, Red variation: {red_variation}")
    print(f"Debug: Filtered IR: {ir_filtered[-5:]}")  # Last 5 values
    
    # Calculate AC and DC components
    ac_red = np.max(red_filtered) - np.min(red_filtered)
    dc_red = np.mean(red_filtered)
    ac_ir = np.max(ir_filtered) - np.min(ir_filtered)
    dc_ir = np.mean(ir_filtered)
    
    # Avoid division by zero
    if dc_red == 0 or dc_ir == 0 or ac_ir == 0:
        print("Debug: Invalid AC/DC values for SpO2")
        return None
    
    # Calculate ratio of ratios
    R = (ac_red / dc_red) / (ac_ir / dc_ir)
    
    # Adjusted SpO2 formula for stability
    spo2 = 109 - 9 * R  # Adjusted coefficients
    spo2 = min(100, max(90, spo2))  # Clamp between 90 and 100
    return round(spo2, 1)

# ---------- DATA STORAGE ----------
window_size = 20  # 0.2 seconds
ir_data = deque(maxlen=window_size)
red_data = deque(maxlen=window_size)

# ---------- MAIN LOOP ----------
print("Reading SpO2 from MAX30102... Press Ctrl+C to exit.")
print("Place the sensor firmly on your finger and keep it steady for 2-3 seconds.")
try:
    while True:
        red, ir = sensor.read_sequential()
        if ir is not None and len(ir) > 0 and red is not None and len(red) > 0:
            ir_data.append(ir[-1])
            red_data.append(red[-1])
            
            # Calculate SpO2
            spo2 = calculate_spo2(list(red_data), list(ir_data), window_size)
            
            # Print results
            print(f"IR: {ir[-1]} | Red: {red[-1]}", end="")
            if spo2 is not None:
                print(f" | SpO2: {spo2}%", end="")
            print()

except KeyboardInterrupt:
    print("\nStopped reading.")
finally:
    sensor.shutdown()  # Properly close the sensor
