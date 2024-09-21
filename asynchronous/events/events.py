from .types import  Event, EventError
import asyncio
import traceback

ev_manager_attrs = [
    "run_event",
    "events",
    "isevent",
    "event",
    "register_event",
    "set_event",
    "wait",
    "remove_event",
    'handlers_registered'
]


class EventManager:
    def __init__(self):
        self.events = {}
        self.attached_to = None
        self.register_event("on_event_error", self.on_event_error)

    def remove_event(self, event):
        return self.events.pop(event, None)

    def isevent(self, event):
        return event in self.events

    async def wait(self, event, timeout=None):
        if not self.isevent(event):
            raise ValueError("Event does not exist")

        ev = self.events.get(event)

        r = await ev.event.wait(timeout=timeout)
        ev.event.clear()
        return r

    def set_event(self, event, func):
        if isinstance(func, Event):
            ev = func
        else:
            ev = Event(event)
            ev.events.add(func)

        self.events[event] = ev
        return ev

    def register_event(self, event, func):
        if self.isevent(event):
            self.events[event].events.add(func)
            return
        ev = Event(event)
        ev.events.add(func)
        self.events[event] = ev


    def event(self, event_name=None):
        def wrapper(func):
            name = event_name
            if event_name is None:
                name = func.__name__

            if not callable(func):
                raise ValueError("Event must be callable")

            return self.register_event(name, func)

        return wrapper

    async def _run_event(self, event, *args, **kwargs):
        ev = self.events.get(event, False)
        if ev:
            ret = await ev(*args, **kwargs)
            ev.event.set()
            return ret

    async def run_event(self, event, *args, **kwargs):
        ret = await self._run_event(event, *args, **kwargs)
        if isinstance(ret, EventError):
            if  self.isevent('on_event_error'):
                r = await self._run_event("on_event_error", ret.error, event, ret.exc_info)
                if isinstance(r, EventError):
                    raise r.error
            
            else:
                raise ret.error
            
            return
        return ret

    async def on_event_error(self, error, event, exc_info):
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(f"\nthis error occurred in {event}")
        

    def attach(self, cls):
        if not self.attached_to is None:
            raise Exception("This event manager is already attached to a class")
        for name in ev_manager_attrs:
            if hasattr(cls, name):
                continue
            attr = getattr(self, name)
            setattr(cls, name, attr)

        self.attached_to = cls

        cls.event_manager = self

    def deattach(self):
        if self.attached_to is None:
            raise Exception("This event manager is not attached to a class")
        for name in ev_manager_attrs:
            if hasattr(self.attached_to, name):
                delattr(self.attached_to, name)
        if hasattr(self.attached_to, "event_manager"):
            delattr(self.attached_to, "event_manager")

    def copy(self, other):
        ev = EventManager(self.always_event_group)
        ev.events = self.events.copy()
        ev.attach(other)



    def handlers_registered(self,event):
        if self.isevent(event) is False:
            return 0 
        return len(self.events[event].events)