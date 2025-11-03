import sys
import re
import time
import argparse
import math
import threading
from heartrate_monitor import HeartRateMonitor

# --- Capture the HeartRateMonitor prints without flooding the console ---
class _StdoutProxy:
    """
    Intercepts lines like: 'BPM: 71.0, SpO2: 99.52'
    and optional 'No finger' messages from the HeartRateMonitor thread,
    stores last values, and suppresses those lines from the console.
    """
    LINE_RE = re.compile(r"\bBPM:\s*([0-9.]+)\s*,\s*SpO2:\s*([0-9.\-NaN]+)", re.IGNORECASE)
    NO_FINGER_RE = re.compile(r"no\s*finger", re.IGNORECASE)

    def __init__(self, real_out):
        self.real_out = real_out
        self.buf = ""
        self.lock = threading.Lock()
        self.last_bpm = None
        self.last_spo2 = None
        self.no_finger = False

    def write(self, s):
        # Accumulate and parse by lines
        self.buf += s
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            self._handle_line(line)

    def flush(self):
        pass  # nothing to flush

    def _handle_line(self, line):
        # Detect "no finger" style messages
        if self.NO_FINGER_RE.search(line):
            with self.lock:
                self.no_finger = True
        # Parse 'BPM: x, SpO2: y'
        m = self.LINE_RE.search(line)
        if m:
            try:
                bpm = float(m.group(1))
            except Exception:
                bpm = None
            try:
                spo2 = float(m.group(2))
            except Exception:
                spo2 = None
            with self.lock:
                self.last_bpm = bpm
                self.last_spo2 = spo2
                # αν ήρθε κανονική μέτρηση, σβήσε το no_finger flag
                if bpm is not None or spo2 is not None:
                    self.no_finger = False
            # DO NOT forward this line => suppress flood
            return
        # Forward any unrelated lines (e.g., startup/shutdown)
        if line.strip() and not self.LINE_RE.search(line):
            print(line, file=self.real_out, flush=True)

    # helpers to read the last values safely
    def snapshot(self):
        with self.lock:
            return self.last_bpm, self.last_spo2, self.no_finger

# --- Utilities ---
def _to_int_or_zero(val, lo, hi):
    try:
        if val is None:
            return 0
        v = float(val)
        if not math.isfinite(v):
            return 0
        iv = int(round(v))
        if iv < lo or iv > hi:
            return 0
        return iv
    except Exception:
        return 0

# --- Args ---
parser = argparse.ArgumentParser(description="Read and print data from MAX30102")
parser.add_argument("-t", "--time", type=int, default=30,
                    help="duration in seconds to read from sensor, default 30")
args = parser.parse_args()

# --- Install proxy to capture HeartRateMonitor prints ---
_real_stdout = sys.stdout  # keep the real stdout
_proxy = _StdoutProxy(_real_stdout)
sys.stdout = _proxy  # redirect prints from HR thread to our proxy

print("sensor starting...")  # will be forwarded by proxy

# Start HeartRateMonitor exactly as before (no internal changes)
# Keep its own printing ON so computations run as in your original code.
hrm = HeartRateMonitor(print_raw=False, print_result=True)
hrm.start_sensor()

# Main loop: print once per second (to real stdout), integers, SpO2=0 if no finger.
t_end = time.time() + args.time
last_tick = 0.0
try:
    while time.time() < t_end:
        now = time.time()
        if now - last_tick >= 1.0:
            bpm_f, spo2_f, no_finger = _proxy.snapshot()

            # BPM: integer 0..220 (0 already used by your code when no pulse)
            bpm_i = _to_int_or_zero(bpm_f, lo=0, hi=220)

            # SpO2 rule:
            # - If 'no finger' flagged => 0
            # - Else round to integer 0..100 (invalid/NaN/out-of-range => 0)
            if no_finger:
                spo2_i = 0
            else:
                spo2_i = _to_int_or_zero(spo2_f, lo=0, hi=100)

            print(f"BPM: {bpm_i} | SpO2: {spo2_i}", file=_real_stdout, flush=True)
            last_tick = now

        time.sleep(0.01)

except KeyboardInterrupt:
    print("keyboard interrupt detected, exiting...", file=_real_stdout, flush=True)

# Restore stdout before stopping sensor (so stop messages show)
sys.stdout = _real_stdout
hrm.stop_sensor()
print("sensor stoped!", flush=True)
