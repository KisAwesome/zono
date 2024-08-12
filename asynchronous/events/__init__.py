from .events import EventManager
from .types import Event,EventError,EventGroupReturn,event


def attach(cls):
    ev_man = EventManager()
    ev_man.attach(cls)
    return ev_man


def deattach(cls):
    for name in cls.event_manager.attrs:
        if hasattr(cls, name):
            delattr(cls, name)
    if hasattr(cls, "event_manager"):
        delattr(cls, "event_manager")
