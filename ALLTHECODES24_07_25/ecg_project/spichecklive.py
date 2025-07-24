import spidev
import time
import matplotlib.pyplot as plt
from collections import deque

# SPI setup
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

def read_adc(channel):
    if channel < 0 or channel > 7:
        return -1
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((adc[1] & 3) << 8) + adc[2]
    return data

# Plot setup
window_size = 200
data_buffer = deque([0]*window_size, maxlen=window_size)
x = list(range(window_size))

plt.ion()
fig, ax = plt.subplots()
line, = ax.plot(x, data_buffer)
ax.set_ylim(0, 1023)
ax.set_title("Live ECG/ADC Plot")
ax.set_ylabel("ADC Value")

try:
    print("Plotting live data από CH0... Πατήστε Ctrl+C για έξοδο.")
    while True:
        value = read_adc(0)
        voltage = value * 3.3 / 1023
        print(f"ADC: {value} | Voltage: {voltage:.2f} V")
        
        data_buffer.append(value)
        line.set_ydata(data_buffer)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.05)  # λίγο πιο χαλαρό για να διαβάζεις τα νούμερα
except KeyboardInterrupt:
    print("Τερματισμός...")
    spi.close()
    plt.ioff()
    plt.show()
