from heartrate_monitor import HeartRateMonitor
import time
import argparse
import math

def _clean_int(val, lo=0, hi=200):
    """Round to nearest int if finite and in range, else 0."""
    try:
        if val is None:
            return 0
        if not math.isfinite(float(val)):
            return 0
        ival = int(round(float(val)))
        if ival < lo or ival > hi:
            return 0
        return ival
    except Exception:
        return 0

parser = argparse.ArgumentParser(description="Read and print data from MAX30102")
parser.add_argument("-r", "--raw", action="store_true",
                    help="(ignored) raw streaming is disabled to print once per second")
parser.add_argument("-t", "--time", type=int, default=30,
                    help="duration in seconds to read from sensor, default 30")
args = parser.parse_args()

print('sensor starting...')

# Σβήνουμε τα εσωτερικά prints για να τυπώνουμε εμείς ανά 1s.
hrm = HeartRateMonitor(print_raw=False, print_result=False)
hrm.start_sensor()

t_end = time.time() + args.time
last_print = 0.0
try:
    while time.time() < t_end:
        now = time.time()
        if now - last_print >= 1.0:
            # Διαβάζουμε τις τρέχουσες τιμές από το αντικείμενο
            bpm  = getattr(hrm, "bpm", 0)
            spo2 = getattr(hrm, "spo2", 0)

            # BPM: αν δεν ανιχνεύει παλμούς, ο υπάρχων κώδικας το έχει 0 — το κρατάμε.
            bpm_int = _clean_int(bpm, lo=0, hi=220)

            # SpO2: αν δεν υπάρχει δάχτυλο/άκυρη μέτρηση, εμφανίζουμε 0
            # Συνηθισμένα sentinel από υλοποιήσεις: -999, None, NaN, >100, <=0.
            spo2_int = _clean_int(spo2, lo=0, hi=100)

            print(f"BPM: {bpm_int} | SpO2: {spo2_int}")
            last_print = now

        time.sleep(0.01)
except KeyboardInterrupt:
    print('keyboard interrupt detected, exiting...')

hrm.stop_sensor()
print('sensor stoped!')
