from .exceptions import CommandError, CommandAlreadyRegistered
import sys
import traceback
from zono.store import Store
from zono.events import Event, attach, EventGroup


class Arguments(list):
    def inlist(self, index):
        if isinstance(index, slice):
            start, stop, step = index.indices(len(self))
            return stop > start
        elif isinstance(index, int):
            return index < len(self)
        return False

    def __getitem__(self, index):
        if not self.inlist(index):
            return None
        return super().__getitem__(index)

    def __setitem__(self, index, x):
        if not self.inlist(index):
            return None
        super().__setitem__(index, x)

    def __delitem__(self, index):
        if not self.inlist(index):
            return
        super().__delitem__(index)


def command(name=None, description="", help=""):
    help = help or description

    def wrapper(func):
        if not callable(func):
            raise ValueError("Command function must be callable")
        cmd_name = name or func.__name__
        return Command(cmd_name, func, description, help_=help)

    return wrapper


def event(event_name=None):
    def wrapper(func):
        name = event_name
        if event_name is None:
            name = func.__name__

        if not callable(func):
            raise ValueError("Event must be callable")

        return Event(func, name)

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


class Context:
    def __init__(self, args, app, **kwargs):
        self.args = Arguments(args)
        self.argnum = len(self.args)
        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])
        if app:
            self.store = app.store
        comp = kwargs.get("completer", None)
        if comp:
            self.MatchCompleter = MatchCompleter
            self.NoMatchCompleter = NoMatchCompleter

    def __repr__(self) -> str:
        string = ""
        for p, value in vars(self).items():
            string += f"{p} : {value}\n"

        return string


class CommandEvent:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args, **kwds):
        if not hasattr(self, "instance"):
            self.instance = getattr(self.callback, "instance", None)
        if self.instance:
            return self.callback(self.instance, *args, **kwds)
        else:
            return self.callback(*args, **kwds)


class Command:
    def __init__(
        self,
        name,
        callback,
        description="",
        threadable=True,
        hidden=False,
        help_="",
        aliases=[],
    ):
        self.description = description
        self.name = name
        self.callback = callback
        self.completer_func = None
        self.error_handler = None
        self.threadable = threadable
        self.hidden = hidden
        self.help = help_
        self.disabled = False
        self.aliases = aliases

    def __call__(self, ctx):
        if not hasattr(self, "instance"):
            self.instance = getattr(self.callback, "instance", None)
        try:
            if self.instance:
                self.callback(self.instance, ctx)
            else:
                self.callback(ctx)
        except BaseException as e:
            if isinstance(e, SystemExit):
                sys.exit()
            info = sys.exc_info()
            err = CommandError(ctx, e, info)
            if callable(self.error_handler):
                self.error_handler(err)
                return
            return err

    def completer(self, cb):
        if not callable(cb):
            raise ValueError("Completer function must be callable")

        func = CommandEvent(cb)
        self.completer_func = func
        return func

    def error(self, cb):
        if not callable(cb):
            raise ValueError("Error handler function must be callable")

        func = CommandEvent(cb)
        self.error_handler = func
        return func


class Module:
    def __init__(self, name, description=""):
        attach(self, True)
        self.name = name
        self.description = description
        self.commands = []

    def add_command_(self, command):
        if not isinstance(command, Command):
            raise ValueError("Command must be an instance of command")

        self.command_check(command.name)
        self.commands.append(command)

    def command_check(self, name):
        for command in self.commands:
            if command.name == name:
                raise CommandAlreadyRegistered(
                    f"{name} is already registered as a command"
                )

    def command(self, name=None, description="", aliases=[], help=""):
        def wrapper(func):
            if not callable(func):
                raise ValueError("Command function must be callable")

            cmd_name = name or func.__name__
            cmd = Command(cmd_name, func, description, help_=help, aliases=aliases)
            self.add_command_(cmd)
            return cmd

        return wrapper

    def add_submodule(self, module):
        if not isinstance(module, __class__):
            raise ValueError("Module must be an instance Module class")

        self.commands.append(module)

    def on_command_error(self, ctx, error):
        if isinstance(error, KeyboardInterrupt):
            return
        traceback.print_exception(ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(f"\nthis error occurred in {ctx.command.name}")
        sys.exit()
