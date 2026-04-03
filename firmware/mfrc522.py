# mfrc522_new.py
from machine import Pin
import time

class MFRC522:
    REQIDL   = 0x26
    REQALL   = 0x52
    AUTHENT1A = 0x60
    AUTHENT1B = 0x61
    OK   = 0
    NOTAGERR = 1
    ERR  = 2

    # Registers
    CommandReg     = 0x01
    CommIEnReg     = 0x02
    CommIrqReg     = 0x04
    ErrorReg       = 0x06
    FIFODataReg    = 0x09
    FIFOLevelReg   = 0x0A
    ControlReg     = 0x0C
    BitFramingReg  = 0x0D
    ModeReg        = 0x11
    TxControlReg   = 0x14
    TxAutoReg      = 0x15
    TModeReg       = 0x2A
    TPrescalerReg  = 0x2B
    TReloadRegH    = 0x2C
    TReloadRegL    = 0x2D
    VersionReg     = 0x37

    def __init__(self, spi, cs, rst):
        self.spi = spi
        self.cs  = cs
        self.rst = rst
        self.cs.value(1)
        self.rst.value(1)
        self._init()

    def _spi_write(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytes([(reg << 1) & 0x7E, val]))
        self.cs.value(1)

    def _spi_read(self, reg):
        self.cs.value(0)
        buf = bytearray(2)
        self.spi.write_readinto(bytes([((reg << 1) & 0x7E) | 0x80, 0]), buf)
        self.cs.value(1)
        return buf[1]

    def _set_bitmask(self, reg, mask):
        self._spi_write(reg, self._spi_read(reg) | mask)

    def _clear_bitmask(self, reg, mask):
        self._spi_write(reg, self._spi_read(reg) & (~mask))

    def _init(self):
        self.rst.value(0)
        time.sleep_ms(50)
        self.rst.value(1)
        time.sleep_ms(50)

        self._spi_write(self.TModeReg,      0x8D)
        self._spi_write(self.TPrescalerReg, 0x3E)
        self._spi_write(self.TReloadRegL,   0x1E)
        self._spi_write(self.TReloadRegH,   0x00)
        self._spi_write(self.TxAutoReg,     0x40)
        self._spi_write(self.ModeReg,       0x3D)
        self._set_bitmask(self.TxControlReg, 0x03)

    def version(self):
        return self._spi_read(self.VersionReg)

    def _card_write(self, cmd, data):
        back_data = []
        back_len  = 0
        err       = False
        irq_en    = 0x77
        wait_irq  = 0x30

        self._spi_write(self.CommIEnReg, irq_en | 0x80)
        self._clear_bitmask(self.CommIrqReg, 0x80)
        self._set_bitmask(self.FIFOLevelReg, 0x80)
        self._spi_write(self.CommandReg, 0x00)

        for d in data:
            self._spi_write(self.FIFODataReg, d)

        self._spi_write(self.CommandReg, cmd)
        if cmd == 0x0C:
            self._set_bitmask(self.BitFramingReg, 0x80)

        i = 2000
        while True:
            irq = self._spi_read(self.CommIrqReg)
            i -= 1
            if not (i != 0 and not (irq & 0x01) and not (irq & wait_irq)):
                break

        self._clear_bitmask(self.BitFramingReg, 0x80)

        if i == 0:
            return self.ERR, None, 0

        if (self._spi_read(self.ErrorReg) & 0x1B) == 0x00:
            err = False
            if irq & irq_en & 0x01:
                err = True
            if cmd == 0x0C:
                n = self._spi_read(self.FIFOLevelReg)
                last_bits = self._spi_read(self.ControlReg) & 0x07
                back_len  = (n - 1) * 8 + last_bits if last_bits else n * 8
                n = min(n, 16)
                for _ in range(n):
                    back_data.append(self._spi_read(self.FIFODataReg))
        else:
            err = True

        if err:
            return self.ERR, None, 0
        return self.OK, back_data, back_len

    def request(self, mode):
        self._spi_write(self.BitFramingReg, 0x07)
        stat, back, _ = self._card_write(0x0C, [mode])
        if stat != self.OK or _ != 0x10:
            return self.ERR, None
        return self.OK, back

    def anticoll(self):
        self._spi_write(self.BitFramingReg, 0x00)
        stat, back, _ = self._card_write(0x0C, [0x93, 0x20])
        if stat == self.OK and back and len(back) == 5:
            crc = back[0] ^ back[1] ^ back[2] ^ back[3]
            if crc != back[4]:
                return self.ERR, None
            return self.OK, back[:4]
        return self.ERR, None

    def halt(self):
        self._card_write(0x0C, [0x50, 0x00])