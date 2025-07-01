import time
from max30102 import MAX30102

# Δημιουργία αντικειμένου με διεύθυνση 0x57 (default, αλλά το βάζουμε ρητά)
sensor = MAX30102()

print("Ανάγνωση παλμών από MAX30102 @0x57... Πατήστε Ctrl+C για έξοδο.")

try:
    while True:
        red, ir = sensor.read_sequential()
        if ir is not None and len(ir) > 0:
            print(f"IR (παλμοί): {ir[-1]} | Red: {red[-1]}")
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nΤέλος ανάγνωσης.")
