from .securesocket import SecureSocket
from zono.events import Event, EventGroup


class Client(object):
    def __new__(cls, *args, **kwargs):
        socket = SecureSocket()
        if cls == Client:
            return socket
        cls = super().__new__(cls)

        for i in dir(cls):
            v = getattr(cls, i)
            if isinstance(v, EventGroup) or isinstance(v, Event):
                v.callback.instance = cls
                socket.register_event(v.name, v.callback)

        cls.socket = socket
        socket.parent = cls
        cls.connect = socket.connect
        cls.send = socket.send
        cls.recv = socket.recv
        cls.request = socket.request
        cls.__init__(*args, **kwargs)

        return socket
