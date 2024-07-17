from .exceptions import RequestError, MiddlewareError
from zono.events import EventGroup, EventGroupReturn
from zono.events import Event
from zono.store import Store
import zono.workers
import traceback
import pprint
import sys


has_instance = lambda x: hasattr(x, "instance")


        
def route(path: str = None):
    def wrapper(func):
        name = path
        if path is None:
            name = func.__name__

        if not callable(func):
            raise ValueError("Request function must be callable")
        return Request(name, func)

    return wrapper


def interval(time):
    def wrapper(func):
        if not callable(func):
            raise ValueError(" function must be callable")
        return Interval(time, func)

    return wrapper


def middleware(func):
    return Middleware(func)


def event(event_name=None):
    def wrapper(func):
        name = event_name
        if event_name is None:
            name = func.__name__

        if not callable(func):
            raise ValueError("Event must be callable")

        return Event(func, name)

    return wrapper


def send_wrapper(ctx, app):
    def wrapped(pkt):
        app.send(pkt, ctx.conn, ctx.addr)
        ctx.responses.append(pkt)

    return wrapped


class Interval(Event):
    def __init__(self,tick,callback):
        self.interval = zono.workers.Interval(tick,self.__call__,True)
        name = f'interval-{self.interval.interval_id}'
        if has_instance(self):
            self.instance = callback.instance
        super().__init__(callback,name)
        
    
    def __call__(self, *args,**kwargs):
        try:
            if has_instance(self):
                return self.callback(self.instance, *args,**kwargs)
            self.callback(ctx,*args,**kwargs)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()

            info = sys.exc_info()
            err = RequestError(ctx, e, info)
            if callable(self.error_handler):
                self.error_handler(err.ctx)
                return
            raise err


class Context:
    def __init__(self, app, **kwargs):
        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])
        self.store = app.store
        self._dict = dict(app=app, store=self.store, **kwargs)
        if hasattr(self, "conn") and hasattr(self, "addr"):
            self.responses = []
            self.send = send_wrapper(self, app)
            self.recv = lambda: self.app.recv(self.conn, self.addr)
            self.close_socket = lambda: self.app.close_socket(self.conn, self.addr)
            self._dict |= dict(
                responses=self.responses,
                send=self.send,
                recv=self.recv,
                close_socket=self.close_socket,
            )
        self.app.run_event("create_context", self)

    def __repr__(self) -> str:
        return pprint.pformat(self._dict)


class Request(Event):
    def __init__(self, path, callback,middlewares=[]):
        self.middlewares = middlewares
        self.path = path
        self.callback = callback
        self.error_handler = None
        if has_instance(self):
            self.instance = callback.instance

    def __call__(self, ctx):
        try:
            if has_instance(self):
                return self.callback(self.instance, ctx)
            self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()

            info = sys.exc_info()
            err = RequestError(ctx, e, info)
            if callable(self.error_handler):
                self.error_handler(err.ctx)
                return
            return err


class Middleware(Event):
    def __init__(self, callback) -> None:
        self.error_handler = None
        self.callback = callback
        if has_instance(self):
            self.instance = callback.instance

    def __call__(self, ctx):
        try:
            if has_instance(self):
                return self.callback(self.instance, ctx)
            self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            err = MiddlewareError(ctx, e, info)
            if callable(self.error_handler):
                self.error_handler(err.ctx)
                return
            return err


class Sessions(dict):
    def __init__(self, callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.callback = callback

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._run_callback(key, value, "set")

    def __delitem__(self, key):
        value = self[key]
        super().__delitem__(key)
        self._run_callback(key, value, "delete")

    def pop(self, key, default=None):
        value = super().pop(key, default)
        self._run_callback(key, value, "pop")
        return value

    def update(self, *args, **kwargs):
        updated_dict = dict(self)
        super().update(*args, **kwargs)
        self._run_callback(None, updated_dict, "update")

    def _run_callback(self, key, value, action):
        if self.callback is not None:
            self.callback(key, value, action)
