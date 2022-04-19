from .types import Module as _Module
from .types import Command,Event,CommandEvent
import inspect


class Module():
    def __new__(cls):
        CLASS = super().__new__(cls)
        commands = []
        events = []
        for i in dir(CLASS):
            kv = getattr(CLASS, i)
            if isinstance(kv, Command) or isinstance(kv, _Module):
                commands.append(kv)
            elif isinstance(kv,Event):
                events.append(kv)
        name = getattr(cls, 'name', None) or cls.__name__
        description = getattr(cls, 'description', getattr(cls,'__doc__',None))
        module = _Module(name, description)
        module.commands = commands
        Module.__init__(cls)
        CLASS.__init__()
        module.load_events()
        for i in events:
            module.register_event(i.name,i.callback)
        return module

    def __init__(self):
        for k, v in inspect.getmembers(self):
            if isinstance(v, Command):
                v.instance = self
                setattr(self, k, v)

            elif isinstance(v,CommandEvent):
                v.instance = self
                setattr(self,k,v)

            elif isinstance(v,Event):
                v.instance = self
                setattr(self,k,v)

            
