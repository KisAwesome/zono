from .types import EventGroup, Event, EventError
import traceback

__all__ = [
    "run_event",
    "events",
    "isevent",
    "event",
    "register_event",
    "set_event",
    "wait",
    "remove_event",
]


class EventManager:
    def __init__(self, always_event_group=True):
        self.events = {}
        self.attached_to = None
        self.always_event_group = always_event_group
        self.register_event("on_event_error", self.on_event_error)
        self.register_event("event_handler_error",self.event_handler_error)

    def remove_event(self, event):
        return self.events.pop(event, None)

    def isevent(self, event, event_group=False):
        if event_group:
            return isinstance(self.events.get(event, None), EventGroup)

        return event in self.events

    def wait(self, event, timeout=None):
        if not self.isevent(event):
            raise ValueError("Event does not exist")

        ev = self.events.get(event)
        # ev.event.clear()
        r = ev.event.wait(timeout=timeout)
        ev.event.clear()
        return r

    def set_event(self, event, func):
        if isinstance(func, Event) or isinstance(func, EventGroup):
            ev = func
        else:
            ev = Event(func, event)

        self.events[event] = ev
        return ev

    def register_event(self, event, func, event_group=False):
        if self.isevent(event):
            if isinstance(self.events[event], EventGroup):
                self.events[event].register_event(func)
            elif event_group or self.always_event_group:
                ev = EventGroup(event)
                ev.register_event(self.events[event])
                ev.register_event(func)
                self.events[event] = ev
            return

        if isinstance(func, Event) or isinstance(func, EventGroup):
            ev = func
        else:
            ev = Event(func, event)

        self.events[event] = ev
        return ev

    def event(self, event_name=None):
        def wrapper(func):
            name = event_name
            if event_name is None:
                name = func.__name__

            if not callable(func):
                raise ValueError("Event must be callable")

            return self.register_event(name, func)

        return wrapper

    def _run_event(self, event, *args, **kwargs):
        ev = self.events.get(event, False)
        if ev:
            ret = ev(*args, **kwargs)
            ev.event.set()
            return ret

    def run_event(self, event, *args, **kwargs):
        ret = self._run_event(event, *args, **kwargs)
        if isinstance(ret, EventError):
            r = self._run_event("on_event_error", ret.error, event, ret.exc_info)
            if isinstance(r, EventError):
                raise r.error
                # g =self._run_event('event_handler_error',ret.error, event, ret.exc_info,r.error,'on_event_error',r.exc_info)
            
                # if isinstance(g, EventError):
                #     raise ret.error
            return
        return ret

    def on_event_error(self, error, event, exc_info):
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(f"\nthis error occurred in {event}")
        
    def event_handler_error(self,origin_error,origin_event,origin_exc_info,error,event,exc_info):
        self.on_event_error(origin_error,origin_event,origin_exc_info)
        print()
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(f'\nAn error occurred in {event} while handling error for {origin_event}')


    def attach(self, cls):
        if not self.attached_to is None:
            raise Exception("This event manager is already attached to a class")
        for name in __all__:
            if hasattr(cls, name):
                continue
            attr = getattr(self, name)
            setattr(cls, name, attr)

        self.attached_to = cls

        cls.event_manager = self

    def deattach(self):
        if self.attached_to is None:
            raise Exception("This event manager is not attached to a class")
        for name in __all__:
            if hasattr(self.attached_to, name):
                delattr(self.attached_to, name)
        if hasattr(self.attached_to, "event_manager"):
            delattr(self.attached_to, "event_manager")

    def copy(self, other):
        ev = EventManager(self.always_event_group)
        ev.events = self.events.copy()
        ev.attach(other)
