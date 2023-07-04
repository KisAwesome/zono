from .events import EventGroup, Event, EventError, EventManager
from .types import event, EventGroupReturn


def attach(cls, always_event_group=True):
    ev_man = EventManager(always_event_group=always_event_group)
    ev_man.attach(cls)
    return ev_man


def deattach(cls):
    for name in cls.event_manager.attrs:
        if hasattr(cls, name):
            delattr(cls, name)
    if hasattr(cls, "event_manager"):
        delattr(cls, "event_manager")
