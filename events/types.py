import sys
import threading


class EventGroupReturn(list):
    pass


class EventError(Exception):
    def __init__(self, error, exc_info, event, *args, **kwargs):
        self.error = error
        self.exc_info = exc_info
        self.event = event
        super().__init__(*args, **kwargs)


def event(event_name=None):
    def wrapper(func):
        name = event_name
        if event_name is None:
            name = func.__name__

        if not callable(func):
            raise ValueError("Event must be callable")

        return Event(func, name)

    return wrapper


class Event:
    exception = EventError

    def __init__(self, callback, name):
        self.name = name
        self.callback = callback
        self.error_handler = None
        self.event = threading.Event()
        self.event.clear()
        if hasattr(callback, "instance"):
            self.instance = callback.instance

    def __call__(self, *args, **kwds):
        try:
            if hasattr(self, "instance"):
                return self.callback(self.instance, *args, **kwds)
            return self.callback(*args, **kwds)

        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            raise __class__.exception(e, info, self)

    def error(self, cb):
        if not callable(cb):
            raise ValueError("Error handler function must be callable")

        func = Event(cb, self.name + "_error")
        self.error_handler = func
        return func


class EventGroup(Event):
    exception = EventError

    def __init__(self, name):
        self.events = []
        self.name = name
        self.callback = self.__call__
        self.event = threading.Event()
        self.event.clear()

    def register_event(self, event):
        ev = event
        if not isinstance(event, Event):
            ev = Event(event, self.name)
        self.events.append(ev)
        return ev

    def event(self):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Event function must be callable")
            return self.register_event(func)

        return wrapper

    def __call__(self, *args, **kwds):
        returns = EventGroupReturn()
        for i in self.events:
            try:
                if hasattr(self, "instance"):
                    returns.append(i(self.instance, *args, **kwds))
                    continue
                returns.append(i(*args, **kwds))

            except BaseException as e:
                info = sys.exc_info()
                raise __class__.exception(e, info, self)
        return returns
