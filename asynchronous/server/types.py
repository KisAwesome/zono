from zono.socket.server.exceptions import MiddlewareError,RequestError,ClientError
from zono.asynchronous.events.types import wrap_coro,event,Event,EventGroupReturn
from zono.socket.server.types import Context as _Context
import asyncio
import sys



has_instance = lambda x: hasattr(x, "instance")

        
def route(path: str = None,*middlewares):
    def wrapper(func):
        name = path
        if path is None:
            name = func.__name__

        if not callable(func):
            raise ValueError("Request function must be callable")
        return Request(name, func,middlewares)

    return wrapper


def middleware(func):
    return Middleware(func)


class Connection:
    def __init__(self,reader,writer):
        self.reader = reader
        self.writer = writer
    async def send(self,data):
        self.writer.write(data)
        await self.writer.drain()
        
    async def recv(self,n):
        return await self.reader.read(n)
    
    async def close(self):
        if self.writer.is_closing():
            return
        self.writer.close()
        await self.writer.wait_closed()
    
    @property
    def addr(self):
        return self.writer.get_extra_info('peername')


def send_wrapper(app,conn,addr,ctx):
    async def wrapper(data):
        await app.send(data,conn,addr)
        ctx.responses.append(data)
        
    return wrapper

def close_wrapper(app,conn,addr):
    async def wrapper():
        await app.close_socket(conn,addr)
        
    return wrapper
def recv_wrapper(app,conn,addr):
    async def wrapper(timeout=None):
        return await app.recv(conn,addr,timeout=timeout)
    return wrapper

class Context(_Context):
    def __init__(self, app, **kwargs):
        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])
        self.store = app.store
        self._dict = dict(app=app, store=self.store, **kwargs)
        if hasattr(self, "conn") and hasattr(self, "addr"):
            self.responses = []
            self.send = send_wrapper(app,self.conn,self.addr,self)
            self.recv = recv_wrapper(app,self.conn,self.addr)
            self.close_socket = close_wrapper(app,self.conn,self.addr)
            self._dict |= dict(
                responses=self.responses,
                send=self.send,
                recv=self.recv,
                close_socket=self.close_socket,
            )

    
    async def create(self):
        await self.app.run_event("create_context", self)


class Middleware(Event):
    def __init__(self, callback) -> None:
        self.error_handler = None
        self.callback = callback
        if has_instance(self):
            self.instance = callback.instance

    async def __call__(self, ctx):
        try:
            if has_instance(self):
                return await self.callback(self.instance, ctx)
            await self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            err = MiddlewareError(ctx, e, info) 
            if callable(self.error_handler):
                await self.error_handler(err)
                return
            
            return err
class Request(Event):
    def __init__(self, path, callback,middlewares=[]):
        self.middlewares =set()
        for i in middlewares:
            self.add_middleware(i)
        
        self.path = path
        self.callback = callback
        self.error_handler = None
        if has_instance(self):
            self.instance = callback.instance

    async def __call__(self, ctx):
        try:
            if has_instance(self):
                return await self.callback(self.instance, ctx)
            await self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()

            info = sys.exc_info()
            err = RequestError(ctx, e, info)
            if callable(self.error_handler):
                await self.error_handler(err.ctx)
                return
            return err

    def add_middleware(self, func):
        if asyncio.iscoroutinefunction(func) is False:
            func = wrap_coro(func)
        self.middlewares.add(func)
            
    def middleware(self,func):
        if asyncio.iscoroutinefunction(func) is False:
            func = wrap_coro(func)
        mw = Middleware(func)
        self.add_middleware(mw)
        return mw

    


def needs_attr(*attrs,fail=None):
    async def needs_attr_mw(ctx):
        
        if hasattr(ctx.pkt,'keys') and all(e in ctx.pkt.keys() for e in attrs):
            return ctx.next()
        
        if fail:
            await ctx.send(fail)

    return needs_attr_mw