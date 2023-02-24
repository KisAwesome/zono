import os
from .types import Command, Context, command
from .module import Module


class BaseCommands(Module):
    def __init__(self):
        pass

    @command(
        "help",
        description="Shows this help message",
        help="When no arguments shows all commands and modules at current path when command is specified command specific help is shown ",
    )
    def help(self, ctx):
        if all(ctx.args) and ctx.args:
            cmd = ctx.app.get_command(ctx.args[0])
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

    @command("..", "Goes back once", "Goes back once in the indentaion tree")
    def back(self, ctx):
        if ctx.app.lock_cli:
            return
        if ctx.app.indentation == []:
            return
        ctx.app.indentation.pop()

    @command("clear", "Clears the console", "Clears the console")
    def clear(self, ctx):
        if ctx.app.windows:
            return os.system("cls")
        os.system("clear")

    @command("exit", "Exits the application", "Exits the application")
    def exit(self, ctx):
        if ctx.app.kill_on_exit:
            return ctx.app.kill_app()
        ctx.app.exit_app()

    @command("$", "Runs a shell command", "Runs a shell command")
    def shell_command(self, ctx):
        os.system(" ".join(ctx.args))

    def _runner_(self, ctx, cmd):
        cmd(ctx)
        print("Finished execution of command in thread")

    @command("thread", "Runs a command in thread", "Runs the give command in a thread")
    def run_in_thread(self, ctx):
        import threading

        cmd = ctx.app.get_command(ctx.args[0])
        if isinstance(cmd, Module):
            return print("Cannot run a module")

        if cmd is None:
            return print("command not found.")

        _args = ctx.args[:]
        _args.pop(0)
        args = " ".join(_args)

        threading.Thread(
            target=self._runner_,
            args=(
                self,
                Context(args, ctx.app),
                cmd,
            ),
        ).start()

    @help.completer
    def help_completer(self, ctx):
        if ctx.argnum != 0 and ctx.argnum != 1:
            return []
        cmds = ctx.app.indentation[-1].commands[:]
        cmds.extend(ctx.app.base_commands)
        return list(map(lambda x: x.name, cmds))

    @run_in_thread.completer
    def thread_completer(self, ctx):
        f = self.help_completer(ctx)
        f.remove("thread")
        return f

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
