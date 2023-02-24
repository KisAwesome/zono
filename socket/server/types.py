from .exceptions import RequestError, MiddlewareError, EventError
from zono.store import Store
from zono.events import Event
from zono.events import EventGroup as _EventGroup
import sys
import pprint


has_instance = lambda x: hasattr(x, "instance")


def request(path=None):
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


class EventGroupReturn(list):
    pass


def event(event_name=None):
    def wrapper(func):
        name = event_name
        if event_name is None:
            name = func.__name__

        if not callable(func):
            raise ValueError("Event must be callable")

        return Event(func, name)

    return wrapper


class Context:
    def __init__(self, app, **kwargs):
        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])
        self.store = app.store
        if hasattr(self, "conn") and hasattr(self, "addr"):
            self.send = lambda pkt: self.app.send(pkt, self.conn, self.addr)
            self.revc = lambda: self.app.recv(self.conn, self.addr)
            self.close_socket = lambda: self.app.close_socket(self.conn, self.addr)

        self._dict = dict(app=app, store=self.store, **kwargs)

    def __repr__(self) -> str:
        return pprint.pformat(self._dict)


class EventGroup(Event):
    def __init__(self, name):
        self.events = []
        self.name = name
        self.error_handler = None

    def register_event(self, event):
        ev = event
        if not isinstance(event, Event):
            ev = Event(event, self.name)

        if has_instance(ev.callback):
            self.instance = ev.callback.instance
        self.events.append(ev)
        return ev

    def add(self):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Event function must be callable")
            return self.register_event(func)

        return wrapper

    def __call__(self, *args, **kwds):
        returns = EventGroupReturn()
        for i in self.events:
            try:
                if has_instance(self):
                    returns.append(i(self.instance, *args, **kwds))
                    continue
                returns.append(i(*args, **kwds))

            except BaseException as e:
                info = sys.exc_info()
                raise EventError(None, e, info)
        return returns


class RequestEvent(Event):
    pass


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
            info = sys.exc_info()
            raise RequestError(ctx, e, info)


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
            raise MiddlewareError(ctx, e, info)


class MiddlewareEvent(Event):
    pass
