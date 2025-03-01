from .server import SecureServer
from .types import Request, Middleware, EventGroup,Interval
from zono.events import Event


class Server:
    def __new__(cls, ip="", port=None, *args, **kwargs) -> SecureServer:
        server = SecureServer(ip, port)
        if cls == Server:
            return server
        cls = super().__new__(cls)

        if hasattr(cls, "modules"):
            for i in cls.modules:
                server.load_module(i)
        for i in dir(cls):
            v = getattr(cls, i)
            if isinstance(v, Request):
                v.instance = cls
                server.register_path(v.path, v)

            elif isinstance(v, Middleware):
                v.instance = cls
                server.register_middleware(v)

            elif isinstance(v,Interval):
                v.instance = cls
                server.intervals.add(v.interval)
            elif isinstance(v, EventGroup) or isinstance(v, Event):
                v.instance = cls
                server.register_event(v.name, v)

        cls.server = server
        server.parent = cls
        cls.shutdown = server.shutdown
        # cls.send_event = server.send_event
        # cls.send = server.send
        # cls.recv = server.recv
        # cls.run_event = server.run_event
        cls.__init__(*args, **kwargs)

        return server
