from zono.asynchronous.server.types import (
    Request,
    Event,
    Middleware,
    route,
    middleware,
    event,
)


class ServerModule:
    def __new__(cls, *args, **kwargs):
        cls = super().__new__(cls)
        mod_name = getattr(cls, '__name__', None) or type(cls).__name__
        module = dict(paths=dict(), events=dict(), middleware=[], cls=cls,name=mod_name)

        for i in dir(cls):
            v = getattr(cls, i)

            if isinstance(v, Request):
                v.instance = cls
                module["paths"][i] = v

            elif isinstance(v, Middleware):
                v.instance = cls
                module["middleware"].append(v)

            elif isinstance(v, Event):
                func = list(v.events)[0]
                func.instance = cls
                module["events"][v.name] =func 
        cls.__init__(*args, **kwargs)
        if hasattr(cls, "setup"):
            module["setup"] = cls.setup
        if hasattr(cls, "module"):
            cls.module(module)

        return module
