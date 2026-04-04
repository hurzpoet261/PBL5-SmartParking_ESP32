import usocket as socket
import ustruct as struct
from ubinascii import hexlify

class MQTTException(Exception):
    pass

class MQTTClient:
    def __init__(self, client_id, server, port=1883, user="S House", password="Phuocbaotinh", keepalive=0):
        self.client_id = client_id
        self.server = server
        self.port = port
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.sock = None

    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def connect(self, clean_session=True):
        self.sock = socket.socket()
        addr = socket.getaddrinfo(self.server, self.port)[0][-1]
        self.sock.connect(addr)
        
        premsg = bytearray(b"\x10\0\0\x04MQTT\x04\x02\0\0")
        msg = bytearray([0x10, 0, 0, 0, 0, 0])
        msg[1] = 10 + len(self.client_id)
        msg[3] = 4
        msg[4] = 2 # Clean session
        
        self.sock.write(msg[:2])
        self._send_str(b"MQTT")
        self.sock.write(msg[4:6])
        self._send_str(self.client_id)
        
        res = self.sock.read(4)
        return res[3] == 0

    def publish(self, topic, msg, retain=False, qos=0):
        pkt = bytearray([0x30, 0, 0, 0])
        pkt[0] |= qos << 1 | retain
        pkt[1] = 2 + len(topic) + len(msg)
        self.sock.write(pkt[:2])
        self._send_str(topic)
        self.sock.write(msg)

    def disconnect(self):
        self.sock.write(b"\xe0\0")
        self.sock.close()        