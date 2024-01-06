from zono.socket.client.securesocket import SecureSocket, Crypt
import cryptography.hazmat.primitives.asymmetric.padding
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.serialization
from .module_helpers import ClientModule, event
from zono.socket.client.types import Context
import zono.zonocrypt
import zono.workers
import threading
import secrets
import socket


class SecureEventSocket(SecureSocket):
    def _connect(self, addr):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect(addr)

        except ConnectionRefusedError:
            raise zono.socket.ConnectionFailed(7)
        num1 = secrets.token_bytes(32)
        try:
            self.send_raw(dict(num=num1))
            pkt = self.recv_raw()
        except zono.socket.ReceiveError:
            raise zono.socket.ConnectionFailed(9)
        except zono.socket.SendError:
            raise zono.socket.ConnectionFailed(9)
        num2 = pkt["kdn"]
        _pem = pkt["pem"]
        public_key = cryptography.hazmat.primitives.serialization.load_pem_public_key(
            _pem
        )

        num3 = secrets.token_bytes(32)

        num3_enc = public_key.encrypt(
            num3,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA384()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
                label=None,
            ),
        )
        self.send_raw(dict(num=num3_enc))

        key_deriv = num1 + num2 + num3
        self.session_key = Crypt.hashing_function(key_deriv)

        self.status = self.recv(buffer=512)
        self.buffer = self.status.get("buffer", self.buffer)
        self.format = self.status.get("format", self.format)

        self.send(
            dict(
                _event_socket=True,
                _event_socket_addr=self.parent_addr,
                _event_socket_key=self.parent_key,
                **(self.wrap_event("client_info", Context(self)) or {}),
            )
        )
        self.final_connect_info = self.recv()
        if not (self.final_connect_info.get("success", False) is True):
            raise zono.socket.ConnectionFailed(7)

        for module in self.modules:
            self.load_module(module)


class EventSocket(ClientModule):
    def setup(self, ctx):
        self.client = ctx.app
        self.run_event = self.client.run_event

    def event_listener_(self):
        while True:
            try:
                ev = self.event_socket.recv(timeout=None)
                self.run_event("socket_event", ev)
            except zono.socket.ReceiveError as e:
                e.alive = True
                try:
                    self.client.keep_alive()
                    self.event_socket.keep_alive()
                except zono.socket.SendError:
                    e.alive = False
                return self.run_event("event_listener_error", e)
            except BaseException as e:
                self.run_event("event_listener_error", e)

    def start_event_listener(self, addr):
        self.event_socket = SecureEventSocket()
        self.event_socket.parent_addr = tuple(self.client.socket.getsockname())
        self.event_socket.parent_key = self.client.session_key
        self.client.event_manager.copy(self.event_socket)
        self.event_socket._connect(addr)
        res = self.event_socket.final_connect_info.get(
            "_event_socket", dict(success=False)
        )

        if res["success"]:
            self.event_thread = threading.Thread(
                target=self.event_listener_, daemon=True
            )
            self.event_thread.start()

        else:
            raise Exception("Failed to start event listener")

        self.run_event("on_event_socket_connect")

    @event()
    def on_connect(self, ctx):
        if ctx.status.get("event_socket", False) is True:
            self.start_event_listener(ctx.addr)

    @event()
    def on_close(self, ctx):
        self.event_socket.close()
        self.event_thread.join()
