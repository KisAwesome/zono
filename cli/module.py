from .types import Module as _Module
from .types import Command, Event, CommandEvent
import inspect


class Module(object):
    def __new__(cls, *args, **kwargs):
        cls = super().__new__(cls)
        commands = []
        events = []
        for i in dir(cls):
            kv = getattr(cls, i)
            if isinstance(kv, Command) or isinstance(kv, _Module):
                commands.append(kv)
            elif isinstance(kv, Event):
                events.append(kv)
        name = getattr(cls, "name", None) or cls.__class__.__name__
        name = name if isinstance(name, str) else cls.__class__.__name__ 
        description = getattr(cls, "description", getattr(cls, "__doc__", None))
        module = _Module(name, description)
        module.commands = commands
        for k, v in inspect.getmembers(cls):
            if isinstance(v, Command):
                v.callback.instance = cls
                v.instance = cls
                # setattr(cls, k, v)

            elif isinstance(v, CommandEvent):
                v.instance = cls
                v.callback.instance = cls

                # setattr(cls, k, v)

            elif isinstance(v, Event):
                v.instance = cls
                v.callback.instance = cls
                # setattr(cls, k, v)

        cls._module_ = module
        cls.__init__(*args, **kwargs)
        module._class_ = cls
        for i in events:
            module.register_event(i.name, i.callback)
        return module
