"""Small synchronous RFC 6455 client for the bridge's local binary WebSocket."""

from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct


class WebSocketError(RuntimeError):
    pass


class BinaryWebSocket:
    def __init__(self, server, timeout):
        self.host, self.port = _address(server)
        self.timeout = timeout
        self.socket = None

    def __enter__(self):
        self.socket = socket.create_connection((self.host, self.port), self.timeout)
        self.socket.settimeout(self.timeout)
        self._handshake()
        return self

    def __exit__(self, exc_type, exc, traceback):
        if self.socket is not None:
            try:
                self._send_frame(0x8, b"")
            except OSError:
                pass
            self.socket.close()
            self.socket = None

    def send_binary(self, payload):
        self._send_frame(0x2, payload)

    def receive_binary(self):
        fragments = []
        active = False
        while True:
            first, second = self._read_exact(2)
            final = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            mask = self._read_exact(4) if masked else None
            payload = self._read_exact(length)
            if mask:
                payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
            if opcode == 0x8:
                raise WebSocketError("Plasticity closed the WebSocket connection")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x2:
                fragments = [payload]
                active = True
            elif opcode == 0x0 and active:
                fragments.append(payload)
            else:
                raise WebSocketError("Unexpected WebSocket frame opcode %d" % opcode)
            if final:
                return b"".join(fragments)

    def _handshake(self):
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET / HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
        ) % (self.host, self.port, key)
        self.socket.sendall(request.encode("ascii"))
        response = self._read_headers()
        lines = response.decode("latin-1").split("\r\n")
        if not lines or " 101 " not in (" " + lines[0] + " "):
            raise WebSocketError("Plasticity rejected WebSocket upgrade: %s" % lines[0])
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        expected = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        if headers.get("sec-websocket-accept") != expected:
            raise WebSocketError("Plasticity returned an invalid WebSocket accept key")

    def _read_headers(self):
        data = bytearray()
        while not data.endswith(b"\r\n\r\n"):
            data.extend(self._read_exact(1))
            if len(data) > 65536:
                raise WebSocketError("WebSocket response headers are too large")
        return bytes(data)

    def _read_exact(self, count):
        data = bytearray()
        while len(data) < count:
            chunk = self.socket.recv(count - len(data))
            if not chunk:
                raise WebSocketError("WebSocket connection closed unexpectedly")
            data.extend(chunk)
        return bytes(data)

    def _send_frame(self, opcode, payload):
        payload = bytes(payload)
        length = len(payload)
        first = 0x80 | opcode
        if length < 126:
            header = struct.pack("!BB", first, 0x80 | length)
        elif length <= 0xFFFF:
            header = struct.pack("!BBH", first, 0x80 | 126, length)
        else:
            header = struct.pack("!BBQ", first, 0x80 | 127, length)
        mask = os.urandom(4)
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self.socket.sendall(header + mask + masked)


def _address(server):
    value = str(server).strip()
    if value.startswith("ws://"):
        value = value[5:]
    if "/" in value:
        value = value.split("/", 1)[0]
    host, separator, port = value.rpartition(":")
    if not separator or not host or not port.isdigit():
        raise WebSocketError("Server must be host:port, for example localhost:8980")
    return host, int(port)
