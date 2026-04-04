"""
Smart Parking System - Hardware Abstraction Layer
Provides clean interfaces for all hardware components
"""

from machine import Pin, PWM, I2C, SPI
import time


# ═══════════════════════════════════════════════════
# RFID Reader
# ═══════════════════════════════════════════════════

class RFIDReader:
    """
    Abstraction for MFRC522 RFID reader
    Handles card detection and UID reading
    """
    
    def __init__(self, spi_bus: int, sck: Pin, mosi: Pin, miso: Pin, cs: Pin, rst: Pin):
        """
        Initialize RFID reader with SPI configuration
        
        Args:
            spi_bus: SPI bus number (1 or 2)
            sck: SPI clock pin
            mosi: SPI MOSI pin
            miso: SPI MISO pin
            cs: Chip select pin
            rst: Reset pin
        """
        # Import MFRC522 library
        from mfrc522 import MFRC522
        
        # Initialize SPI bus
        self.spi = SPI(spi_bus, baudrate=1_000_000, polarity=0, phase=0,
                      sck=sck, mosi=mosi, miso=miso)
        
        # Initialize MFRC522 reader
        self.reader = MFRC522(self.spi, cs, rst)
    
    def get_version(self) -> int:
        """
        Get MFRC522 chip version
        
        Returns:
            Version number from chip register
        """
        return self.reader.version()
    
    def scan(self) -> str:
        """
        Scan for RFID card and return UID
        
        Returns:
            Card UID as hex string with "0x" prefix (e.g., "0xa3d6ce05")
            None if no card detected or error occurred
        """
        try:
            # Request card
            stat, _ = self.reader.request(self.reader.REQIDL)
            if stat != self.reader.OK:
                return None
            
            # Get card UID
            stat, uid = self.reader.anticoll()
            if stat != self.reader.OK:
                return None
            
            # Format UID as hex string with "0x" prefix
            uid_hex = "0x" + "".join(["{:02x}".format(b) for b in uid])
            
            return uid_hex
            
        except Exception:
            return None
    
    def halt(self) -> None:
        """
        Halt the RFID reader to stop communication with card
        """
        self.reader.halt()


# ═══════════════════════════════════════════════════
# Ultrasonic Sensor
# ═══════════════════════════════════════════════════

class UltrasonicSensor:
    """
    Abstraction for HC-SR04 ultrasonic distance sensor
    Measures distance to detect vehicle presence
    """
    pass


# ═══════════════════════════════════════════════════
# Servo Controller
# ═══════════════════════════════════════════════════

class ServoController:
    """
    Abstraction for servo motor gate control
    Manages gate opening and closing operations
    """
    pass


# ═══════════════════════════════════════════════════
# LCD Display
# ═══════════════════════════════════════════════════

class LCDDisplay:
    """
    Abstraction for I2C LCD display
    Handles text display and status messages
    """
    pass


# ═══════════════════════════════════════════════════
# Feedback Controller
# ═══════════════════════════════════════════════════

class FeedbackController:
    """
    Abstraction for LED and buzzer feedback
    Provides visual and audio feedback for system events
    """
    pass
