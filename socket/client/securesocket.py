import cryptography.hazmat.primitives.asymmetric.padding
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.serialization
from .types import Context
import zono.zonocrypt
import zono.workers
import zono.events
import zono.socket
import traceback
import secrets
import socket
import sys

Crypt = zono.zonocrypt.zonocrypt()


def wrap_error(e):
    if zono.socket.show_full_error:
        return e


class SecureSocket:
    def __init__(self):
        self.buffer = 64
        self.format = "utf-8"
        self.timeout = None
        self.server_info = None
        self.connection_info = None
        self.kill_on_error = True
        self.modules = []
        zono.events.attach(self, always_event_group=True)
        self.set_event('on_event_error',self.on_event_error)

    def load_module(self, module):
        if not isinstance(module, dict):
            return
        if "setup" in module:
            module["setup"](Context(self, module=module))
        if "events" in module:
            for ev, handler in module["events"].items():
                self.register_event(ev, handler)
        if "modules" in module:
            for i in module["modules"]:
                self.load_modules(i)

        self.modules.append(module)

    def wrap_event(self, event, *args, **kwargs):
        ret = self.run_event(event, *args, **kwargs)
        if isinstance(ret, dict) or ret is None:
            return ret
        n = dict()
        for i in ret:
            if i is None:
                print(f"ERROR event: {event} a sub event in group returned None")
                continue
            n |= i
        return n

    def connect(self, addr):
        try:
            self._connect(addr)
        except zono.socket.ReceiveError as e:
            if e.errorno == 3:
                raise zono.socket.ConnectionFailed(8) from wrap_error(e)
            raise zono.socket.ConnectionFailed(11) from e
        except zono.socket.SendError as e:
            raise zono.socket.ConnectionFailed(11) from e

    def _connect(self, addr):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect(addr)
        except ConnectionRefusedError as e:
            raise zono.socket.ConnectionFailed(7) from wrap_error(e)
        num1 = secrets.token_bytes(32)
        try:
            self.send_raw(dict(num=num1))
            pkt = self.recv_raw(1)
        except zono.socket.ReceiveError as e:
            raise zono.socket.ConnectionFailed(9) from wrap_error(e)
        except zono.socket.SendError as e:
            raise zono.socket.ConnectionFailed(9) from wrap_error(e)
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
                    algorithm=cryptography.hazmat.primitives.hashes.SHA512()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA512(),
                label=None,
            ),
        )
        self.send_raw(dict(num=num3_enc))

        key_deriv = num1 + num2 + num3
        self.session_key = Crypt.hashing_function(key_deriv)

        status = self.recv(timeout=1)
        self.connection_info = status
        self.server_info = status.copy()
        self.clean_server_info()
        self.format = status.get("format", self.format)
        self.buffer = status.get("buffer", self.buffer)

        self.send(self.wrap_event("client_info", Context(self)) or {})

        self.final_connect_info = self.recv(timeout=1)
        if not (self.final_connect_info.get("success", False) is True):
            raise zono.socket.ConnectionFailed(7)

        self.interval = zono.workers.set_interval(
            status["timeout"] * 0.85, self.keep_alive, daemon=True
        )
        self.run_event(
            "on_connect",
            Context(
                self,
                status=status,
                final_connect_info=self.final_connect_info,
                addr=addr,
            ),
        )

    def keep_alive(self):
        return self.send(dict(_keepalive=True, path=None))

    def clean_server_info(self):
        for i in ("info", "status", "success"):
            self.server_info.pop(i, None)

    def send(self, pkt, buffer=None):
        buffer = buffer or self.buffer
        return zono.socket.send(self.socket, pkt, self.session_key, self.format, buffer)

    def recv(self, buffer=None, timeout=-1):
        buffer = buffer or self.buffer
        if timeout == -1:
            timeout = self.timeout
        return zono.socket.recv(
            self.socket, buffer, timeout, self.session_key, self.format
        )

    def request(self, path, pkt=dict(), _recv=True, buffer=None, timeout=-1):
        pkt["path"] = path
        self.send(pkt)
        if _recv:
            return self.recv(buffer=buffer, timeout=timeout)

    def send_raw(self, pkt):
        return zono.socket.send_raw(self.socket, pkt, self.format, self.buffer)

    def recv_raw(self, timeout=-1):
        if timeout == -1:
            timeout = self.timeout
        return zono.socket.recv_raw(self.socket, self.buffer, self.format, timeout)

    def close(self):
        self.socket.close()
        if hasattr(self, "interval"):
            zono.workers.cancel_interval(self.interval)
        self.run_event("on_close", Context(self))

    
    def on_event_error(self, error, event, exc_info):

        traceback.print_exception(
            exc_info[0], exc_info[1], exc_info[2], file=sys.stderr
        )
        print(error, file=sys.stderr)
        print(f"\nthis error occurred in {event}", file=sys.stderr)
        if self.kill_on_error:
            self.close()
            sys.exit(1)