import zlib
import socket
from .packet import *
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


# Socket connection to the minecraft server
class TCPConnection(Packet):
    def __init__(self, addr, debug = False, timeout=10):
        Packet.__init__(self)
        self.encrypt = False
        self.debug = debug
        self.compression_threshold = None
        self.socket = socket.create_connection(addr, timeout=timeout)

    def read(self, length):
        result = bytearray()
        while len(result) < length:
            new = self.socket.recv(length - len(result))
            if len(new) == 0:
                raise IOError("Server didn't respond with information!")
            result.extend(new)
        if self.encrypt:
            result = bytearray(self.decryptor.update(bytes(result)))
        return result

    def write(self, data):
        self.socket.sendall(data)

    def receive_packet(self):
        packet_length = self.read_varint()
        packet_in = Packet()
        raw_data = self.read(packet_length)

        # Decompress if needed
        if self.compression_threshold is not None:
            raw_packet = Packet()
            raw_packet.receive(raw_data)
            data_length = raw_packet.read_varint()
            raw_data = raw_packet.read(len(raw_data))
            if data_length > 0:
                raw_data = zlib.decompress(raw_data)
        packet_in.receive(raw_data)
        return packet_in

    def send_packet(self, packet_out):
        # Compress if needed
        if self.compression_threshold is not None:
            data_length = len(packet_out.sent)
            raw_packet = packet_out.flush()
            if data_length < self.compression_threshold:
                packet_out.write_varint(0)
                packet_out.write(raw_packet)
            else:
                raw_packet = zlib.compress(raw_packet)
                packet_out.write_varint(len(raw_packet))
                packet_out.write(raw_packet)

        packet_data = packet_out.flush()
        packet_out.write_varint(len(packet_data))
        packet_out.write(packet_data)

        if self.encrypt:
            packet_data = packet_out.flush()
            packet_out.write(bytearray(self.encryptor.update(bytes(packet_data))))

        if self.debug:
            print('Sending packet: ' + str(packet_out.sent))
        self.write(packet_out.flush())

    # Configures the encryption from given key
    def configure_encryption(self, secret_key):
        self.cipher = Cipher(algorithms.AES(secret_key), modes.CFB8(secret_key), backend=default_backend())
        self.encryptor = self.cipher.encryptor()
        self.decryptor = self.cipher.decryptor()
        self.encrypt = True
        print('Encryption enabled')

    def close(self):
        self.socket.close()

    def __del__(self):
        self.socket.close()
