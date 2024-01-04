import os
from .types import Context, command
from .module import Module


errors = {
    ValueError: "Expected a numerical value",
    IndexError: "Missing expected arguments",
}


class BaseCommands(Module):
    def __init__(self):
        pass

    @command(
        "^",
        "Runs a command a specified number of times",
        "Runs a command a specified number of times",
    )
    def run_multiple(self, ctx):
        t = int(ctx.args.pop(0))
        cmd = " ".join(ctx.args)
        for i in range(t):
            ctx.app.run_event("on_input", cmd)

    @run_multiple.error
    def handler(self, error):
        for err, msg in errors.items():
            if isinstance(error.error, err):
                return print(msg)

        raise error.error

    @command(
        "help",
        description="Shows this help message",
        help="When no arguments shows all commands and modules at current path when command is specified command specific help is shown ",
    )
    def help(self, ctx):
        if all(ctx.args) and ctx.args:
            cmd = ctx.app.get_command(ctx.args[0], alias=True)
            if cmd:
                if cmd.help:
                    print(f"help for {cmd.name}:")
                    print(cmd.help)
                else:
                    print(f"Help for {cmd.name} does not exist")

            else:
                print("Command does not exist")

            return

        if ctx.app.indentation == []:
            return ctx.app.main_menu()

        ctx.app.internal_menu()

    @command(
        "..", "Goes back once in the menu", "Goes back once in the indentation tree"
    )
    def back(self, ctx):
        if ctx.app.lock_cli:
            return
        if ctx.app.indentation == []:
            return
        ctx.app.indentation.pop()
        ctx.app.run_event("indentation_changed", Context([], ctx.app))

    @command("clear", "Clears the console", "Clears the console")
    def clear(self, ctx):
        if ctx.app.windows:
            return os.system("cls")
        # os.system("clear")
        print("\033c", end="")

    @command("exit", "Exits the application", "Exits the application")
    def exit(self, ctx):
        ctx.app.exit_app()

    @command("$", "Runs a shell command", "Runs a shell command")
    def shell_command(self, ctx):
        os.system(" ".join(ctx.args))

    def _runner_(self, ctx, cmd):
        cmd(ctx)
        print("Finished execution of command in thread")

    @command("thread", "Runs a command in thread", "Runs the given command in a thread")
    def run_in_thread(self, ctx):
        import threading

        cmd = ctx.app.get_command(ctx.args[0])
        if isinstance(cmd, Module):
            return print("Cannot run a module")

        if cmd is None:
            return print("command not found.")

        _args = ctx.args[:]
        _args.pop(0)

        threading.Thread(
            target=self._runner_,
            args=(
                Context(_args, ctx.app),
                cmd,
            ),
        ).start()

    @help.completer
    def help_completer(self, ctx):
        if ctx.argnum != 0 and ctx.argnum != 1:
            return []
        cmds = ctx.app.base_commands[:]
        if ctx.app.indentation != []:
            cmds.extend(ctx.app.indentation[-1].commands[:])
        return [cmd.name for cmd in cmds]

    @run_multiple.completer
    def run_multiple_completer(self, ctx):
        if ctx.argnum == 1:
            return []
        if ctx.argnum == 2:
            cmds = ctx.app.base_commands[:]
            if ctx.app.indentation != []:
                cmds.extend(ctx.app.indentation[-1].commands[:])

            return [cmd.name for cmd in cmds]

        l = ctx.lbuffer[2:]

        cmd = ctx.app.get_command(l[0])
        if cmd is None:
            return
        if cmd.completer_func is None:
            return

        l1 = l[:]
        l1.pop(0)

        try:
            return cmd.completer_func(Context(l1, ctx.app, completer=True, lbuffer=l))
        except Exception as e:
            print(e)
            print(f"This error occurred in the completer function for {cmd.name}")

    @run_in_thread.completer
    def thread_completer(self, ctx):
        if ctx.argnum == 1:
            cmds = ctx.app.base_commands[:]
            if ctx.app.indentation != []:
                cmds.extend(ctx.app.indentation[-1].commands[:])

            g = [cmd.name for cmd in cmds]
            g.remove("thread")
            return g

        l = ctx.lbuffer[1:]
        cmd = ctx.app.get_command(l[0])
        if cmd is None:
            return
        if cmd.completer_func is None:
            return
        l1 = l[:]
        l1.pop(0)

        try:
            return cmd.completer_func(Context(l1, ctx.app, completer=True, lbuffer=l))
        except Exception as e:
            print(e)
            print(f"This error occurred in the completer function for {cmd.name}")

    @shell_command.completer
    def shell_completer(self, ctx):
        if not ctx.app.windows:
            return []
        if not getattr(ctx.app.store, "_shell_commands", None):
            shell_commands = []
            for i in os.getenv("path").split(";"):
                if not os.path.exists(i):
                    continue
                for j in os.listdir(i):
                    _type = os.path.splitext(f"{i}\\{j}")[1].lower()
                    if not _type == ".exe" or _type == ".bat":
                        continue
                    shell_commands.append(j)

            ctx.app.store._shell_commands = shell_commands
        return ctx.app.store._shell_commands
