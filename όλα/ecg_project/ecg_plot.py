import spidev
import time
import matplotlib.pyplot as plt
from collections import deque

# SPI setup
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1350000

# MCP3008 read
def read_channel(channel):
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((adc[1] & 3) << 8) + adc[2]
    return data

# Plotting setup
window_size = 200
data_buffer = deque([0]*window_size, maxlen=window_size)
x = list(range(window_size))

plt.ion()
fig, ax = plt.subplots()
line, = ax.plot(x, data_buffer)
ax.set_ylim(0, 1023)
ax.set_title("Live ECG Signal (CH0)")
ax.set_ylabel("ADC Value")

try:
    while True:
        value = read_channel(0)
        data_buffer.append(value)
        line.set_ydata(data_buffer)
        fig.canvas.draw()
        fig.canvas.flush_events()
        time.sleep(0.01)
except KeyboardInterrupt:
    spi.close()
    plt.ioff()
    plt.show()
