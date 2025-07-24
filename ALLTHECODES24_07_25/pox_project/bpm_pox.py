import time
import numpy as np
from max30102 import MAX30102
from scipy.signal import find_peaks

sensor = MAX30102()

print("Ανάγνωση παλμών & υπολογισμός BPM... Πατήστε Ctrl+C για έξοδο.")

ir_values = []
timestamps = []
sample_duration = 10  # δευτερόλεπτα μέτρησης

try:
    print(f"Μέτρηση για {sample_duration} δευτερόλεπτα...")

    start_time = time.time()
    while time.time() - start_time < sample_duration:
        red, ir = sensor.read_sequential()
        if ir is not None and len(ir) > 0:
            ir_values.extend(ir)
            timestamps.extend([time.time()] * len(ir))
        time.sleep(0.1)

    print(f"Συνολικά δείγματα: {len(ir_values)}")

    # Εντοπισμός peaks
    ir_array = np.array(ir_values)
    peaks, _ = find_peaks(ir_array, distance=30, prominence=5000)

    peak_times = [timestamps[i] for i in peaks]
    intervals = np.diff(peak_times)

    if len(intervals) > 0:
        avg_interval = np.mean(intervals)
        bpm = 60 / avg_interval
        print(f"💓 Υπολογισμένο BPM: {int(bpm)}")
    else:
        print("❌ Δεν εντοπίστηκαν αρκετά peaks για BPM.")

except KeyboardInterrupt:
    print("\nΔιακοπή μέτρησης.")
