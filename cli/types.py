from .exceptions import CommandError, CommandAlreadyRegistered
import sys
import traceback


def command(name=None, description=''):
    def wrapper(func):
        if not callable(func):
            raise ValueError('Command function must be callable')
        cmd_name = name or func.__name__
        return Command(cmd_name, func, description)

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


class Store:
    def __init__(self, ref={}):
        for i in ref:
            if isinstance(ref[i], dict):
                ref[i] = Store(ref[i])
            setattr(self, i, ref[i])

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = Store(value)
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key, None)


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
        self.instance = getattr(callback, 'instance', None)
        

    def __call__(self, *args, **kwds):
        self.instance = getattr(self.callback, 'instance', None)
        if self.instance:
            self.callback(self.instance,*args,**kwds)
        else:
            self.callback(*args,**kwds)

class CommandEvent:
    def __init__(self,callback):
        self.callback = callback
        self.instance = getattr(callback, 'instance', None)

    def __call__(self, *args, **kwds):
        self.instance = getattr(self.callback, 'instance', None)
        if self.instance:
            self.callback(self.instance,*args,**kwds)
        else:
            self.callback(*args,**kwds)

class Command:
    def __init__(self, name, callback, description='', threadable=True, hidden=False):
        self.description = description
        self.name = name
        self.callback = callback
        self.completer_func = None
        self.error_handler = None
        self.threadable = threadable
        self.hidden = hidden
        self.instance = getattr(callback, 'instance', None)

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

    def command(self, name=None, description='', aliases=[]):
        def wrapper(func):
            if not callable(func):
                raise ValueError('Command function must be callable')

            cmd_name = name or func.__name__
            if aliases:
                for alias in aliases:
                    cmd = Command(alias, func, description)
                    self.add_command_(cmd)

            cmd = Command(cmd_name, func, description)
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

