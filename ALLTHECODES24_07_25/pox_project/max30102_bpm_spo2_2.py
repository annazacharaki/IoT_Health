import time
import numpy as np
from max30102 import MAX30102
from scipy.signal import find_peaks
from collections import deque

# ---------- SENSOR SETUP ----------
Fs = 100  # Sampling rate (Hz, based on MAX30102 default)
try:
    sensor = MAX30102()  # Use default I2C address
except Exception as e:
    print(f"Error initializing MAX30102: {e}")
    exit(1)

# ---------- SIGNAL QUALITY CHECK ----------
def check_signal_quality(ir_data, min_variation=800, min_value=20000):
    """Check if IR signal is valid and has enough variation."""
    if len(ir_data) < 5:
        return False
    variation = np.max(ir_data) - np.min(ir_data)
    mean_value = np.mean(ir_data)
    return variation > min_variation and mean_value > min_value

# ---------- BPM & SpO2 CALCULATION ----------
def calculate_bpm(ir_data, sample_rate=100, window_size=30):
    """Calculate heart rate (BPM) from IR data using peak detection."""
    if len(ir_data) < window_size:
        print(f"Debug: Not enough data, {len(ir_data)}/{window_size} samples")
        return None
    
    # Check signal quality
    if not check_signal_quality(ir_data):
        print("Debug: Signal invalid (low variation or sensor not on finger)")
        return None
    
    # Use raw signal (no filtering)
    signal = np.array(ir_data)
    
    # Debug: Print signal variation
    variation = np.max(signal) - np.min(signal)
    print(f"Debug: IR variation: {variation}")
    print(f"Debug: Raw IR: {signal[-5:]}")  # Last 5 values
    
    # Peak detection using scipy.signal.find_peaks
    peaks, _ = find_peaks(signal, distance=0.2*sample_rate, height=np.mean(signal) - 0.4 * np.std(signal))
    
    print(f"Debug: Found {len(peaks)} peaks")
    print(f"Debug: Peaks indices: {peaks}")  # Debug peak positions
    
    # Calculate average time between peaks
    if len(peaks) < 2:
        return None
    
    peak_intervals = np.diff(peaks) / sample_rate  # Time between peaks in seconds
    avg_interval = np.mean(peak_intervals)
    if avg_interval < 0.3:  # Avoid unrealistic BPM (>200)
        print("Debug: Peaks too close, likely noise")
        return None
    bpm = 60 / avg_interval
    if bpm > 150 or bpm < 40:  # Restrict to realistic range
        print("Debug: BPM out of realistic range")
        return None
    return round(bpm, 1)

def calculate_spo2(red_data, ir_data, window_size=30):
    """Calculate SpO2 using ratio of ratios method."""
    if len(red_data) < window_size or len(ir_data) < window_size:
        print(f"Debug: Not enough data for SpO2, Red: {len(red_data)}/{window_size}, IR: {len(ir_data)}/{window_size}")
        return None
    
    # Check signal quality
    if not check_signal_quality(ir_data) or not check_signal_quality(red_data):
        print("Debug: Signal invalid for SpO2 (low variation or sensor not on finger)")
        return None
    
    # Use raw signal (no filtering)
    red_signal = np.array(red_data)
    ir_signal = np.array(ir_data)
    
    # Calculate AC and DC components
    ac_red = np.max(red_signal) - np.min(red_signal)
    dc_red = np.mean(red_signal)
    ac_ir = np.max(ir_signal) - np.min(ir_signal)
    dc_ir = np.mean(ir_signal)
    
    # Avoid division by zero
    if dc_red == 0 or dc_ir == 0 or ac_ir == 0:
        print("Debug: Invalid AC/DC values for SpO2")
        return None
    
    # Calculate ratio of ratios
    R = (ac_red / dc_red) / (ac_ir / dc_ir)
    
    # Adjusted SpO2 formula for better accuracy
    spo2 = 108 - 10 * R  # Adjusted coefficients
    spo2 = min(100, max(90, spo2))  # Clamp between 90 and 100
    return round(spo2, 1)

# ---------- DATA STORAGE ----------
window_size = 20  # 0.2 seconds
ir_data = deque(maxlen=window_size)
red_data = deque(maxlen=window_size)

# ---------- MAIN LOOP ----------
print("Reading pulse and SpO2 from MAX30102... Press Ctrl+C to exit.")
print("Place the sensor firmly on your finger and keep it steady for 3-5 seconds.")
try:
    while True:
        red, ir = sensor.read_sequential()
        if ir is not None and len(ir) > 0 and red is not None and len(red) > 0:
            ir_data.append(ir[-1])
            red_data.append(red[-1])
            
            # Calculate BPM and SpO2
            bpm = calculate_bpm(list(ir_data), Fs, window_size)
            spo2 = calculate_spo2(list(red_data), list(ir_data), window_size)
            
            # Print results
            print(f"IR: {ir[-1]} | Red: {red[-1]}", end="")
            if bpm is not None:
                print(f" | BPM: {bpm}", end="")
            if spo2 is not None:
                print(f" | SpO2: {spo2}%", end="")
            print()

except KeyboardInterrupt:
    print("\nStopped reading.")
finally:
    sensor.shutdown()  # Properly close the sensor
