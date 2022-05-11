from typing import Any
from .exceptions import CommandError, CommandAlreadyRegistered
import sys
import traceback


def command(name=None, description='',help=''):
    def wrapper(func):
        if not callable(func):
            raise ValueError('Command function must be callable')
        cmd_name = name or func.__name__
        return Command(cmd_name, func, description,help_=help)

    return wrapper

def event(event_name=None):
    def wrapper(func):
        name = event_name
        if event_name is None:
            name = func.__name__

        if not callable(func):
            raise ValueError('Event must be callable')

        return Event(func,name)
    return wrapper

class MatchCompleter:
    def __init__(self, l):
        l = list(l)
        self.list = l[:]
        self.list.append(None)


class NoMatchCompleter:
    def __init__(self, l):
        l = list(l)
        self.list = l[:]
        self.list.append(None)




#  import zono.cli;app = zono.cli.Application();store=app.store
class Store(dict):
    dictattrs = ['__class__', '__class_getitem__', '__contains__', '__delattr__', '__delitem__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__ior__', '__iter__', '__le__', '__len__', '__lt__', '__ne__', '__new__', '__or__', '__reduce__', '__reduce_ex__', '__repr__', '__reversed__', '__ror__', '__setattr__', '__setitem__', '__sizeof__', '__str__', '__subclasshook__', 'clear', 'copy', 'fromkeys', 'get', 'items', 'keys', 'pop', 'popitem', 'setdefault', 'update', 'values']
    def __setattr__(self, __name: Any, __value: Any) -> None:
        if __name in Store.dictattrs:
            return super().__setattr__(__name,__value)
        return super().__setitem__(__name, __value)

    def __getattribute__(self, __name: Any) -> Any:
        if __name in Store.dictattrs:
            return super().__getattribute__(__name)
        return super().__getitem__(__name)

    


class Context:
    def __init__(self, args, app, **kwargs):
        _args = args.split(' ')
        args_ = []
        for _arg in _args:
            if _arg == ' ' or _arg == '':
                continue
            args_.append(_arg)

        self.args = args_
        self.argnum = len(self.args)
        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])

        self.store = app.store
        comp = kwargs.get('completer', None)
        if comp:
            self.MatchCompleter = MatchCompleter
            self.NoMatchCompleter = NoMatchCompleter

    def __repr__(self) -> str:
        string = ''
        for p, value in vars(self).items():
            string += f'{p} : {value}\n'

        return string


class Event:
    def __init__(self,callback,name):
        self.name = name
        self.callback = callback
        # self.instance = getattr(callback, 'instance', None)
        

    def __call__(self, *args, **kwds):
        # print(self.instance)
        self.instance = getattr(self.callback, 'instance',None)
        if self.instance:
            return self.callback(self.instance,*args,**kwds)
        else:
            return self.callback(*args,**kwds)

class CommandEvent:
    def __init__(self,callback):
        self.callback = callback
        self.instance = getattr(callback, 'instance', None)

    def __call__(self, *args, **kwds):
        self.instance = getattr(self.callback, 'instance', None)
        if self.instance:
            return self.callback(self.instance,*args,**kwds)
        else:
            return self.callback(*args,**kwds)

class Command:
    def __init__(self, name, callback, description='', threadable=True, hidden=False,help_=''):
        self.description = description
        self.name = name
        self.callback = callback
        self.completer_func = None
        self.error_handler = None
        self.threadable = threadable
        self.hidden = hidden
        self.instance = getattr(callback, 'instance', None)
        self.help = help_

    def __call__(self, ctx):
        try:
            if self.instance:
                self.callback(self.instance, ctx)
            else:
                self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            raise CommandError(
                ctx, e, info)

    def completer(self, cb):
        if not callable(cb):
            raise ValueError('Completer function must be callable')
        
        func = CommandEvent(cb)
        self.completer_func = func
        return func

    def error(self, cb):
        if not callable(cb):
            raise ValueError('Error handler function must be callable')

        func = CommandEvent(cb)
        self.error_handler = func
        return func

class Module:
    def __init__(self, name, description=''):
        self.name = name
        self.description = description
        self.commands = []
        self.events = {}
        self.events_loaded = False
        self.load_events()

    def add_command_(self, command):
        if not isinstance(command, Command):
            raise ValueError('Command must be an instance of command')

        self.command_check(command.name)
        self.commands.append(command)

    def command_check(self, name):
        for command in self.commands:
            if command.name == name:
                raise CommandAlreadyRegistered(
                    f'{name} is already registered as a command')

    def command(self, name=None, description='', aliases=[],help=''):
        def wrapper(func):
            if not callable(func):
                raise ValueError('Command function must be callable')

            cmd_name = name or func.__name__
            if aliases:
                for alias in aliases:
                    cmd = Command(alias, func, description,help_=help)
                    self.add_command_(cmd)

            cmd = Command(cmd_name, func, description,help_=help)
            self.add_command_(cmd)
            return cmd

        return wrapper

    def add_submodule(self, module):
        if not isinstance(module, __class__):
            raise ValueError('Module must be an instance Module class')

        self.commands.append(module)

    def register_event(self,event,func):
        ev = Event(func,event)
        self.events[event] = ev
        return ev


    def event(self,  event_name=None):
        def wrapper(func):
            name = event_name
            if event_name is None:
                name = func.__name__

            if not callable(func):
                raise ValueError('Event must be callable')

            return self.register_event(name,func)
        return wrapper


    def on_event_error(self, error, event, exc_info):
        traceback.print_exception(
            exc_info[0], exc_info[1], exc_info[2])
        print(f'\nthis error occurred in {event}')
        sys.exit()

    def on_command_error(self, ctx, error):
        if isinstance(error, KeyboardInterrupt):
            return
        traceback.print_exception(
            ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(f'\nthis error occurred in {ctx.command.name}')
        sys.exit()

    def _run_event(self, event, *args, **kwargs):
        ev = self.events.get(event, False)
        if ev:
            # print(ev.instance)
            ret = ev(*args, **kwargs)
            return ret
        return

    def run_event(self, event, *args, **kwargs):
        try:
            ret = self._run_event(event, *args, **kwargs)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            self._run_event('on_event_error', e, event, sys.exc_info())
        return ret


    def on_load(self,ctx):
        pass

    def load_events(self):
        if self.events_loaded:
            return 

        self.register_event('on_command_error',self.on_command_error)
        self.register_event('on_event_error',self.on_event_error)
        self.register_event('on_load',self.on_load)
        self.events_loaded = True

