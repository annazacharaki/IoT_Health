import smbus2
import time

# I2C ρυθμίσεις
I2C_BUS = 1  # I2C δίαυλος του Raspberry Pi 5
MCP9808_ADDR = 0x18  # Προεπιλεγμένη διεύθυνση I2C του MCP9808
TEMP_REG = 0x05  # Καταχωρητής θερμοκρασίας

# Αρχικοποίηση I2C διαύλου
bus = smbus2.SMBus(I2C_BUS)

def configure_mcp9808():
    """Ρυθμίζει τον MCP9808 για μέγιστη ανάλυση (0.0625°C)."""
    try:
        # Ρύθμιση καταχωρητή Configuration (0x01) για συνεχή μέτρηση
        bus.write_word_data(MCP9808_ADDR, 0x01, 0x0000)
        # Ρύθμιση καταχωρητή Resolution (0x08) για 0.0625°C
        bus.write_byte_data(MCP9808_ADDR, 0x08, 0x03)
    except Exception as e:
        print(f"Σφάλμα ρύθμισης MCP9808: {e}")

def read_temperature():
    """Διαβάζει τη θερμοκρασία από τον MCP9808 σε °C."""
    try:
        # Διάβασε 2 bytes από τον καταχωρητή θερμοκρασίας
        data = bus.read_word_data(MCP9808_ADDR, TEMP_REG)
        # Μετατροπή δεδομένων (byte swap λόγω endianness)
        raw = ((data & 0xFF) << 8) | ((data >> 8) & 0xFF)
        # Έλεγχος σημαδιού (αρνητική θερμοκρασία)
        if raw & 0x1000:
            temp = -((raw & 0x0FFF) / 16.0)
        else:
            temp = (raw & 0x0FFF) / 16.0
        return temp
    except Exception as e:
        print(f"Σφάλμα ανάγνωσης θερμοκρασίας: {e}")
        return None

def main():
    """Κύρια συνάρτηση για συνεχή ανάγνωση θερμοκρασίας."""
    configure_mcp9808()
    print("Ανάγνωση θερμοκρασίας από MCP9808...")
    
    try:
        while True:
            temp = read_temperature()
            if temp is not None:
                print(f"Θερμοκρασία: {temp:.2f} °C")
            else:
                print("Αποτυχία ανάγνωσης θερμοκρασίας")
            time.sleep(1)  # Ανάγνωση κάθε 1 δευτερόλεπτο
    except KeyboardInterrupt:
        print("\nΠρόγραμμα τερματίστηκε από τον χρήστη")
    finally:
        bus.close()  # Κλείσε τον I2C δίαυλο

if __name__ == "__main__":
    main()
