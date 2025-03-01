import zono.workers
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
from .encryption import *
import zono.colorlogger
import zono.workers
import zono.events
import zono.socket
import traceback
import secrets
import socket
import errno
import sys



class SecureServer:
    def __init__(self, ip="", port=None):
        self.port = port
        self.ip = ip or self.get_server_ip()
        self.logger =  zono.colorlogger.create_logger("zono.server", level=1)
        self.Crypt = zono.zonocrypt.zonocrypt()
        self.init()

    def init(self):
        self.sessions = Sessions(self.session_update)
        self._warn_missing_response = True
        zono.events.attach(self, True)
        self._shutting_down = False
        self.timeout_duration = 10
        self.kill_on_error = True
        self.init_buffer = 64
        self.middlewares = []
        self.format = "utf-8"
        self.store = Store()
        self.next_mw = False
        self.intervals = set()
        self.modules = {}
        self.buffer = 128
        self.paths = {}
        self.load_events()
        # self.threads = []
    
    def wrap_event(self, event, *args, **kwargs):
        ret = self.run_event(event, *args, **kwargs)
        if isinstance(ret, dict) or ret is None:
            return ret
        n = dict()
        for i in ret:
            if i is None:
                self.logger.error(f"a sub event in {event} group returned None")
                continue
            n |= i
        return n

    def wrap_list_event(self, event, *args, **kwargs):
        ret = self.run_event(event, *args, **kwargs)
        if ret is None:
            return ret
        
        if isinstance(ret,EventGroupReturn):
            lst = []

            for i in ret:
                if isinstance(i, list):
                    lst.extend(i)

            return lst
        return ret

    def wrap_bool_event(self, ret, default=None):
        if ret is None:
            return default
        if isinstance(ret, EventGroupReturn):
            return all(ret)
        return ret

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
        self.run_event('shutdown_server',Context(self))
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
        # for t in self.threads:
        #     t.join()
        self.run_event('server_closed',Context(self))

    def init_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.ip, self.port))
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _close_socket(self, conn, addr,connected=True):
        session = self.get_session(addr)
        if session is not None:
            session.get('_internal').get('_thread').terminate()
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
        if connected:
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
                info = {}
                t = zono.workers.Thread(
                    target=self.handle_client,
                    args=(conn, addr,info),
                )
                info['_thread'] = t
                t.start()
                # self.threads.append(t)

    def recv_loop(self, conn, addr):
        while True:
            _session = self.get_session(addr)

            if not self.wrap_bool_event(
                self.run_event(
                    "before_packet",
                    Context(self, conn=conn, addr=addr, session=_session),
                ),
                default=True,
            ):
                return self.close_socket(conn, addr)
            try:
                raw_pkt = self.recv(conn, addr, timeout=self.timeout_duration)
            except ReceiveError as e:
                print(e)
                if e.errorno in ():
                    continue
                return self.close_socket(conn, addr)
            pkt = self.wrap_pkt(raw_pkt)
            ctx = Context(
                self,
                pkt=pkt,
                conn=conn,
                addr=addr,
                session=_session,
                next=self.next,
                raw_pkt=raw_pkt,
            )
            if not self.wrap_bool_event(
                self.run_event(
                    "after_packet",
                    ctx,
                ),
                default=True,
            ):
                return self.close_socket(conn, addr)
            if pkt.get("_keepalive", None) == True:
                continue
            self.handle_request(ctx, pkt,conn,addr)
            

    def handle_request(self,ctx,pkt,conn,addr):
        path = pkt.get("path", None)
        ctx.request = path
        self.next_mw = True
        for i in self.middlewares:
            if not self.next_mw is True:
                return
            self.next_mw = False
            ret = i(ctx)
            if isinstance(ret, MiddlewareError):
                self.run_event("on_middleware_error", ret.ctx, ret.error)

        if not self.next_mw is True:
            return
        
        if isinstance(path,str) and path in self.paths:
            handler = self.paths[path]
            self.next_mw = True
            for i in handler.middlewares:
                if not self.next_mw is True:
                    return
                self.next_mw = False
                ret = i(ctx)
                ctx.path_middleware = True
                if isinstance(ret, MiddlewareError):
                    self.run_event("on_middleware_error", ret.ctx, ret.error)
            if not self.next_mw is True:
                return
            del ctx.next
            e = handler(ctx)
            if len(ctx.responses) == 0 and self._warn_missing_response:
                self.logger.warning(
                    f"{path} did not return a response to the client"
                )
                # self._warn_missing_response = False

            if isinstance(e, RequestError):
                if self.isevent("on_request_error"):
                    return self.run_event("on_request_error", e.ctx, e.error)
                raise e.error

            self.run_event('on_request_processed',ctx)
        else:
            err = ClientError(404,ctx=ctx)

            self.run_event("on_client_error", err.ctx)
            self.send(
                dict(
                    status=404, msg="Path not found", error=True, success=False
                ),
                conn,
                addr,
            )
    
    def wrap_pkt(self, pkt):
        if isinstance(pkt, dict):
            return Store(pkt)
        return Store(dict(content=pkt, raw=True))

    def init_connection(self, conn):
        echo_pkt = self.recv_raw(conn, self.init_buffer, 1)
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

        num_3_enc = self.recv_raw(conn, self.init_buffer, 1)["num"]

        num3 = private_key.decrypt(
            num_3_enc,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA512()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA512(),
                label=None,
            ),
        )

        key_deriv = num1 + num2 + num3
        return self.Crypt.hashing_function(key_deriv)

    def create_connection_session(self, conn, addr,info):
        self.sessions[addr] = Store(conn=conn,_internal=info)

    def handle_client(self, conn, addr,info):
        ctx = Context(self, conn=conn, addr=addr)
        if not self.wrap_bool_event(
            self.run_event("connect_check", ctx),
            default=True,
        ):
            conn.close()
            self.run_event("on_connection_refusal", ctx)
            sys.exit()

        self.create_connection_session(conn, addr,info)
        try:
            key = self.init_connection(conn)
            self.get_session(addr)["key"] = key

        except ReceiveError as e:
            ctx.error = e
            ctx.session =self.get_session(addr)
            self.run_event(
                "on_connect_fail",
                ctx
            )
            return self._close_socket(conn, addr,False)
        ctx.session = self.get_session(addr)
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
                        ctx
                    )
                    or {}
                ),
            ),
            conn,
            addr,
            self.init_buffer,
        )

        client_info = self.recv(conn, addr, self.buffer, 2)
        ctx.client_info = client_info
        if not self.wrap_bool_event(
            self.run_event(
                "client_info",
                ctx,
            ),
            default=True,
        ):
            self.run_event(
                "on_connection_refusal",
                ctx,
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
                        ctx,
                    )
                    or {}
                ),
            ),
            conn,
            addr,
        )
        self.run_event(
            "on_connect",
            ctx,
        )
        if self.wrap_bool_event(
            self.run_event(
                "start_event_loop",
                ctx,
            ),
            default=True,
        ):
            self.recv_loop(conn, addr)

    def get_request(self, path):
        return self.paths.get(path, None)

    def register_path(self, path, func,*middlewares):
        if not callable(func):
            raise ValueError("Path handler must be callable")
        for i in middlewares:
            if not callable(i):
                raise ValueError("All middlewares must be callable")
        if isinstance(func,Request):
            req = func
        else:
            req = Request(path, func,middlewares)
        self.paths[path] = req
        return req

    def register_middleware(self, func):
        if isinstance(func, Middleware):
            mw = func
        else:
            mw = Middleware(func)
        self.middlewares.append(mw)
        return mw

    def route(self, path,*middlewares):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Request function must be callable")
            return self.register_path(path, func,*middlewares)

        return wrapper

    def middleware(self):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Middleware function must be callable")
            return self.register_middleware(func)

        return wrapper

    def get_server_ip(self):
        return 'localhost'

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
        if getattr(ctx,'path_middleware') is True:
            print(f"\nthis error occurred in middleware function for path {ctx.path}", file=sys.stderr)
        else:
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
        self.set_event('on_event_error',self.on_event_error)

    def get_session_key(self, addr):
        s = self.sessions.get(addr, None)
        if s:
            return s["key"]

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
            raise ValueError('Module must be a dict')

        name = module.get("name",None)
        if name is None:
            raise ValueError('Module must have a name value')
        if "setup" in module:
            import traceback

            try:
                module["setup"](Context(self, module=module))
            except Exception as e:
                traceback_lines = traceback.format_exception(type(e), e, e.__traceback__)
                relevant_traceback = traceback_lines[1:]
                print("".join(relevant_traceback).strip())
                sys.exit(1)
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
        self.modules[name] = module

    def send_raw(self, pkt, conn, buffer=None):
        buffer = buffer or self.buffer
        return zono.socket.send_raw(conn, pkt, self.format, buffer)

    def recv_raw(self, conn, buffer=None, timeout=None):
        buffer = buffer or self.buffer
        return zono.socket.recv_raw(conn, buffer, self.format, timeout)

    def start_intervals(self):
        for i in self.intervals:
            i.start()
    def is_event_socket(self, addr, *_):
        return False

    def run(self):
        self.run_event('startup',Context(self))
        self.start_intervals()
        self.init_socket()
        self.accept_connections()
