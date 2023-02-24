from .events import EventGroup, Event, EventError, EventManeger
from .types import event, EventGroupReturn


def attach(cls, always_event_group=True):
    ev_man = EventManeger(always_event_group=always_event_group)
    ev_man.attach(cls)
    return ev_man


def deattach(cls):
    for name in cls.event_maneger.attrs:
        if hasattr(cls, name):
            delattr(cls, name)
    if hasattr(cls, "event_maneger"):
        delattr(cls, "event_maneger")
