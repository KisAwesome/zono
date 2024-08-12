import sys
import asyncio


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

        ev = Event(name)
        ev.events.add(func)
        return ev

    return wrapper


def wrap_coro(func):
    async def wrapper(*args,**kwds):
        return func(*args,**kwds)
    if hasattr(func, 'instance'):
        wrapper.instance = func.instance
    return wrapper

class Event:
    def __init__(self, name):
        self.events = set()
        self.name = name
        self.callback = self.__call__
        self.event = asyncio.Event()
        self.event.clear()
        self.error_handler = None

    async def __call__(self, *args, **kwds):
        tasks = []
        events = []
        for i in self.events:
            if asyncio.iscoroutinefunction(i):
                events.append(i)
            else:
                events.append(wrap_coro(i))
        self.events = events
        try:
            async with asyncio.TaskGroup() as tg:
                for x in self.events:
                    if hasattr(x, "instance"):
                        cr = x(x.instance, *args, **kwds)
                    else:
                        cr = x(*args, **kwds)
                    task = tg.create_task(cr)
                    tasks.append(task)
        
        except BaseException as e:
            if callable(self.error_handler):
                await self.error_handler(e.exceptions[0], e.__traceback__, self.name)
                return
            return EventError(e.exceptions[0], e.__traceback__, self.name)
        if len(tasks) ==1 :
            return tasks[0].result()
        return EventGroupReturn([task.result() for task in tasks])
  


    def error(self, cb):
        if not callable(cb):
            raise ValueError("Error handler function must be callable")
        
        self.error_handler = cb
        if asyncio.iscoroutinefunction(self.error_handler) is False:
            self.error_handler = wrap_coro(cb)
        return cb
