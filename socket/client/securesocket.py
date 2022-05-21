import secrets
import socket
import threading
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.primitives.asymmetric.padding
import zono.zonocrypt


Crypt = zono.zonocrypt.zonocrypt()

objcrypt = zono.zonocrypt.objcrypt(hash_algorithm=zono.zonocrypt.objcrypt.SHA512)


KEY_UPPERBOUND = 100000000


class SecureSocket:
    def __init__(self):
        self.buffer = 512
        self.format = "utf-8"
        self.event_handler = None

    def connect(self, addr):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(addr)
        num1 = secrets.randbelow(KEY_UPPERBOUND)
        self.send_raw(dict(num=num1))
        pkt = self.recv_raw()
        num2 = pkt["kdn"]
        _pem = pkt["pem"]
        public_key = cryptography.hazmat.primitives.serialization.load_pem_public_key(
            _pem
        )

        num3 = secrets.randbelow(KEY_UPPERBOUND)

        num3_enc = public_key.encrypt(
            str(num3).encode("utf-8"),
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA384()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
                label=None,
            ),
        )
        self.send_raw(dict(num=num3_enc))

        key_deriv = str(num1 * num2 * num3)
        self.session_key = Crypt.hashing_function(key_deriv)
        status = self.recv()
        self.buffer = status.get("buffer", self.buffer)
        if status.get("event_socket", False):
            if not callable(self.event_handler):
                raise Exception("No event handler set")
            self.event_socket = EventSocket()
            self.event_socket.connect(addr)
            res = self.event_socket.send(
                dict(
                    path="event_socket",
                    addr=self.socket.getsockname(),
                    key=self.session_key,
                )
            )
            if res["success"]:
                threading.Thread(target=self.event_listiner).start()

    def event_listiner_(self):
        while True:
            try:
                ev = self.event_socket.recv()
                self.event_handler(ev)

            except BaseException as e:
                print(e)

    def send(self, pkt):
        message = objcrypt.encrypt(pkt, self.session_key)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.format)
        send_length += b" " * (self.buffer - len(send_length))
        self.socket.send(send_length)
        self.socket.send(message)

    def recv(self):
        msg_len = int(self.lient.recv(self.buffer).decode(self.format))
        msg = self.socket.recv(msg_len)
        obj = objcrypt.decrypt(msg, self.session_key)
        return obj

    def send_raw(self, pkt):
        message = objcrypt.encode(pkt)
        msg_length = len(message)

        send_length = str(msg_length).encode(self.format)
        send_length += b" " * (self.buffer - len(send_length))

        self.socket.send(send_length)
        self.socket.send(message)

    def recv_raw(self):
        msg_len = int(self.socket.recv(self.buffer).decode(self.format))
        msg = self.socket.recv(msg_len)
        msg = objcrypt.decode(msg)
        return msg

    def recv(self):
        msg_len = int(self.socket.recv(self.buffer).decode(self.format))
        msg = self.socket.recv(msg_len)
        obj = objcrypt.decrypt(msg, self.session_key)
        return obj


class EventSocket(SecureSocket):
    def connect(self, addr):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(addr)
        num1 = secrets.randbelow(KEY_UPPERBOUND)
        self.send_raw(dict(num=num1))
        pkt = self.recv_raw()
        num2 = pkt["kdn"]
        _pem = pkt["pem"]
        public_key = cryptography.hazmat.primitives.serialization.load_pem_public_key(
            _pem
        )

        num3 = secrets.randbelow(KEY_UPPERBOUND)

        num3_enc = public_key.encrypt(
            str(num3).encode("utf-8"),
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA384()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
                label=None,
            ),
        )
        self.send_raw(dict(num=num3_enc))

        key_deriv = str(num1 * num2 * num3)
        self.session_key = Crypt.hashing_function(key_deriv)
        status = self.recv()
        self.buffer = status.get("buffer", self.buffer)
