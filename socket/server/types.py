from .exceptions import RequestError, MiddlewareError, EventError
import sys
from zono.store import Store


def request(path):
    def wrapper(func):
        if not callable(func):
            raise ValueError("Request function must be callable")
        return Request(path)

    return wrapper


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
        self.send = lambda pkt: self.app.send(pkt, self.conn, self.addr)
        self.revc = lambda: self.app.recv(self.conn, self.addr)

    def __repr__(self) -> str:
        string = ""
        for p, value in vars(self).items():
            string += f"{p} : {value}\n"

        return string


class Event:
    def __init__(self, callback, name):
        self.name = name
        self.callback = callback
        self.error_handler = None

    def __call__(self, *args, **kwds):
        if not hasattr(self, "instance"):
            self.instance = getattr(self.callback, "instance", None)

        try:
            if self.instance:
                return self.callback(self.instance, *args, **kwds)
            else:
                return self.callback(*args, **kwds)

        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            raise EventError(None, e, info)

    def error(self, cb):
        if not callable(cb):
            raise ValueError("Error handler function must be callable")

        func = Event(cb)
        self.error_handler = func
        return func


class EventGroup(Event):
    def __init__(self, name):
        self.events = []
        self.name = name
        self.error_handler = None

    def register_event(self, event):
        ev = event
        if not (isinstance(event, Event) or issubclass(event, Event)):
            ev = Event(event, self.name)
        self.events.append(ev)
        return ev

    def add(self):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Event function must be callable")
            return self.register_event

        return wrapper

    def __call__(self, *args, **kwds):
        returns = EventGroupReturn()
        for i in self.events:
            try:
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

    def __call__(self, ctx):
        if not hasattr(self, "instance"):
            self.instance = getattr(self.callback, "instance", None)
        try:
            if self.instance:
                self.callback(self.instance, ctx)
            else:
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

    def __call__(self, ctx):
        if not hasattr(self, "instance"):
            self.instance = getattr(self.callback, "instance", None)
        try:
            if self.instance:
                self.callback(self.instance, ctx)
            else:
                self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            raise MiddlewareError(ctx, e, info)


class MiddlewareEvent(Event):
    pass
