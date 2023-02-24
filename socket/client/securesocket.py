import cryptography.hazmat.primitives.asymmetric.padding
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.serialization
import zono.zonocrypt
import zono.events
import threading
import secrets
import socket
import copy


Crypt = zono.zonocrypt.zonocrypt()
objcrypt = zono.zonocrypt.objcrypt(hash_algorithm=zono.zonocrypt.objcrypt.SHA512)


def terminate(thread):
    if thread._tstate_lock.locked():
        thread._tstate_lock.release()
    thread._stop()

    if thread._ident in threading.enumerate():
        thread._delete()


KEY_UPPERBOUND = 100000000


class ConnectionClosed(Exception):
    pass


class SecureSocket:
    def __init__(self):
        self.buffer = 512
        self.format = "utf-8"
        zono.events.attach(self, always_event_group=False)
        self.register_event("client_info", lambda: {})
        self.register_event("on_connect", lambda: None)
        self.server_info = None

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

        self.send(self.run_event("client_info"))
        status = self.recv()
        self.buffer = status.get("buffer", self.buffer)
        if status.get("event_socket", False):
            _ev = copy.copy(self.event_maneger)
            self.event_socket = EventSocket()
            _ev.attached_to = None
            _ev.attach(self.event_socket)
            self.event_socket.connect(addr)
            self.event_socket.send(
                dict(
                    path="_event_socket",
                    addr=tuple(self.socket.getsockname()),
                    key=self.session_key,
                )
            )
            res = self.event_socket.recv()
            if res["success"]:
                self.event_thread = threading.Thread(target=self.event_listiner_)
                self.event_thread.start()
            else:
                raise Exception("Failed to start event listener")

        self.server_info = status
        self.run_event("on_connect")

    def event_listiner_(self):
        while True:
            try:
                ev = self.event_socket.recv()
                if ev is ConnectionClosed:
                    return
                self.run_event("socket_event", ev)
            except socket.error:
                e = ConnectionClosed("Event socket has been closed by the host")
                return self.run_event("event_listiner_error", e)
            except BaseException as e:
                self.run_event("event_listiner_error", e)

    def send(self, pkt):
        message = objcrypt.encrypt(pkt, self.session_key)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.format)
        send_length += b" " * (self.buffer - len(send_length))
        self.socket.send(send_length)
        self.socket.send(message)

    def recv(self):
        try:
            msg_len = int(self.socket.recv(self.buffer).decode(self.format))
        except ValueError:
            raise socket.error
        except OSError:
            return ConnectionClosed
        msg = self.socket.recv(msg_len)
        obj = objcrypt.decrypt(msg, self.session_key)
        return obj

    def request(self, path, pkt):
        pkt["path"] = path
        self.send(pkt)
        return self.recv()

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

    def close(self):
        self.socket.close()
        if hasattr(self, "event_socket"):
            self.event_socket.close()
            self.event_thread.join()


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
        self.send(self.event_maneger.run_event("client_info"))
        status = self.recv()
        self.buffer = status.get("buffer", self.buffer)
