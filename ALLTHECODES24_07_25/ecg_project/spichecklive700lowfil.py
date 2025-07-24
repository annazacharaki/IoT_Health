import spidev
import time
import matplotlib.pyplot as plt
from collections import deque
from scipy.signal import butter, lfilter, iirnotch

# ---------- SPI SETUP ----------
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

def read_adc(channel):
    if channel < 0 or channel > 7:
        return -1
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc[1] & 3) << 8) + adc[2]

# ---------- FILTER SETUP ----------
Fs = 100  # Sampling Rate (Hz)
nyq = 0.5 * Fs

# Low-pass filter < 40Hz
low_cutoff = 40 / nyq
b_lp, a_lp = butter(2, low_cutoff, btype='low')

# Notch @ 50Hz (ρεύμα)
f0 = 50.0
Q = 30.0
b_notch, a_notch = iirnotch(f0 / nyq, Q)

def apply_filters(signal):
    # 1. Notch filter
    notch_filtered = lfilter(b_notch, a_notch, signal)
    # 2. Low-pass filter
    return lfilter(b_lp, a_lp, notch_filtered)

# ---------- PLOT SETUP ----------
window_size = 200
raw_data = deque([0]*window_size, maxlen=window_size)
filtered_data = deque([0]*window_size, maxlen=window_size)
x = list(range(window_size))

plt.ion()
fig, ax = plt.subplots()
raw_line, = ax.plot(x, raw_data, label="Raw", alpha=0.4)
filtered_line, = ax.plot(x, filtered_data, label="Filtered", color='blue')
ax.set_ylim(0, 1023)
ax.set_title("ECG Signal – Raw vs Filtered")
ax.set_ylabel("ADC Value")
ax.legend()

i = 0
max_samples = 700
print("Plotting filtered ECG (μέχρι 700 δείγματα)...")

try:
    while i < max_samples:
        value = read_adc(0)
        raw_data.append(value)
        
        # Apply filter
        filtered = apply_filters(list(raw_data))[-1]
        filtered_data.append(filtered)

        # Update plot
        raw_line.set_ydata(raw_data)
        filtered_line.set_ydata(filtered_data)
        fig.canvas.draw()
        fig.canvas.flush_events()

        time.sleep(0.01)
        i += 1

    print("Ολοκληρώθηκαν 700 δείγματα ✅")
    spi.close()
    plt.ioff()
    plt.show()

except KeyboardInterrupt:
    print("Τερματισμός με Ctrl+C")
    spi.close()
    plt.ioff()
    plt.show()
