import asyncio 
from zono.socket.exceptions import ReceiveError,SendError
from zono.socket.server.types import Store
from .types import Middleware,Request,Context,Connection,MiddlewareError,ClientError,RequestError,wrap_coro,EventGroupReturn
import sys
import traceback
from zono.asynchronous.events import Event, attach
from zono.socket.server.encryption import *
import socket
import errno
import secrets


show_full_error = False


def wrap_error(e):
    if zono.socket.show_full_error:
        return e


objcrypt = zono.zonocrypt.zonocrypt(serialization='yaml')


async def  _recv(conn, buffer):

    try:
        return await conn.recv(buffer)

    # except socket.timeout as e:
    #     raise ReceiveError(2) from wrap_error(e)

    except ConnectionResetError as e:
        raise ReceiveError(5) from wrap_error(e)
    # except OSError as err:
    #     if err.errno == errno.EBADF:
    #         raise ReceiveError(4) from wrap_error(err)

    #     raise err


async def _send(conn, data):
    await conn.send(data)
    # try:
    #     conn.sendall(data)
    # except socket.timeout as e:
    #     raise SendError(2) from wrap_error(e)
    # except BrokenPipeError as e:
    #     raise SendError(6) from wrap_error(e)
    # except ConnectionAbortedError as e:
    #     raise SendError(13) from wrap_error(e)
    # except OSError as err:
    #     if err.errno == errno.EBADF:
    #         raise SendError(4) from wrap_error(err)
    #     raise err
    # return 0


async def recv(conn, buffer, timeout, session_key, _format):
    
    try:
        async with asyncio.timeout(timeout):
            pck = await _recv(conn, buffer)
    except asyncio.TimeoutError as e:
        raise ReceiveError(2) from wrap_error(e)
    
    try:
        pck = pck.decode(_format)
        if len(pck) == 0:
            raise ReceiveError(12)
        msg_len = int(pck)
    except ValueError as e:
        raise ReceiveError(1) from wrap_error(e)
    try:
        async with asyncio.timeout(timeout):
            msg = await _recv(conn, msg_len)
    except asyncio.TimeoutError as e:
        raise ReceiveError(2) from wrap_error(e)
    obj = await asyncio.to_thread(objcrypt.decrypt,msg, session_key)
    return obj
    # try:
    #     conn.settimeout(timeout)
    # except OSError as err:
    #     if err.errno == errno.EBADF:
    #         raise ReceiveError(14) from wrap_error(err)


    # msg = _recv(conn, msg_len)

    # try:
    #     obj = objcrypt.decrypt(msg, session_key)
    # except zono.zonocrypt.IncorrectDecryptionKey as e:
    #     raise ReceiveError(3) from wrap_error(e)
    # return obj


async def send(conn, pkt, session_key, _format, buffer):
    message = await asyncio.to_thread(objcrypt.encrypt,pkt, session_key)
    msg_length = len(message)
    send_length = str(msg_length).encode(_format)
    send_length += b" " * (buffer - len(send_length))

    await _send(conn, send_length)
    await _send(conn, message)
    return 0


async def send_raw(conn, pkt, _format, buffer):
    message = await asyncio.to_thread(objcrypt.encode,pkt)
    msg_length = len(message)

    send_length = str(msg_length).encode(_format)
    send_length += b" " * (buffer - len(send_length))

    await _send(conn, send_length)
    await _send(conn, message)
    return 0


async def recv_raw(conn, buffer, _format, timeout, decode=True):
    try:
        async with asyncio.timeout(timeout):
            lenpkt = await _recv(conn, buffer)
            
    except asyncio.TimeoutError as e:
        raise ReceiveError(2) from wrap_error(e)
    
    msg_len = int(lenpkt.decode(_format))
    try:
        async with  asyncio.timeout(timeout):
            msg = await _recv(conn, msg_len)
    except asyncio.TimeoutError as e:
        raise ReceiveError(2) from wrap_error(e)
    if decode:
        msg = await asyncio.to_thread(objcrypt.decode,msg)
    return msg



class SecureServer:
    def __init__(self, ip="", port=None):
        self.port = port or 8080
        self.ip = ip or self.get_server_ip()
        self.logger =  zono.colorlogger.create_logger("zono.server", level=1)
        self.Crypt = zono.zonocrypt.zonocrypt()
        self.init()

    def init(self):
        self.sessions = dict()
        self._warn_missing_response = True
        attach(self)
        self._shutting_down = False
        self.timeout_duration = 10
        self.kill_on_error = True
        self.init_buffer = 64
        self.middlewares = set()
        self.format = "utf-8"
        self.store = Store()
        self.next_mw = False
        self.intervals = set()
        self.modules = {}
        self.buffer = 128
        self.paths = {}
        self.load_events()
        
    async def wrap_event(self, event, *args, **kwargs):
        ret = await self.run_event(event, *args, **kwargs)
        if isinstance(ret, dict) or ret is None:
            return ret
        n = dict()
        for i in ret:
            if i is None:
                self.logger.error(f"a sub event in {event} group returned None")
                continue
            n |= i
        return n

    async def wrap_list_event(self, event, *args, **kwargs):
        ret = await self.run_event(event, *args, **kwargs)
        if ret is None:
            return ret
        if isinstance(ret,EventGroupReturn):
            lst = []

            for i in ret:
                if isinstance(i, list):
                    lst.extend(i)

            return lst
        return ret

    def get_session_key(self, addr):
        s = self.sessions.get(addr, None)
        if s:
            return s["key"]

    def get_session(self, addr):
        return self.sessions.get(addr, None)
    def wrap_bool_event(self, ret, default=None):
        if ret is None:
            return default
        if isinstance(ret, EventGroupReturn):
            return all(ret)
        return ret
    
    def form_addr(self, addr):
        return f"{addr[0]}:{addr[1]}"

    def next(self):
        self.next_mw = True
        
    def wrap_pkt(self, pkt):
        if isinstance(pkt, dict):
            return Store(pkt)
        return Store(dict(content=pkt, raw=True))
    
    def create_connection_session(self, conn, addr):
        self.sessions[addr] = Store(conn=conn)
    
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
    
    async def _close_socket(self, conn, addr,connected=True):
        session = self.get_session(addr)
        if session is not None:
            await self.run_event(
                "on_session_close",
                Context(self, addr=addr, conn=conn, session=session),
            )
            self.sessions.pop(addr, None)
   
        await conn.close()
        if connected:
            await self.run_event(
            "on_disconnect", Context(self, conn=conn, addr=addr, session=session)
        )

    async def close_socket(self, conn, addr):
        session = self.get_session(addr)
        if session is None:
            return
        await self._close_socket(conn, addr)
        
    
    async def shutdown(self):
        await self.run_event('shutdown_server',Context(self))
        if self._shutting_down:
            return
        self._shutting_down = True
        # for interid in self.intervals:
        #     if zono.workers.get_interval(interid):
        #         zono.workers.cancel_interval(interid)

        for addr, session in self.sessions.copy().items():
            await self._close_socket(session["conn"], addr)

        await self.run_event('server_closed',Context(self))
        self.server.close()
        await self.server.wait_closed()

    
    def register_middleware(self, func):
        if isinstance(func, Middleware):
            mw = func
        else:
            if asyncio.iscoroutinefunction(func) is False:
                raise ValueError('Cannot register middleware that is not a coroutine')
            mw = Middleware(func)
        self.middlewares.add(mw)
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
    
    
    
    def load_events(self):
        self.register_event("on_request_error", self.on_request_error)
        self.register_event("on_middleware_error", self.on_middleware_error)
        self.set_event('on_event_error',self.on_event_error)

    async def on_event_error(self, error, event, exc_info):

        # traceback.print_exception(
            # exc_info[0], exc_info[1], exc_info[2], file=sys.stderr
        # )
        traceback.print_tb(error.__traceback__,limit=3)
        print(exc_info)
        print(error, file=sys.stderr)
        print(f"\nthis error occurred in {event}", file=sys.stderr)
        if self.kill_on_error:
            await self.shutdown()


    async def on_request_error(self, ctx, error):
        traceback.print_exception(
            ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2], file=sys.stderr
        )
        print(error, file=sys.stderr)
        print(f"\nthis error occurred in {ctx.request}", file=sys.stderr)
        if self.kill_on_error:
            await self.shutdown()
            

    async def on_middleware_error(self, ctx, error):
        traceback.print_exception(
            ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2], file=sys.stderr
        )
        print(error, file=sys.stderr)
        if getattr(ctx,'path_middleware') is True:
            print(f"\nthis error occurred in middleware function for path {ctx.path}", file=sys.stderr)
        else:
            print(f"\nthis error occurred in middleware function", file=sys.stderr)
        if self.kill_on_error:
            await self.shutdown()
    
    
    async def recv_raw(self,conn,buffer=None,timeout=None):
        buffer = buffer or self.buffer
        return await recv_raw(conn,buffer,self.format,timeout)
        
    async def send_raw(self,pkt,conn,buffer=None):
        buffer = buffer or self.buffer
        await send_raw(conn,pkt,self.format,buffer)
        
    async def send(self, pkt, conn, addr, buffer=None):
        buffer = buffer or self.buffer
        return await send(
            conn, pkt, self.get_session_key(addr), self.format, buffer
        )

    async def recv(self, conn, addr, buffer=None, timeout=None):
        buffer = buffer or self.buffer

        return await recv(
            conn, buffer, timeout, self.get_session_key(addr), self.format
        )
    
    async def init_connection(self, conn):
        echo_pkt = await self.recv_raw(conn, self.init_buffer, 1)

        num1 = echo_pkt["num"]

        private_key = await asyncio.to_thread(
            cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key,  public_exponent=65537, key_size=2048
        )
        public_key = private_key.public_key()

        pem = public_key.public_bytes(
            encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
            format=cryptography.hazmat.primitives.serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        num2 = secrets.token_bytes(32)
        await self.send_raw(dict(pem=pem, kdn=num2), conn, self.init_buffer)

        num_3_enc = await self.recv_raw(conn, self.init_buffer, 1)

        num3 = await asyncio.to_thread(private_key.decrypt,
            num_3_enc["num"],
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA512()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA512(),
                label=None,
            
            ))

        key_deriv = num1 + num2 + num3
        return await asyncio.to_thread(self.Crypt.hashing_function,key_deriv)
    
    async def recv_loop(self, conn, addr):
        while True:
            _session = self.get_session(addr)

            if not self.wrap_bool_event(
                await self.run_event(
                    "before_packet",
                    Context(self, conn=conn, addr=addr, session=_session),
                ),
                default=True,
            ):
                return await self.close_socket(conn, addr)
            try:
                raw_pkt = await self.recv(conn, addr, timeout=self.timeout_duration)
            except ReceiveError as e:
                print(e)
                if e.errorno in ():
                    continue
                return await self.close_socket(conn, addr)
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
            await ctx.create()
            if not self.wrap_bool_event(
                await self.run_event(
                    "after_packet",
                    ctx,
                ),
                default=True,
            ):
                return await self.close_socket(conn, addr)
            if pkt.get("_keepalive", None) == True:
                continue
            await self.handle_request(ctx, pkt,conn,addr)
            

    async def handle_request(self,ctx,pkt,conn,addr):
        path = pkt.get("path", None)
        ctx.request = path
        self.next_mw = True
        for i in self.middlewares:
            if not self.next_mw is True:
                return
            self.next_mw = False
            ret = await i(ctx)
            if isinstance(ret, MiddlewareError):
                await self.run_event("on_middleware_error", ret.ctx, ret.error)

        if not self.next_mw is True:
            return
        
        if isinstance(path,str) and path in self.paths:
            handler = self.paths[path]
            self.next_mw = True
            for i in handler.middlewares:
                if not self.next_mw is True:
                    return
                self.next_mw = False
                ret = await i(ctx)
                ctx.path_middleware = True
                if isinstance(ret, MiddlewareError):
                    await self.run_event("on_middleware_error", ret.ctx, ret.error)
            if not self.next_mw is True:
                return
            del ctx.next
            e = await handler(ctx)
            if len(ctx.responses) == 0 and self._warn_missing_response:
                self.logger.warning(
                    f"{path} did not return a response to the client"
                )
                # self._warn_missing_response = False

            if isinstance(e, RequestError):
                if self.isevent("on_request_error"):
                    return await self.run_event("on_request_error", e.ctx, e.error)
                raise e.error

            await self.run_event('on_request_processed',ctx)
        else:
            err = ClientError(404,ctx=ctx)

            await self.run_event("on_client_error", err.ctx)
            await self.send(
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
    
    async def handle_client(self, reader,writer):
        conn = Connection(reader,writer)
        addr = conn.addr

        ctx = Context(self, conn=conn, addr=addr)
        if not self.wrap_bool_event(
            await self.run_event("connect_check", ctx),
            default=True,
        ):
            await conn.close()
            await self.run_event("on_connection_refusal", ctx)
            return

        self.create_connection_session(conn, addr)
        try:
            key = await self.init_connection(conn)
            self.get_session(addr)["key"] = key

        except ReceiveError as e:
            ctx.error = e
            ctx.session =self.get_session(addr)
            await self.run_event(
                "on_connect_fail",
                ctx
            )
            return await self._close_socket(conn, addr,False)
        ctx.session = self.get_session(addr)
        await self.send(
            dict(
                status=200,
                info="Initiated secure connection",
                buffer=self.buffer,
                success=True,
                timeout=self.timeout_duration,
                **(
                    (await self.wrap_event(
                        "server_info",
                        ctx
                    ))
                    or {}
                ),
            ),
            conn,
            addr,
            self.init_buffer,
        )

        client_info = await self.recv(conn, addr, self.buffer, 2)
        ctx.client_info = client_info
        if not self.wrap_bool_event(
            await self.run_event(
                "client_info",
                ctx,
            ),
            default=True,
        ):
            await self.run_event(
                "on_connection_refusal",
                ctx,
            )
            return await self.close_socket(conn, addr)

        await self.send(
            dict(
                status=200,
                info="Connection established",
                success=True,
                **(
                    (await self.wrap_event(
                        "connection_established_info",
                        ctx,
                    ))
                    or {}
                ),
            ),
            conn,
            addr,
        )
        await self.run_event(
            "on_connect",
            ctx,
        )
        if self.wrap_bool_event(
            await self.run_event(
                "start_event_loop",
                ctx,
            ),
            default=True,
        ):
            await self.recv_loop(conn, addr)        
            
    
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
    
    async def run(self):
        await self.run_event('startup',Context(self))
        # self.start_intervals()
        try:
            self.server = await asyncio.start_server(client_connected_cb=self.handle_client,host=self.ip,port=self.port)
            async with self.server:
                await self.run_event("on_start", Context(self, ip=self.ip, port=self.port))
                await self.server.serve_forever()
                
        except KeyboardInterrupt:
            pass
        
    def start(self):
        try:
            asyncio.run(self.run())
            
        except KeyboardInterrupt:
            pass
        except asyncio.CancelledError:
            if self._shutting_down:
                return
            self.logger.fatal('Asyncio cancelled error')

    # conn.settimeout(timeout)
    # try:
    #     msg_len = int(_recv(conn, buffer).decode(_format))
    # except ValueError as e:
    #     raise ReceiveError(1) from wrap_error(e)
    # msg = _recv(conn, msg_len)
    # if decode:
    #     msg = objcrypt.decode(msg)
    # return msg


