from .types import (
    Store,
    Event,
    Context,
    Request,
    Middleware,
    EventGroupReturn,
    EventGroup,
)
from .exceptions import *
import cryptography.hazmat.primitives.asymmetric.padding
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.serialization
import zono.colorlogger
import zono.zonocrypt
import zono.events
import traceback
import threading
import secrets
import socket
import sys
import os


Crypt = zono.zonocrypt.zonocrypt()

objcrypt = zono.zonocrypt.objcrypt(hash_algorithm=zono.zonocrypt.objcrypt.SHA512)


KEY_UPPERBOUND = 100000000


class SecureServer:
    def __init__(self, ip="", port=None, event_socket=False):
        self.port = port
        self.hostname = socket.gethostname()
        self.ip = ip or self.get_server_ip()
        self.event_socket = event_socket
        zono.events.attach(self, False)
        self.init()

    def init(self):
        self.store = Store()
        self.events = Store()
        self.base_events = {}
        self.kill_on_exit = False
        self.kill_on_error = True
        self.custom_session_handler = False
        self.paths = {}
        self.next_mw = False
        self.sessions = {}
        self.buffer = 512
        self.init_buffer = 512
        self.format = "utf-8"
        self.middlewares = []
        self._shutting_down = False
        self.load_events()
        self.load_paths()

    def server_info(self):
        return dict(
            buffer=self.buffer,
            format=self.format,
            event_socket=self.event_socket,
            ip=self.ip,
            port=self.port,
        )

    def form_addr(self, addr):
        return f"{addr[0]}:{addr[1]}"

    def next(self):
        self.next_mw = True

    def shutdown(self):
        self._shutting_down = True
        for addr, session in self.sessions.copy().items():
            if self.get_session(addr) is None:
                continue
            self._close_socket(session["conn"], addr)
        if hasattr(self, "socket"):
            self.socket.close()

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _close_socket(self, conn, addr):
        self.run_event(
            "on_session_close",
            Context(self, addr=addr, conn=conn, session=self.get_session(addr)),
        )
        self.sessions.pop(addr, None)
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()
        self.run_event("on_disconnect", Context(self, conn=conn, addr=addr))

    def close_socket(self, conn, addr):
        if "event_socket" in self.get_session(addr):
            self._close_socket(
                self.sessions[addr].event_socket, self.sessions[addr].event_socket_addr
            )
        self._close_socket(conn, addr)

    def accept_connections(self):
        self.run_event("on_start", Context(self, ip=self.ip, port=self.port))
        self.socket.listen()
        while True:
            try:
                conn, addr = self.socket.accept()
            except ConnectionAbortedError:
                if self._shutting_down:
                    return

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
                _session = self.get_session(addr)

                if not self.run_event(
                    "before_packet",
                    Context(self, conn=conn, addr=addr, session=_session),
                ):
                    return self.close_socket(conn, addr)

                pkt = self.recv(conn, addr)
                ctx = Context(
                    self,
                    pkt=Store(pkt),
                    conn=conn,
                    addr=addr,
                    session=_session,
                    next=self.next,
                )
                path = pkt.get("path", None)
                ctx.request = path
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
                        del ctx.next
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
                s = self.get_session(addr)
                if s is None:
                    return
                self.run_event(
                    "on_session_close",
                    Context(self, addr=addr, conn=conn, session=s),
                )
                self.sessions.pop(addr, None)
                self.run_event("on_disconnect", Context(self, conn=conn, addr=addr))
                break

    def init_connection(self, conn, addr):
        echo_pkt = self.recv_raw(conn, self.init_buffer)
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
        self.send_raw(dict(pem=pem, kdn=num2), conn, self.init_buffer)

        num_3_enc = self.recv_raw(conn, self.init_buffer)["num"]

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

        return Crypt.hashing_function(key_deriv)

    def create_session(self, conn, addr):
        self.sessions[addr] = Store(conn=conn)
        s = self.run_event("create_session", Context(self, conn=conn, addr=addr))

        if isinstance(s, EventGroupReturn) or isinstance(s, list):
            for i in s:
                self.sessions[addr] |= i

        elif isinstance(s, dict):
            self.sessions[addr] |= s

    def handle_client(self, conn, addr):
        if not self.run_event("connect_check", Context(self, conn=conn, addr=addr)):
            conn.close()
            self.run_event("on_connection_refusal", Context(self, conn=conn, addr=addr))
            sys.exit()

        self.create_session(conn, addr)
        try:
            key = self.init_connection(conn, addr)
            self.get_session(addr)["key"] = key

        except Exception as e:
            self.run_event(
                "on_connect_fail",
                Context(
                    self, error=e, addr=addr, conn=conn, session=self.get_session(addr)
                ),
            )
            return self.close_socket(conn, addr)
        client_info = self.recv(conn, addr, self.init_buffer)
        client_info["addr"] = addr
        client_info["conn"] = conn
        if not self.run_event("client_info", client_info):
            self.run_event(
                "on_connection_refusal",
                Context(self, conn=conn, addr=addr, client_info=client_info),
            )
            return self.close_socket(conn, addr)
        self.send(
            dict(
                status=200,
                info="Initiated secure connection",
                buffer=self.buffer,
                event_socket=self.event_socket,
                success=True,
                **self.run_event("server_info"),
            ),
            conn,
            addr,
            self.init_buffer,
        )
        self.run_event(
            "on_connect",
            Context(self, conn=conn, addr=addr, session=self.get_session(addr)),
        )
        self.recv_loop(conn, addr)

    def get_request(self, path):
        return self.paths.get(path, None)

    def register_path(self, path, func):
        req = Request(path, func)
        self.paths[path] = req
        return req

    def register_middleware(self, func):
        mw = Middleware(func)
        self.middlewares.append(mw)
        return mw

    def register_base_event(self, event, func):
        self.base_events[event] = Event(func, event)
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

    def route(self, path):
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

    def get_server_ip(self):
        return socket.gethostbyname(self.hostname)

    def on_event_error(self, error, event, exc_info):
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(error)
        print(f"\nthis error occurred in {event}")
        if self.kill_on_error:
            os._exit(0)

    def on_request_error(self, ctx, error):
        traceback.print_exception(ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(error)
        print(f"\nthis error occurred in {ctx.request}")
        if self.kill_on_error:
            os._exit(0)

    def on_middleware_error(self, ctx, error):
        traceback.print_exception(ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(error)
        print(f"\nthis error occurred in middleware function")
        if self.kill_on_error:
            os._exit(0)

    def load_events(self):
        self.register_base_event("on_ready", lambda: None)
        self.register_base_event("on_request_error", self.on_request_error)
        self.register_base_event("on_event_error", self.on_event_error)
        self.register_base_event("connect_check", lambda x: True)
        self.register_base_event("create_session", lambda c: dict())
        self.register_base_event("on_middleware_error", self.on_middleware_error)
        self.register_base_event("before_packet", lambda x: True)
        self.register_base_event("server_info", lambda: {})

    def send_event(self, addr, event):
        if not self.event_socket:
            raise Exception("This server does not have event sockets enabled")

        session = self.get_session(addr)
        if not session:
            raise ValueError("Session not found")

        ev_sock = session.get("event_socket", None)
        ev_addr = session.get("event_socket_addr", None)
        if ev_sock is None or ev_addr is None:
            raise ClientError(f"{addr} has no event socket registered")

        self.send(event, ev_sock, ev_addr)

    def load_loggers(self):
        self.register_base_event(
            "on_connect",
            lambda ctx: zono.colorlogger.log(f"{self.form_addr(ctx.addr)} connected"),
        )
        self.register_base_event(
            "on_disconnect",
            lambda ctx: zono.colorlogger.log(
                f"{self.form_addr(ctx.addr)} disconnected"
            ),
        )
        self.register_base_event(
            "on_start",
            lambda ctx: zono.colorlogger.major_log(
                f"Server listening @{ctx.ip}:{ctx.port}"
            ),
        )
        self.register_base_event(
            "on_client_error",
            lambda ctx: zono.colorlogger.error(
                f"Client error {self.form_addr(ctx.addr)}: {ctx.msg}"
            ),
        )
        self.register_base_event(
            "on_connection_refusal",
            lambda ctx: zono.colorlogger.error(
                f"{self.form_addr(ctx.addr)} connection refused"
            ),
        )
        self.register_base_event(
            "on_connect_fail",
            lambda ctx: zono.colorlogger.error(
                f"{self.form_addr(ctx.addr)} connection initiation failed"
            ),
        )

    def get_session_key(self, addr):
        s = self.sessions.get(addr, None)
        if s:
            return s.key

    def get_session(self, addr):
        return self.sessions.get(addr, None)

    def send(self, pkt, conn, addr, buffer=None):
        buffer = buffer or self.buffer
        message = objcrypt.encrypt(pkt, self.get_session_key(addr))
        msg_length = len(message)
        send_length = str(msg_length).encode(self.format)
        send_length += b" " * (self.buffer - len(send_length))
        conn.send(send_length)
        conn.send(message)

    def recv(self, conn, addr, buffer=None):
        buffer = buffer or self.buffer
        try:
            msg_len = int(conn.recv(buffer).decode(self.format))
        except ValueError:
            raise socket.error
        msg = conn.recv(msg_len)
        obj = objcrypt.decrypt(msg, self.get_session_key(addr))
        return obj

    def load_module(self, module):
        if not isinstance(module, dict):
            return
        if "setup" in module:
            module["setup"](Context(self, module=module))
        if "events" in module:
            for ev, handler in module["events"].items():
                self.set_event(ev, handler)
        if "paths" in module:
            for path, handler in module["paths"].items():
                self.register_event(path, handler)

        if "middleware" in module:
            for middleware in module["middleware"]:
                self.register_middleware(middleware)

    def send_raw(self, pkt, conn, buffer=None):
        buffer = buffer or self.buffer
        message = objcrypt.encode(pkt)
        msg_length = len(message)
        send_length = str(msg_length).encode(self.format)
        send_length += b" " * (buffer - len(send_length))
        conn.send(send_length)
        conn.send(message)

    def recv_raw(self, conn, buffer=None):
        buffer = buffer or self.buffer
        msg_len = int(conn.recv(buffer).decode(self.format))
        msg = conn.recv(msg_len)
        msg = objcrypt.decode(msg)
        return msg

    def is_event_socket(self, addr):
        s = self.get_session(addr)
        if s is None:
            return
        return s.get("parent_addr", None) or False

    def _event_socket(self, ctx):
        addr = tuple(ctx.pkt.get("addr", None))
        key = ctx.pkt.get("key", None)

        if not (addr and key):
            return ctx.send(dict(success=False, error=True, info="Incomplete packet"))

        user_session = self.get_session(addr)
        if user_session is None:
            return ctx.send(
                dict(success=False, error=True, info="session does not exist")
            )

        if not user_session["key"] == key:
            return ctx.send(
                success=False, error=True, info="Session key does not match"
            )

        ctx.session["parent_addr"] = addr
        user_session["event_socket"] = ctx.conn
        user_session["event_socket_addr"] = ctx.addr

        ctx.send(
            dict(success=True, error=False, info="Registered event socket successfully")
        )
        self.run_event(
            "event_socket_registered",
            Context(
                self,
                client_session=user_session,
                addr=ctx.addr,
                conn=ctx.conn,
                parent_addr=addr,
            ),
        )

    def load_paths(self):
        if self.event_socket:
            self.register_path("_event_socket", self._event_socket)

    def run(self):
        self.init_socket()
        self.accept_connections()
