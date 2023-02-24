from .types import EventGroup, Event, EventError
import traceback
import inspect
import sys


class EventManeger:
    def __init__(self, always_event_group=True):
        self.events = {}
        self.base_events = {}
        self.kill_on_error = False
        self.attached_to = None
        self.always_event_group = always_event_group
        self._debug = False
        self.attrs = [
            "run_baseevent",
            "run_event",
            "events",
            "isevent",
            "event",
            "register_event",
            "set_event",
            "base_events",
            "register_base_event",
            "wait",
        ]
        self.register_base_event("on_event_error", self.on_event_error)

    def isevent(self, event):
        return event in self.events

    def wait(self, event, timeout=None):
        if not self.isevent(event):
            raise ValueError("Event does not exist")

        ev = self.events.get(event)
        # ev.event.clear()
        r = ev.event.wait(timeout=timeout)
        ev.event.clear()
        return r

    def register_base_event(self, event, func):
        if isinstance(func, Event) or isinstance(func, EventGroup):
            ev = func
        else:
            if self.always_event_group:
                ev = EventGroup(event)
                ev.register_event(func)
            else:
                ev = Event(func, event)
        self.base_events[event] = ev
        self.register_event(event, ev)

    def set_event(self, event, func):
        if isinstance(func, Event) or isinstance(func, EventGroup):
            ev = func
        else:
            ev = Event(func, event)

        self.events[event] = ev
        return ev

    def register_event(self, event, func):
        if self.isevent(event):
            if isinstance(self.events[event], EventGroup):
                self.events[event].register_event(func)
        if isinstance(func, Event) or isinstance(func, EventGroup):
            ev = func
        else:
            if self.always_event_group:
                ev = EventGroup(event)
                ev.register_event(func)
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

    def _run_event(self, event, caller, *args, **kwargs):
        ev = self.events.get(event, False)
        if self._debug:
            print()
            print(event, args, kwargs, caller.filename, caller.lineno)
        if ev:
            ret = ev(*args, **kwargs)
            ev.event.set()
            return ret

    def run_event(self, event, *args, **kwargs):
        caller = inspect.getframeinfo(inspect.stack()[1][0])
        try:
            return self._run_event(event, caller, *args, **kwargs)
        except EventError as e:
            self._run_event("on_event_error", caller, e.error, event, sys.exc_info())

    def _run_baseevent(self, event, *args, **kwargs):
        ev = self.base_events.get(event, False)
        if ev:
            ret = ev(*args, **kwargs)
            return ret

    def run_baseevent(self, event, *args, **kwargs):
        try:
            return self._run_baseevent(event, *args, **kwargs)

        except EventError as e:
            self._run_event("on_event_error", e.error, event, sys.exc_info())

    def on_event_error(self, error, event, exc_info):
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(error)
        print(f"\nthis error occurred in {event}")
        if self.kill_on_error:
            sys.exit()

    def attach(self, cls):
        if not self.attached_to is None:
            raise Exception("This event maneger is already attached to a class")
        for name in self.attrs:
            if hasattr(cls, name):
                continue
            attr = getattr(self, name)
            setattr(cls, name, attr)

        self.attached_to = cls

        cls.event_maneger = self

    def deattach(self):
        if self.attached_to is None:
            raise Exception("This event maneger is not attached to a class")
        for name in self.attrs:
            if hasattr(self.attached_to, name):
                delattr(self.attached_to, name)
        if hasattr(self.attached_to, "event_maneger"):
            delattr(self.attached_to, "event_maneger")
