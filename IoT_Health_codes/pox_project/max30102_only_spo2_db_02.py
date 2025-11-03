#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import time
import math
import threading
import argparse
import sqlite3

# ---------- PATH / IMPORTS ----------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Χρησιμοποιούμε την ίδια κρυπτογράφηση & DB όπως στο max30102_only_spo2_db.py
from utils.encryption_utils import encrypt_field  # same as original
from heartrate_monitor import HeartRateMonitor    # measurement like main_03.py

# ---------- DATABASE ----------
DB_PATH = "/home/anna/health_database/health_data.db"

def save_spo2(spo2_int: int):
    """
    Αποθηκεύει ΜΟΝΟ λογικές μετρήσεις SpO2 (1..100) στον πίνακα spo2_data,
    κρυπτογραφημένες όπως στο αρχικό script.
    """
    if not (1 <= spo2_int <= 100):
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        blob = encrypt_field(str(spo2_int).encode())
        cur.execute(
            "INSERT INTO spo2_data (timestamp, enc_spo2) VALUES (datetime('now','localtime'), ?)",
            (blob,),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Σφάλμα αποθήκευσης SpO2: {e}")

# ---------- STDOUT PROXY (όπως στο main_03 measurement) ----------
class _StdoutProxy:
    """
    Παγιδεύει γραμμές τύπου: 'BPM: 71.0, SpO2: 99.52'
    και μηνύματα 'no finger' από το thread του HeartRateMonitor.
    Κρατά τις τελευταίες τιμές και δεν τις ξανατυπώνει (για να τυπώνουμε 1Hz).
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
        self.buf += s
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            self._handle_line(line)

    def flush(self):
        pass

    def _handle_line(self, line):
        if self.NO_FINGER_RE.search(line):
            with self.lock:
                self.no_finger = True

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
                if bpm is not None or spo2 is not None:
                    self.no_finger = False
            # καταπίνουμε τη γραμμή (δεν την τυπώνουμε)
            return

        # οτιδήποτε άλλο μήνυμα επιτρέπεται να περάσει
        if line.strip() and not self.LINE_RE.search(line):
            print(line, file=self.real_out, flush=True)

    def snapshot(self):
        with self.lock:
            return self.last_bpm, self.last_spo2, self.no_finger

# ---------- HELPERS ----------
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

# ---------- MAIN ----------
def main():
    parser = argparse.ArgumentParser(description="MAX30102 SpO2 -> encrypted SQLite (20 samples default)")
    parser.add_argument("-t", "--time", type=int, default=20,
                        help="duration in seconds to read from sensor, default 20")
    args = parser.parse_args()

    # Εγκατάσταση proxy stdout ώστε να πάρουμε τις τιμές από το HeartRateMonitor σαν στο main_03.py
    real_stdout = sys.stdout
    proxy = _StdoutProxy(real_stdout)
    sys.stdout = proxy

    print("Reading SpO2 (1Hz) and storing valid values to DB... (stops after default 20s)")
    print("Place the sensor on your finger and keep steady.")

    # Εκκίνηση HeartRateMonitor με print_result=True (όπως στο main_03)
    hrm = HeartRateMonitor(print_raw=False, print_result=True)
    hrm.start_sensor()

    t_end = time.time() + args.time
    last_tick = 0.0
    saved = 0

    try:
        while time.time() < t_end:
            now = time.time()
            if now - last_tick >= 1.0:
                bpm_f, spo2_f, no_finger = proxy.snapshot()

                # BPM δεν αποθηκεύεται εδώ – μόνο SpO2.
                # Κανόνας SpO2 όπως στο main_03: 0 όταν no finger, αλλιώς στρογγυλοποίηση και clamp 0..100.
                if no_finger:
                    spo2_i = 0
                else:
                    spo2_i = _to_int_or_zero(spo2_f, lo=0, hi=100)

                # Αποθήκευση ΜΟΝΟ λογικών (1..100), όπως ζητήθηκε
                if 1 <= spo2_i <= 100:
                    save_spo2(spo2_i)
                    saved += 1

                # Προαιρετικό ενημερωτικό (1Hz) για τον χρήστη
                print(f"SpO2 snapshot: {spo2_i} (saved: {saved})", file=real_stdout, flush=True)

                last_tick = now

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopped by user.", file=real_stdout, flush=True)
    finally:
        # Επαναφορά stdout για να φανούν τα τελικά μηνύματα
        sys.stdout = real_stdout
        hrm.stop_sensor()
        print(f"Done. Stored {saved} valid SpO2 value(s) to DB.", flush=True)

if __name__ == "__main__":
    main()
