from zono.socket.server.types import Event, EventGroup, event


class ClientModule:
    def __new__(cls, *args, **kwargs):
        cls = super().__new__(cls)
        
        mod_name = getattr(cls, '__name__', None) or type(cls).__name__

        module = dict(events=dict(), cls=cls,name=mod_name)

        for i in dir(cls):
            v = getattr(cls, i)

            if isinstance(v, EventGroup) or isinstance(v, Event):
                v.instance = cls
                module["events"][i] = v

        if hasattr(cls, "setup"):
            module["setup"] = cls.setup
        if hasattr(cls, "module"):
            cls.module(module)
        cls.__init__(cls, *args, **kwargs)

        return module
