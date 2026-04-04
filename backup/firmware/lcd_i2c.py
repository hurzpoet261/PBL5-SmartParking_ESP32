"""
Driver LCD I2C 16x2 / 20x4 cho ESP32
SDA = GPIO21, SCL = GPIO22
Địa chỉ I2C mặc định: 0x27 (có thể là 0x3F tùy module)
"""

from machine import I2C, Pin
import time

class LCD_I2C:
    def __init__(self, i2c_addr=0x27, cols=16, rows=2):
        """
        Khởi tạo LCD I2C
        i2c_addr: địa chỉ I2C của LCD (0x27 hoặc 0x3F)
        cols: số cột (16 hoặc 20)
        rows: số hàng (2 hoặc 4)
        """
        self.i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
        self.addr = i2c_addr
        self.cols = cols
        self.rows = rows
        self.buffer = [0x00] * (cols * rows)
        
        # Các lệnh LCD
        self.LCD_CLEARDISPLAY = 0x01
        self.LCD_RETURNHOME = 0x02
        self.LCD_ENTRYMODESET = 0x04
        self.LCD_DISPLAYCONTROL = 0x08
        self.LCD_CURSORSHIFT = 0x10
        self.LCD_FUNCTIONSET = 0x20
        self.LCD_SETCGRAMADDR = 0x40
        self.LCD_SETDDRAMADDR = 0x80
        
        # Các bit điều khiển I2C-LCD
        self.LCD_BACKLIGHT = 0x08
        self.LCD_ENABLE = 0x04
        self.LCD_READ_WRITE = 0x02
        self.LCD_REGISTER_SELECT = 0x01
        
        self._init_lcd()
    
    def _write_byte(self, byte, mode=0):
        """Ghi 1 byte lên LCD qua I2C"""
        high_nibble = byte & 0xF0
        low_nibble = (byte << 4) & 0xF0
        
        self._write_nibble(high_nibble | mode)
        self._write_nibble(low_nibble | mode)
    
    def _write_nibble(self, nibble):
        """Ghi 4 bit (nibble) lên LCD"""
        # Ghi dữ liệu + bật backlight + bit enable LOW
        self.i2c.writeto(self.addr, bytes([nibble | self.LCD_BACKLIGHT]))
        time.sleep_us(1)
        
        # Bật pulse Enable
        self.i2c.writeto(self.addr, bytes([nibble | self.LCD_BACKLIGHT | self.LCD_ENABLE]))
        time.sleep_us(1)
        
        # Disable Enable
        self.i2c.writeto(self.addr, bytes([nibble | self.LCD_BACKLIGHT]))
        time.sleep_us(50)
    
    def _init_lcd(self):
        """Khởi tạo LCD theo chế độ 4-bit"""
        time.sleep_ms(50)
        
        # Chuỗi khởi tạo: ghi 0x30 3 lần (8-bit mode setting trước)
        for _ in range(3):
            self._write_nibble(0x30)
            time.sleep_ms(5)
        
        # Chuyển sang 4-bit mode
        self._write_nibble(0x20)
        time.sleep_ms(5)
        
        # Ghi các lệnh khởi tạo
        self._write_byte(0x28)  # 4-bit mode, 2 dòng, 5x8 font
        time.sleep_ms(2)
        
        self._write_byte(0x08)  # Tắt display
        time.sleep_ms(2)
        
        self._write_byte(0x01)  # Xóa display
        time.sleep_ms(2)
        
        self._write_byte(0x06)  # Chế độ entry: cursor tăng, không scroll
        time.sleep_ms(2)
        
        self._write_byte(0x0C)  # Bật display, tắt cursor
        time.sleep_ms(2)
    
    def clear(self):
        """Xóa toàn bộ display"""
        self._write_byte(self.LCD_CLEARDISPLAY)
        time.sleep_ms(2)
        self.buffer = [0x00] * (self.cols * self.rows)
    
    def home(self):
        """Về vị trí đầu tiên"""
        self._write_byte(self.LCD_RETURNHOME)
        time.sleep_ms(2)
    
    def set_cursor(self, col, row):
        """Đặt vị trí cursor (col: 0-15, row: 0-1)"""
        if row == 0:
            self._write_byte(0x80 + col)
        elif row == 1:
            self._write_byte(0xC0 + col)
        time.sleep_ms(1)
    
    def write(self, text):
        """Ghi text tại vị trí cursor hiện tại"""
        for char in text:
            self._write_byte(ord(char), self.LCD_REGISTER_SELECT)
            time.sleep_us(50)
    
    def print(self, text, col=0, row=0):
        """In text tại vị trí xác định (đơn giản: in đơn hàng)"""
        self.set_cursor(col, row)
        self.write(text)
    
    def show_uid(self, card_id, distance=-1):
        """Hiển thị UID thẻ và khoảng cách"""
        self.clear()
        
        # Dòng 1: Tên
        self.print("The VE:", 0, 0)
        
        # Dòng 2: UID dài, cắt ngắn chỉ lấy 6-7 ký tự cuối
        uid_short = card_id[-6:] if len(card_id) > 6 else card_id
        self.set_cursor(0, 1)
        self.write(uid_short.ljust(16))
        
        time.sleep_ms(100)
    
    def show_message(self, line1, line2=""):
        """Hiển thị 2 dòng text"""
        self.clear()
        self.print(line1[:self.cols], 0, 0)
        if line2:
            self.print(line2[:self.cols], 0, 1)
