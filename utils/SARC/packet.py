import uuid
import struct


class Packet:
    def __init__(self):
        self.sent = bytearray()
        self.received = bytearray()

    def read(self, length):
        result = self.received[:length]
        self.received = self.received[length:]
        return result

    def write(self, data):
        if isinstance(data, Packet):
            data = bytearray(data.flush())
        if isinstance(data, str):
            data = bytearray(data)
        if isinstance(data, bytes):
            data = bytearray(data)
        self.sent.extend(data)

    def receive(self, data):
        if not isinstance(data, bytearray):
            data = bytearray(data)
        self.received.extend(data)

    def remaining(self):
        return len(self.received)

    def flush(self):
        result = self.sent
        self.sent = bytearray()
        return result

    def _unpack(self, format, data):
        return struct.unpack('>' + format, bytes(data))[0]

    def _pack(self, format, data):
        return struct.pack('>' + format, data)

    def read_varint(self):
        result = 0
        for i in range(5):
            part = ord(self.read(1))
            result |= (part & 0x7F) << 7 * i
            if not part & 0x80:
                return result
        raise IOError('Server sent a varint that was too big!')

    def write_varint(self, value):
        remaining = value
        for i in range(5):
            if remaining & ~0x7F == 0:
                self.write(struct.pack('!B', remaining))
                return
            self.write(struct.pack('!B', remaining & 0x7F | 0x80))
            remaining >>= 7
        raise ValueError('The value' + str(value) + 'is too big to send in a varint')

    def read_utf(self):
        length = self.read_varint()
        return self.read(length).decode('utf8')

    def write_utf(self, value):
        self.write_varint(len(value))
        self.write(bytearray(value, 'utf8'))

    def read_ascii(self):
        result = bytearray()
        while len(result) == 0 or result[-1] != 0:
            result.extend(self.read(1))
        return result[:-1].decode('ISO-8859-1')

    def write_ascii(self, value):
        self.write(bytearray(value, 'ISO-8859-1'))
        self.write(bytearray.fromhex('00'))

    def read_short(self):
        return self._unpack('h', self.read(2))

    def write_short(self, value):
        self.write(self._pack('h', value))

    def read_ushort(self):
        return self._unpack('H', self.read(2))

    def write_ushort(self, value):
        self.write(self._pack('H', value))

    def read_int(self):
        return self._unpack('i', self.read(4))

    def write_int(self, value):
        self.write(self._pack('i', value))

    def read_uint(self):
        return self._unpack('I', self.read(4))

    def write_uint(self, value):
        self.write(self._pack('I', value))

    def read_long(self):
        return self._unpack('q', self.read(8))

    def write_long(self, value):
        self.write(self._pack('q', value))

    def read_ulong(self):
        return self._unpack('Q', self.read(8))

    def write_ulong(self, value):
        self.write(self._pack('Q', value))

    def read_bytearray_as_str(self):
        length = self.read_varint()
        return self._unpack(str(length) + 's', self.read(length))

    def read_float(self):
        return self._unpack('f', self.read(4))

    def write_float(self, value):
        self.write(self._pack('f', value))

    def read_double(self):
        return self._unpack('d', self.read(8))

    def write_double(self, value):
        self.write(self._pack('d', value))

    def read_bool(self):
        return self._unpack('?', self.read(1))

    def write_bool(self, value):
        self.write(self._pack('?', value))

    def read_byte(self):
        return self._unpack('b', self.read(1))

    def write_byte(self, value):
        self.write(self._pack('b', value))

    def read_ubyte(self):
        return self._unpack('B', self.read(1))

    def write_ubyte(self, value):
        self.write(self._pack('B', value))

    def read_uuid(self):
        return str(uuid.UUID(bytes=bytes(self.read(16))))

    def write_uuid(self, value):
        self.write(uuid.UUID(value).bytes)
