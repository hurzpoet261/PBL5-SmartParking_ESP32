from machine import Pin, SPI

class MFRC522:
    OK = 0
    NOTAGERR = 1
    ERR = 2
    REQIDL = 0x26
    ANTICOLL = 0x93

    def __init__(self, spi, gpioRst, gpioCs):
        self.spi = spi
        self.rst = Pin(gpioRst, Pin.OUT)
        self.cs = Pin(gpioCs, Pin.OUT)
        self.cs.value(1)
        self.rst.value(1)
        self.init()

    def _wreg(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytearray([reg << 1, val]))
        self.cs.value(1)

    def _rreg(self, reg):
        self.cs.value(0)
        self.spi.write(bytearray([(reg << 1) | 0x80]))
        val = self.spi.read(1)[0]
        self.cs.value(1)
        return val

    def init(self):
        self._wreg(0x01, 0x0F) # SoftReset
        self._wreg(0x2A, 0x8D) # TMode
        self._wreg(0x2B, 0x3E) # TPrescaler
        self._wreg(0x2D, 30)   # TReloadValueL
        self._wreg(0x2C, 0)    # TReloadValueH
        self._wreg(0x15, 0x40) # TxASK
        self._wreg(0x11, 0x3D) # ModeReg
        self.antenna_on()

    def antenna_on(self):
        if not (self._rreg(0x14) & 0x03):
            self._wreg(0x14, self._rreg(0x14) | 0x03)

    def request(self, mode):
        self._wreg(0x0D, 0x07) # BitFramingReg
        stat = self._cmd(0x0C, bytearray([mode]))
        backbits = (self._rreg(0x04) & 0x07) if stat == self.OK else 0
        return stat, backbits

    def _cmd(self, cmd, buf):
        self._wreg(0x0A, 0x00)  # ClearBitErrors
        self._wreg(0x08, len(buf))  # FIFOLevelReg
        
        for i in range(len(buf)):
            self._wreg(0x09, buf[i])
        
        self._wreg(0x01, cmd | 0x10)  # Start transmission
        
        i = 2000
        while i > 0:
            n = self._rreg(0x04)
            i -= 1
            if not (n & 0x04) and n > 0:
                break
        
        if i != 0:
            return self.OK if not (self._rreg(0x06) & 0xB4) else self.ERR
        else:
            return self.ERR

    def anticoll(self):
        buf = bytearray([self.ANTICOLL, 0x20])
        stat = self._cmd(0x0E, buf)
        
        if stat == self.OK:
            uid = []
            for i in range(5):
                uid.append(self._rreg(0x09))
            return self.OK, uid[:4]
        return self.NOTAGERR, None