from .types import (
    Command,
    Store,
    NoMatchCompleter,
    MatchCompleter,
    Context,
    Module,
    Event,
)
from .exceptions import CommandError, ArgumentError
from .basecommands import BaseCommands
import zono.events
import os
import readline
import collections.abc
import sys
import traceback


class Application:
    def __init__(self):
        zono.events.attach(self, False)
        self.modules = []
        self.indentation = []
        self.base_commands = []
        self.spacer = "::"
        self.lock_cli = False
        self.events_loaded = False
        self._input_stop = False
        self.store = Store()
        self._invoking = None
        self.show_menu = True
        if "libedit" in readline.__doc__:
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")

        readline.set_completer(self.complete)
        self.kill_on_exit = False

        self.windows = os.name == "nt"
        self.load_events()
        self.load_base_commands()

    def hide_menu(self):
        self.show_menu = False

    def complete(self, text, state):
        l = []
        raw_l = []

        buffer = readline.get_line_buffer().lstrip().split(" ")

        for i in buffer:
            raw_l.append(i)
            if i != "" or i != " ":
                l.append(i)

        if len(l) == 1:
            if not self.indentation:
                cmds = list(map(lambda x: x.name, self.modules))

            else:
                cmds = list(map(lambda x: x.name, self.indentation[-1].commands))

            cmds.extend(list(map(lambda x: x.name, self.base_commands)))
            results = [x for x in cmds if x.startswith(text)] + [None]
            r = results[state]
            return r

        else:
            cmd = self.get_command(l[0])
            if cmd is None:
                return
            if cmd.completer_func is None:
                return

            l1 = l[:]
            l1.pop(0)

            args = " ".join(l1)

            try:
                completions = cmd.completer_func(
                    Context(args, self, completer=True, lbuffer=buffer)
                )
            except Exception as e:
                print(e)
                print(f"This error occured in the completer function for {cmd.name}")

            if isinstance(completions, collections.abc.Iterable):
                completions = list(completions)
                results = [x for x in completions if x.startswith(text)] + [None]
                r = results[state]
                return r
            elif isinstance(completions, MatchCompleter):
                results = [x for x in completions.list if x.startswith(text)] + [None]
                r = results[state]
                return r
            elif isinstance(completions, NoMatchCompleter):
                return completions.list[state]

            else:
                raise ValueError(
                    "Completion must be list, MatchCompleter or NoMatchCompleter"
                )

    def stop_input(self):
        self._input_stop = True

    def exit_app(self):
        self.stop_input()
        if self.kill_on_exit:
            self.kill_app()

    def lock_indent(self):
        self.lock_cli = True

    def unlock_indent(self):
        self.lock_cli = False

    def kill_app(self, status=0):
        print()
        os._exit(status)

    def get_command(self, command):
        if not self.indentation:
            for i in self.base_commands:
                if i.name == command:
                    return i

        else:
            cmds = self.indentation[-1].commands[:]
            cmds.extend(self.base_commands)
            for i in cmds:
                if isinstance(i, Module):
                    continue
                if i.name == command:
                    return i

    def add_module(self, module):
        if not isinstance(module, Module):
            raise ValueError("Module must be an instance Module class")

        module.run_event("on_load", Context("", self))
        module.application = self
        self.modules.append(module)

    def input_event(self, inp):
        inp = inp.lstrip()
        for base in self.base_commands:
            if base.disabled:
                continue
            if base.name == inp.split(" ")[0]:
                try:
                    self._invoking = base
                    base(
                        Context(
                            inp.replace(base.name, "", 1).strip(), self, command=base
                        )
                    )

                    self._invoking = None

                except CommandError as e:
                    self._invoking = None
                    if base.error_handler:
                        return base.error_handler(e.ctx, e.error)
                    if self.isevent("on_command_error"):
                        return self.run_event("on_command_error", e.ctx, e.error)

                    raise e
                return

        if self.indentation != []:
            indentation = self.indentation[-1].commands

        else:
            indentation = self.modules
        for command in indentation:
            if command.name == inp.split(" ")[0]:
                if isinstance(command, Command):
                    if command.disabled:
                        continue

                    try:
                        self._invoking = command
                        command(
                            Context(
                                inp.replace(command.name, "", 1).strip(),
                                self,
                                command=command,
                            )
                        )

                        self._invoking = None

                    except CommandError as e:
                        self._invoking = None
                        if command.error_handler:
                            return command.error_handler(e.ctx, e.error)
                        if self.on_command_error:
                            return self.run_event("on_command_error", e.ctx, e.error)
                        raise e

                    return

                else:
                    if self.lock_cli:
                        return
                    self.indentation.append(command)
                    command.run_event(
                        "on_enter", Context("", self, hide_menu=self.hide_menu)
                    )
                    self.run_event("indentation_changed", Context("", self))
                    return

        self.run_event(
            "command_not_found", Context("", self, command=inp.split(" ")[0])
        )

    def yesno(self, msg):
        opts = ("y", "n", "yes", "no")
        while True:
            inp = input(msg)
            if inp in opts:
                if inp.lower() == "y" or inp.lower == "yes":
                    return True
                return False
            print("input must be yes/no or y/n")

    def get_indentation(self):
        if not self.indentation:
            return ""

        indentation = list(map(lambda x: x.name, self.indentation))
        return " ".join(indentation)

    def quit_event(self):
        self.exit_app()

    def eof_event(self):
        print()
        self.exit_app()

    def on_event_error(self, error, event, exc_info):
        traceback.print_exception(exc_info[0], exc_info[1], exc_info[2])
        print(f"\nthis error occurred in {event}")
        sys.exit()

    def on_command_error(self, ctx, error):
        if isinstance(error, KeyboardInterrupt):
            return
        traceback.print_exception(ctx.exc_info[0], ctx.exc_info[1], ctx.exc_info[2])
        print(f"\nthis error occurred in {ctx.command.name}")
        sys.exit()

    def input_loop(self):
        self.run_event("on_ready")
        while True:
            if self._input_stop:
                return
            try:
                INP = input(f"{self.get_indentation()}>")
                self.run_event("on_input", INP)

            except KeyboardInterrupt:
                self.run_event("keyboard_interrupt")
                continue
            except EOFError:
                self.run_event("eof")
                continue

    def kbd_interupt_event(self):
        self.run_event("on_quit")

    def deafault_indentation(self, *ind, lock=False):
        if not ind:
            raise ValueError("No indentations provided")
        for i in ind:
            if not isinstance(i, Module):
                raise ValueError("Indentation list must contain only modules")
        self.lock_cli = lock
        if not ind[0] in self.modules:
            self.add_module(ind[0])
        self.indentation = list(ind)

    def main_menu(self):
        if self.indentation:
            return self.run_event("indentation_changed", Context("", self))
        message = ""

        base_names = list(map(lambda x: x.name, self.base_commands))
        _spacer1 = max(len(s) for s in base_names)
        mod_names = list(map(lambda x: x.name, self.modules))
        if mod_names:
            _spacer = max(len(s) for s in mod_names)
            if _spacer > _spacer1:
                _spacer1 = _spacer
            else:
                _spacer = _spacer1
            spacer = " " * _spacer

        spacer1 = " " * _spacer1

        for module in self.modules:
            _s = _spacer - len(module.name)
            if _s == 0:

                s = ""
            s = " " * _s
            if module.description:
                message += (
                    f"\n|-- {module.name}{s}{spacer}{self.spacer}  {module.description}"
                )
            else:
                message += f"\n|-- {module.name}"

        m2 = ""
        for sub in self.base_commands:
            if sub.hidden or sub.disabled:
                continue
            _s = _spacer1 - len(sub.name)
            if _s == 0:
                s = ""

            s = " " * _s
            if sub.description:
                m2 += f"\n|-- {sub.name}{s}{spacer1}{self.spacer}  {sub.description}"

            else:
                m2 += f"\n|-- {sub.name}"

        print("Base commands", end="")
        print(m2)
        print("\n")
        print("Modules", end="")
        print(message)
        print()

    def internal_menu(self):
        message = ""

        base_names = list(map(lambda x: x.name, self.base_commands))
        _spacer1 = max(len(s) for s in base_names)

        mod_names = list(map(lambda x: x.name, self.indentation[-1].commands))
        if mod_names:
            _spacer = max(len(s) for s in mod_names)
            if _spacer > _spacer1:
                _spacer1 = _spacer
            else:
                _spacer = _spacer1
            spacer = " " * _spacer

        spacer1 = " " * _spacer1
        for module in self.indentation[-1].commands:
            if isinstance(module, Command):
                if module.hidden or module.disabled:
                    continue
            _s = _spacer - len(module.name)
            if _s == 0:
                s = ""

            s = " " * _s

            if module.description:
                message += f"\n|-- {module.name}{s}{spacer}{ self.spacer}  {module.description}"

            else:
                message += f"\n|-- {module.name}"

        m2 = ""
        for sub in self.base_commands:
            if sub.hidden or sub.disabled:
                continue
            _s = _spacer1 - len(sub.name)
            if _s == 0:
                s = ""

            s = " " * _s
            m2 += f"\n|-- {sub.name}{s}{spacer1}{ self.spacer}  {sub.description}"

        print("Base commands", end="")
        print(m2)
        print("\n")
        print("Commands", end="")
        print(message)
        print()

    def command_not_found(self, ctx):
        print("The command you entered does not exist.")

    def indentation_changed(self, ctx):
        if self.show_menu:
            return self.internal_menu()
        self.show_menu = True

    def module(self, name, description=""):
        module = Module(name, description=description)
        self.add_module(module)
        return module

    def load_events(self):
        self.register_base_event("on_ready", lambda: None)
        self.register_base_event("on_input", self.input_event)
        self.register_base_event("on_quit", self.quit_event)
        self.register_base_event("eof", self.eof_event)
        self.register_base_event("command_not_found", self.command_not_found)
        self.register_base_event("indentation_changed", self.indentation_changed)
        self.register_base_event("on_command_error", self.on_command_error)
        self.register_base_event("on_event_error", self.on_event_error)
        self.register_base_event("kill_app", self.kill_app)
        self.register_base_event("ctrl_c_event", self.ctrl_c_event)
        self.register_base_event("keyboard_interrupt", self.kbd_interupt_event)

    def ctrl_c_event(self):
        if self._invoking:
            if self._invoking.error_handler:
                return self._invoking.error_handler(
                    Context("", self), KeyboardInterrupt()
                )

        self.run_event("kill_app")

    def load_base_commands(self):
        self.basecmd = BaseCommands()
        self.basecmd.application = self
        self.base_commands = self.basecmd.commands

    def run(self):
        self.main_menu()
        self.input_loop()
