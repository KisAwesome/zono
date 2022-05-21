import socket
import threading
import zono.colorlogger
import zono.zonocrypt
import secrets
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives
import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.primitives.asymmetric.padding
from .types import Store, Event, Context, Request, Middleware, EventGroupReturn
from .exceptions import *
import sys
import traceback
import socket
import signal
import os


signal.signal(signal.SIGBREAK, lambda x, y: os._exit(0))

Crypt = zono.zonocrypt.zonocrypt()

objcrypt = zono.zonocrypt.objcrypt(hash_algorithm=zono.zonocrypt.objcrypt.SHA512)


KEY_UPPERBOUND = 100000000


def form_addr(addr):
    return f"{addr[0]}:{addr[1]}"


class Server:
    def __init__(self, ip="", port=None):
        self.events = {}
        self.store = Store()
        self.base_events = {}
        self.kill_on_exit = False
        self.kill_on_error = True
        self.port = port
        self.hostname = socket.gethostname()
        self.ip = ip or self.get_server_ip()
        self.sessions = {}
        self.buffer = 512
        self.format = "utf-8"
        self.middlewares = []
        self.event_socket = False

        self.load_events()
        self.paths = {}
        self.next_mw = False

    def next(self):
        self.next_mw = True

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.listen()

    def accept_connections(self):
        self.run_event("on_start", self.ip, self.port)
        self.socket.listen()
        while True:
            conn, addr = self.socket.accept()
            if not self.run_event("connect_check", conn, addr):
                continue

            threading.Thread(
                target=self.handle_client,
                args=(
                    conn,
                    addr,
                ),
            ).start()

    def recv_loop(self, conn, addr):
        while True:
            try:
                pkt = self.recv(conn, addr)
                path = pkt.get("path", None)
                ctx = Context(
                    self,
                    pkt=pkt,
                    conn=conn,
                    addr=addr,
                    request=path,
                    session=self.get_session(addr),
                    next=self.next,
                )
                self.next_mw = True
                for i in self.middlewares:
                    if not self.next_mw:
                        break
                    self.next_mw = False
                    try:
                        i(ctx)
                    except MiddlewareError as e:
                        self.run_event("on_middleware_error", e.ctx, e.error)

                if not self.next_mw:
                    continue
                if path in self.paths:
                    try:
                        handler = self.paths[path]
                        handler(ctx)

                    except RequestError as e:
                        if handler.error_handler:
                            return handler.error_handler(e.ctx, e.error)
                        if self.isevent("on_request_error"):
                            return self.run_event("on_request_error", e.ctx, e.error)

                        raise e

                else:
                    msg = "Client requested a path which does not exist"
                    ctx.error = ClientError(msg)
                    ctx.msg = msg

                    self.run_event("on_client_error", ctx)
                    self.send(
                        dict(status=404, info="Path not found", error=True),
                        conn,
                        addr,
                    )

            except socket.error as e:
                self.sessions.pop(addr, None)
                self.run_event("on_disconnect", conn, addr)
                break

    def handle_client(self, conn, addr):
        echo_pkt = self.recv_raw(conn)
        num1 = echo_pkt["num"]

        private_key = (
            cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key(
                public_exponent=65537, key_size=2048
            )
        )
        public_key = private_key.public_key()

        pem = public_key.public_bytes(
            encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
            format=cryptography.hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        num2 = secrets.randbelow(KEY_UPPERBOUND)
        self.send_raw(dict(pem=pem, kdn=num2), conn)

        num_3_enc = self.recv_raw(conn)["num"]

        _num3 = private_key.decrypt(
            num_3_enc,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA384()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
                label=None,
            ),
        )
        num3 = int(_num3.decode("utf-8"))

        key_deriv = str(num1 * num2 * num3)

        key = Crypt.hashing_function(key_deriv)

        self.sessions[addr] = Store(conn=conn, key=key)
        s = self.run_event("create_session", conn, addr)

        if isinstance(s, EventGroupReturn) or isinstance(s, list):
            for i in s:
                self.sessions[addr] |= i

        else:
            self.sessions[addr] |= s

        self.send(
            dict(
                status=200,
                info="Initiated secure connection",
                buffer=self.buffer,
                event_socket=self.event_socket,
            ),
            conn,
            addr,
        )
        self.run_event("on_connect", conn, addr)
        self.recv_loop(conn, addr)

    def get_request(self, path):
        return self.paths.get(path, None)

    def isevent(self, event):
        return event in self.events

    def register_event(self, event, func):
        ev = Event(func, event)
        self.events[event] = ev
        return ev

    def register_path(self, path, func):
        req = Request(path, func)
        self.paths[path] = req
        return req

    def register_middleware(self, func):
        mw = Middleware(func)
        self.middlewares.append(mw)
        return mw

    def register_base_event(self, event, func):
        self.base_events[event] = func
        self.register_event(event, func)

    def event(self, event_name=None):
        def wrapper(func):
            name = event_name
            if event_name is None:
                name = func.__name__

            if not callable(func):
                raise ValueError("Event must be callable")

            return self.register_event(name, func)

        return wrapper

    def request(self, path):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Request function must be callable")
            return self.register_path(path, func)

        return wrapper

    def middleware(self):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Request function must be callable")
            return self.register_middleware(func)

        return wrapper

    def _run_event(self, event, *args, **kwargs):
        ev = self.events.get(event, False)
        if ev:
            ret = ev(*args, **kwargs)
            return ret
        return

    def run_event(self, event, *args, **kwargs):
        try:
            return self._run_event(event, *args, **kwargs)

        except EventError as e:
            self._run_event("on_event_error", e.error, event, sys.exc_info())
        # try:
        #     ret = self._run_event(event, *args, **kwargs)
        # except EventError as e:
        #     if isinstance(e.error, SystemExit):
        #         sys.exit()
        #     self._run_event("on_event_error", e.error, event, sys.exc_info())

        # except BaseException as e:
        #     if isinstance(e, SystemExit):
        #         sys.exit()
        #     self._run_event("on_event_error", e, event, sys.exc_info())

        # return ret

    def get_server_ip(self):
        return socket.gethostbyname(self.hostname)

    def on_event_error(self, error, event, exc_info):
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(f"\nthis error occurred in {event}")
        if self.kill_on_error:
            os._exit(0)

    def on_request_error(self, ctx, error):
        traceback.print_exception(ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(f"\nthis error occurred in {ctx.request}")
        if self.kill_on_error:
            os._exit(0)

    def on_middleware_error(self, ctx, error):
        traceback.print_exception(ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(f"\nthis error occurred in middleware function")
        if self.kill_on_error:
            os._exit(0)

    def load_events(self):
        self.register_base_event("on_ready", lambda: None)
        self.register_base_event("on_request_error", self.on_request_error)
        self.register_base_event("on_event_error", self.on_event_error)
        self.register_base_event("connect_check", lambda x, y: True)
        self.register_base_event("create_session", lambda c, a: dict())
        self.register_base_event("on_middleware_error", self.on_middleware_error)

    def load_base_requests(self):
        pass

    def load_loggers(self):
        self.register_event(
            "on_connect", lambda c, a: zono.colorlogger.log(f"{a} connected")
        )
        self.register_event(
            "on_disconnect", lambda c, a: zono.colorlogger.log(f"{a} disconnected")
        )
        self.register_event(
            "on_start",
            lambda ip, port: zono.colorlogger.major_log(
                f"Server listening @{ip}:{port}"
            ),
        )
        self.register_event(
            "on_client_error",
            lambda ctx: zono.colorlogger.error(
                f"Client error {form_addr(ctx.addr)}: {ctx.msg}"
            ),
        )

    def get_session_key(self, addr):
        s = self.sessions.get(addr, None)
        if s:
            return s.key

    def get_session(self, addr):
        return self.sessions.get(addr, None)

    def send(self, pkt, conn, addr):
        message = objcrypt.encrypt(pkt, self.get_session_key(addr))

        msg_length = len(message)

        send_length = str(msg_length).encode(self.format)

        send_length += b" " * (self.buffer - len(send_length))

        conn.send(send_length)
        conn.send(message)

    def recv(self, conn, addr):
        try:
            msg_len = int(conn.recv(self.buffer).decode(self.format))
        except ValueError:
            raise socket.error
        msg = conn.recv(msg_len)
        obj = objcrypt.decrypt(msg, self.get_session_key(addr))
        return obj

    def send_raw(self, pkt, conn):
        message = objcrypt.encode(pkt)
        msg_length = len(message)

        send_length = str(msg_length).encode(self.format)
        send_length += b" " * (self.buffer - len(send_length))

        conn.send(send_length)
        conn.send(message)

    def recv_raw(self, conn):
        msg_len = int(conn.recv(self.buffer).decode(self.format))
        msg = conn.recv(msg_len)
        msg = objcrypt.decode(msg)
        return msg

    def run(self):
        self.init_socket()
        self.accept_connections()
