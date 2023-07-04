from .exceptions import RequestError, MiddlewareError
from zono.events import EventGroup,EventGroupReturn
from zono.events import Event
from zono.store import Store
import traceback
import pprint
import sys


has_instance = lambda x: hasattr(x, "instance")


def request(path: str = None):
    def wrapper(func):
        name = path
        if path is None:
            name = func.__name__

        if not callable(func):
            raise ValueError("Request function must be callable")
        return Request(name, func)

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
        ctx.responded = True
        ctx._dict['responded'] = True

    return wrapped


class Context:
    def __init__(self, app, **kwargs):

        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])
        self.store = app.store
        self._dict = dict(app=app, store=self.store, **kwargs)
        if hasattr(self, "conn") and hasattr(self, "addr"):
            self.responded = False
            self.send = send_wrapper(self, app)
            self.recv = lambda: self.app.recv(self.conn, self.addr)
            self.close_socket = lambda: self.app.close_socket(self.conn, self.addr)
            self._dict |= dict(responded=False,send=self.send,recv=self.recv,close_socket=self.close_socket)


    def __repr__(self) -> str:
        return pprint.pformat(self._dict)





class Request(Event):
    def __init__(self, path, callback):
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

            traceback.print_exc()

            info = sys.exc_info()
            return RequestError(ctx, e, info)


class Middleware(Event):
    def __init__(self, callback) -> None:
        self.error_handler = None
        self.callback = callback
        if has_instance(self):
            self.instance = callback.instance

    def __call__(self, ctx):
        try:
            if has_instance(self):
                self.callback(self.instance, ctx)
            self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            return MiddlewareError(ctx, e, info)

