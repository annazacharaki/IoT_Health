import smbus2
import time
import sqlite3

# I2C ρυθμίσεις
I2C_BUS = 1  # I2C δίαυλος του Raspberry Pi 5
MCP9808_ADDR = 0x18  # Προεπιλεγμένη διεύθυνση I2C του MCP9808
TEMP_REG = 0x05  # Καταχωρητής θερμοκρασίας

# Database settings
DB_PATH = "/home/anna/health_database/health_data.db"

# Αρχικοποίηση I2C διαύλου
bus = smbus2.SMBus(I2C_BUS)

def configure_mcp9808():
    """Ρυθμίζει τον MCP9808 για μέγιστη ανάλυση (0.0625°C)."""
    try:
        bus.write_word_data(MCP9808_ADDR, 0x01, 0x0000)
        bus.write_byte_data(MCP9808_ADDR, 0x08, 0x03)
    except Exception as e:
        print(f"Σφάλμα ρύθμισης MCP9808: {e}")

def read_temperature():
    """Διαβάζει τη θερμοκρασία από τον MCP9808 σε °C."""
    try:
        data = bus.read_word_data(MCP9808_ADDR, TEMP_REG)
        raw = ((data & 0xFF) << 8) | ((data >> 8) & 0xFF)
        if raw & 0x1000:
            temp = -((raw & 0x0FFF) / 16.0)
        else:
            temp = (raw & 0x0FFF) / 16.0
        return temp
    except Exception as e:
        print(f"Σφάλμα ανάγνωσης θερμοκρασίας: {e}")
        return None

def save_temperature(temp):
    """Αποθηκεύει τη θερμοκρασία στον πίνακα temp_data."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO temp_data (timestamp, temp) VALUES (datetime('now'), ?)",
            (temp,),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Σφάλμα αποθήκευσης θερμοκρασίας: {e}")

def main():
    """Κύρια συνάρτηση για ανάγνωση θερμοκρασίας και τερματισμό μετά από 20 δείγματα."""
    configure_mcp9808()
    print("Ανάγνωση θερμοκρασίας από MCP9808 και αποθήκευση στη βάση...")

    count = 0
    try:
        while True:
            temp = read_temperature()
            if temp is not None:
                print(f"Θερμοκρασία: {temp:.2f} °C")
                save_temperature(temp)
            else:
                print("Αποτυχία ανάγνωσης θερμοκρασίας")

            count += 1
            if count >= 20:
                print("Έγιναν 20 μετρήσεις — τερματισμός.")
                break

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nΠρόγραμμα τερματίστηκε από τον χρήστη")
    finally:
        bus.close()

if __name__ == "__main__":
    main()
