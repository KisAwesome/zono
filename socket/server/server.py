from .types import (
    Store,
    Event,
    Context,
    Request,
    Middleware,
    EventGroupReturn,
    Sessions,
)
from .exceptions import *
import cryptography.hazmat.primitives.asymmetric.padding
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.serialization
import zono.colorlogger
import zono.zonocrypt
import zono.workers
import zono.events
import zono.socket
import traceback
import threading
import secrets
import socket
import errno
import sys


Crypt = zono.zonocrypt.zonocrypt()


logger = zono.colorlogger.create_logger("zono.server", level=1)


class SecureServer:
    def __init__(self, ip="", port=None):
        self.port = port
        self.hostname = socket.gethostname()
        self.ip = ip or self.get_server_ip()
        self.init()

    def init(self):
        self.sessions = Sessions(self.session_update)
        self._warn_missing_response = True
        zono.events.attach(self, True)
        self._shutting_down = False
        self.timeout_duration = 10
        self.kill_on_error = True
        self.init_buffer = 512
        self.middlewares = []
        self.format = "utf-8"
        self.store = Store()
        self.next_mw = False
        self.intervals = []
        self.modules = []
        self.buffer = 512
        self.paths = {}
        self.load_events()

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

    def wrap_bool_event(self, ret, default=None):
        if isinstance(ret, EventGroupReturn):
            return all(ret)
        return ret or default

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

    def connection_status(self, conn):
        # return conn.getsockopt(socket.SOL_SOCKET, socket.SO_CONNECTED)
        if "closed" in str(conn):
            return False
        try:
            data = conn.recv(1)
            if data == b"":
                return True
            else:
                return False

        except socket.error as e:
            if (
                e.errno == errno.EWOULDBLOCK
                or e.errno == errno.EAGAIN
                or e.errno == errno.EBADF
            ):
                return False
            else:
                raise

    def shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        for interid in self.intervals:
            if zono.workers.get_interval(interid):
                zono.workers.cancel_interval(interid)

        for addr, session in self.sessions.copy().items():
            self._close_socket(session["conn"], addr)
        if hasattr(self, "socket"):
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            self.socket.close()

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _close_socket(self, conn, addr):
        session = self.get_session(addr)
        if session is not None:
            self.run_event(
                "on_session_close",
                Context(self, addr=addr, conn=conn, session=session),
            )
            self.sessions.pop(addr, None)
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()
        self.run_event(
            "on_disconnect", Context(self, conn=conn, addr=addr, session=session)
        )

    def close_socket(self, conn, addr):
        session = self.get_session(addr)
        if session is None:
            return
        self._close_socket(conn, addr)

    def accept_connections(self):
        self.run_event("on_start", Context(self, ip=self.ip, port=self.port))
        self.socket.listen()
        while not self._shutting_down:
            try:
                conn, addr = self.socket.accept()

            except ConnectionAbortedError:
                if self._shutting_down:
                    return
                raise
            except KeyboardInterrupt:
                self.shutdown()
            else:
                threading.Thread(
                    target=self.handle_client,
                    args=(conn, addr),
                ).start()

    def recv_loop(self, conn, addr):
        while True:
            try:
                _session = self.get_session(addr)

                if not self.wrap_bool_event(
                    self.run_event(
                        "before_packet",
                        Context(self, conn=conn, addr=addr, session=_session),
                    ),
                    default=True,
                ):
                    return self.close_socket(conn, addr)

                raw_pkt = self.recv(conn, addr, timeout=self.timeout_duration)
                pkt = self.wrap_pkt(raw_pkt)
                if not self.wrap_bool_event(
                    self.run_event(
                        "after_packet",
                        Context(self, conn=conn, addr=addr, session=_session, pkt=pkt),
                    ),
                    default=True,
                ):
                    return self.close_socket(conn, addr)
                ctx = Context(
                    self,
                    pkt=pkt,
                    conn=conn,
                    addr=addr,
                    session=_session,
                    next=self.next,
                    raw_pkt=raw_pkt,
                )
                if pkt.get("_keepalive", None) == True:
                    continue
                path = pkt.get("path", None)
                ctx.request = path
                self.next_mw = True
                for i in self.middlewares:
                    if not self.next_mw:
                        break
                    self.next_mw = False
                    ret = i(ctx)
                    if isinstance(ret, MiddlewareError):
                        self.run_event("on_middleware_error", ret.ctx, ret.error)

                if not self.next_mw:
                    continue

                if path in self.paths:
                    handler = self.paths[path]
                    del ctx.next
                    e = handler(ctx)
                    if ctx.responded is False and self._warn_missing_response:
                        logger.warning(
                            f"{path} did not return a response to the client"
                        )
                        self._warn_missing_response = False

                    if isinstance(e, RequestError):
                        if self.isevent("on_request_error"):
                            return self.run_event("on_request_error", e.ctx, e.error)

                        raise e.error

                else:
                    msg = "Client requested a path which does not exist"
                    ctx.error = ClientError(msg)
                    ctx.msg = msg

                    self.run_event("on_client_error", ctx)
                    self.send(
                        dict(
                            status=404, msg="Path not found", error=True, success=False
                        ),
                        conn,
                        addr,
                    )

            except ReceiveError as e:
                return self.close_socket(conn, addr)

    def wrap_pkt(self, pkt):
        if isinstance(pkt, dict):
            return Store(pkt)
        return Store(dict(content=pkt, raw=True))

    def init_connection(self, conn):
        echo_pkt = self.recv_raw(conn, self.init_buffer, 2)
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

        num2 = secrets.token_bytes(32)
        self.send_raw(dict(pem=pem, kdn=num2), conn, self.init_buffer)

        num_3_enc = self.recv_raw(conn, self.init_buffer, 2)["num"]

        num3 = private_key.decrypt(
            num_3_enc,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA384()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
                label=None,
            ),
        )

        key_deriv = num1 + num2 + num3
        return Crypt.hashing_function(key_deriv)

    def create_connection_session(self, conn, addr):
        self.sessions[addr] = Store(conn=conn)

    def handle_client(self, conn, addr):
        if not self.wrap_bool_event(
            self.run_event("connect_check", Context(self, conn=conn, addr=addr)),
            default=True,
        ):
            conn.close()
            self.run_event("on_connection_refusal", Context(self, conn=conn, addr=addr))
            sys.exit()

        self.create_connection_session(conn, addr)
        try:
            key = self.init_connection(conn)
            self.get_session(addr)["key"] = key

        except Exception as e:
            self.run_event(
                "on_connect_fail",
                Context(
                    self, error=e, addr=addr, conn=conn, session=self.get_session(addr)
                ),
            )
            return self.close_socket(conn, addr)
        self.send(
            dict(
                status=200,
                info="Initiated secure connection",
                buffer=self.buffer,
                success=True,
                timeout=self.timeout_duration,
                **(
                    self.wrap_event(
                        "server_info",
                        Context(self, addr=addr, conn=conn, session=self.get_session(addr)),
                    )
                    or {}
                ),
            ),
            conn,
            addr,
            self.init_buffer,
        )

        client_info = self.recv(conn, addr, self.init_buffer, 2)

        if not self.wrap_bool_event(
            self.run_event(
                "client_info",
                Context(
                    self, addr=addr, conn=conn, client_info=client_info, session=self.get_session(addr)
                ),
            ),
            default=True,
        ):
            self.run_event(
                "on_connection_refusal",
                Context(
                    self, conn=conn, addr=addr, client_info=client_info, session=self.get_session(addr)
                ),
            )
            return self.close_socket(conn, addr)

        self.send(
            dict(
                status=200,
                info="Connection established",
                success=True,
                **(
                    self.wrap_event(
                        "connection_established_info",
                        Context(
                            self,
                            addr=addr,
                            conn=conn,
                            client_info=client_info,
                            session=self.get_session(addr),
                        ),
                    )
                    or {}
                ),
            ),
            conn,
            addr,
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
        traceback.print_exception(
            exc_info[0], exc_info[1], exc_info[2], file=sys.stderr
        )
        print(error, file=sys.stderr)
        print(f"\nthis error occurred in {event}", file=sys.stderr)
        if self.kill_on_error:
            self.shutdown()

    def on_request_error(self, ctx, error):
        traceback.print_exception(
            ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2], file=sys.stderr
        )
        print(error, file=sys.stderr)
        print(f"\nthis error occurred in {ctx.request}", file=sys.stderr)
        if self.kill_on_error:
            self.shutdown()

    def on_middleware_error(self, ctx, error):
        traceback.print_exception(
            ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2], file=sys.stderr
        )
        print(error, file=sys.stderr)
        print(f"\nthis error occurred in middleware function", file=sys.stderr)
        if self.kill_on_error:
            self.shutdown()

    def session_update(self, key, value, action):
        self.run_event(
            "session_update", Context(self, key=key, value=value, action=action)
        )

    def load_events(self):
        self.register_event("on_request_error", self.on_request_error)
        self.register_event("on_middleware_error", self.on_middleware_error)

    def get_session_key(self, addr):
        s = self.sessions.get(addr, None)
        if s:
            return s['key']

    def get_session(self, addr):
        return self.sessions.get(addr, None)

    def send(self, pkt, conn, addr, buffer=None):
        buffer = buffer or self.buffer
        return zono.socket.send(
            conn, pkt, self.get_session_key(addr), self.format, buffer
        )

    def recv(self, conn, addr, buffer=None, timeout=None):
        buffer = buffer or self.buffer

        return zono.socket.recv(
            conn, buffer, timeout, self.get_session_key(addr), self.format
        )

    def load_module(self, module):
        if not isinstance(module, dict):
            return
        if "setup" in module:
            module["setup"](Context(self, module=module))
        if "events" in module:
            for ev, handler in module["events"].items():
                self.register_event(ev, handler)
        if "paths" in module:
            for path, handler in module["paths"].items():
                self.register_path(path, handler)

        if "middleware" in module:
            for middleware in module["middleware"]:
                self.register_middleware(middleware)
        if "modules" in module:
            for i in module["modules"]:
                self.load_modules(i)

        self.modules.append(module)

    def send_raw(self, pkt, conn, buffer=None):
        return zono.socket.send_raw(conn, pkt, self.format, buffer)

    def recv_raw(self, conn, buffer=None, timeout=None):
        buffer = buffer or self.buffer
        return zono.socket.recv_raw(conn, buffer, self.format, timeout)

    def is_event_socket(self, addr, *_):
        return False

    def run(self):
        self.init_socket()
        self.accept_connections()
