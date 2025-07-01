import time
import numpy as np
from max30102 import MAX30102
from scipy.signal import butter, lfilter
from collections import deque

# ---------- SENSOR SETUP ----------
try:
    sensor = MAX30102()  # Use default I2C address
except Exception as e:
    print(f"Error initializing MAX30102: {e}")
    exit(1)

# ---------- FILTER SETUP ----------
Fs = 100  # Sampling rate (Hz, based on MAX30102 default)
nyq = 0.5 * Fs
low_cutoff = 4.0 / nyq  # Increased to 4 Hz to capture more pulse signal
b, a = butter(2, low_cutoff, btype='low')

def apply_lowpass(signal):
    return lfilter(b, a, signal)

# ---------- SIGNAL QUALITY CHECK ----------
def check_signal_quality(ir_data, min_variation=500):
    """Check if IR signal has enough variation for pulse detection."""
    if len(ir_data) < 10:
        return False
    variation = np.max(ir_data) - np.min(ir_data)
    return variation > min_variation

# ---------- BPM & SpO2 CALCULATION ----------
def calculate_bpm(ir_data, sample_rate=100, window_size=50):
    """Calculate heart rate (BPM) from IR data using peak detection."""
    if len(ir_data) < window_size:
        print(f"Debug: Not enough data, {len(ir_data)}/{window_size} samples")
        return None
    
    # Check signal quality
    if not check_signal_quality(ir_data):
        print("Debug: Signal variation too low, check sensor placement")
        return None
    
    # Apply low-pass filter
    filtered_ir = apply_lowpass(ir_data)
    
    # Simple peak detection: Find local maxima
    peaks = []
    threshold = np.mean(filtered_ir) + 0.2 * np.std(filtered_ir)  # Even lower threshold
    for i in range(1, len(filtered_ir) - 1):
        if filtered_ir[i] > filtered_ir[i-1] and filtered_ir[i] > filtered_ir[i+1] and filtered_ir[i] > threshold:
            peaks.append(i)
    
    print(f"Debug: Found {len(peaks)} peaks")
    
    # Calculate average time between peaks
    if len(peaks) < 2:
        return None
    
    peak_intervals = np.diff(peaks) / sample_rate  # Time between peaks in seconds
    avg_interval = np.mean(peak_intervals)
    bpm = 60 / avg_interval
    return round(bpm, 1)

def calculate_spo2(red_data, ir_data, window_size=50):
    """Calculate SpO2 using ratio of ratios method."""
    if len(red_data) < window_size or len(ir_data) < window_size:
        print(f"Debug: Not enough data for SpO2, Red: {len(red_data)}/{window_size}, IR: {len(ir_data)}/{window_size}")
        return None
    
    # Check signal quality
    if not check_signal_quality(ir_data) or not check_signal_quality(red_data):
        print("Debug: Signal variation too low for SpO2, check sensor placement")
        return None
    
    # Apply low-pass filter
    red_filtered = apply_lowpass(red_data)
    ir_filtered = apply_lowpass(ir_data)
    
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
    
    # Empirical SpO2 formula (simplified)
    spo2 = 110 - 25 * R
    spo2 = min(100, max(0, spo2))  # Clamp between 0 and 100
    return round(spo2, 1)

# ---------- DATA STORAGE ----------
window_size = 50  # Reduced to 50 samples (0.5 seconds)
ir_data = deque(maxlen=window_size)
red_data = deque(maxlen=window_size)

# ---------- MAIN LOOP ----------
print("Reading pulse and SpO2 from MAX30102... Press Ctrl+C to exit.")
print("Place the sensor firmly on your finger and keep it steady for at least 5 seconds.")
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
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nStopped reading.")
finally:
    sensor.shutdown()  # Properly close the sensor
