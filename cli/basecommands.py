import os
from .types import Command, Context


class BaseCommands:
    def __init__(self):
        pass

    def help(self, ctx):
        if ctx.app.indentation == []:
            return ctx.app.main_menu()

        message = ''

        base_names = list(map(lambda x: x.name, ctx.app.base_commands))
        _spacer1 = max(len(s) for s in base_names)
        mod_names = list(
            map(lambda x: x.name, ctx.app.indentation[-1].commands))
        if mod_names:
            _spacer = max(len(s) for s in mod_names)
            if _spacer > _spacer1:
                _spacer1 = _spacer
            else:
                _spacer = _spacer1
            spacer = ' ' * _spacer

        spacer1 = ' ' * _spacer1
        for module in ctx.app.indentation[-1].commands:
            _s = _spacer-len(module.name)
            if _s == 0:
                s = ''

            s = ' '*_s

            if module.description:
                message += f'\n|-- {module.name}{s}{spacer}{ ctx.app.spacer}  {module.description}'

            else:
                message += f'\n|-- {module.name}'

        m2 = ''
        for sub in ctx.app.base_commands:
            _s = _spacer1-len(sub.name)
            if _s == 0:
                s = ''

            s = ' '*_s
            m2 += f'\n|-- {sub.name}{s}{spacer1}{ ctx.app.spacer}  {sub.description}'

        print('Base commands', end='')
        print(m2)
        print('\n')
        print('Commands', end='')
        print(message)
        print()

    def back(self, ctx):
        if ctx.app.lock_cli:
            return
        if ctx.app.indentation == []:
            return
        ctx.app.indentation.pop()

    def clear(self, ctx):
        if ctx.app.windows:
            return os.system('cls')
        os.system('clear')

    def exit(self, ctx):
        if ctx.app.kill_on_exit:
            return ctx.app.kill_app()
        ctx.app.exit_app()

    def shell_command(self, ctx):
        os.system(' '.join(ctx.args))

    def _runner_(self, ctx, cmd):
        cmd(ctx)
        print('Finished execution of command in thread')

    def run_in_thread(self, ctx):
        import threading
        _args = ctx.args

        inp = ' '.join(_args)
        cmd = None

        if ctx.app.indentation != []:
            indentation = ctx.app.indentation[-1].commands

        else:
            indentation = ctx.app.modules
        for command in indentation:
            if command.name == inp.split(' ')[0]:
                if isinstance(command, Command):
                    cmd = (
                        command, (Context(inp.replace(command.name, '').strip(), ctx.app, command=command)))

                else:
                    return print('Cannot run module in thread')

        if cmd is None:
            return ctx.app.run_event('command_not_found', Context(
                '', self, command=_args[0]))

        threading.Thread(target=self._runner_,
                         args=(cmd[1], cmd[0].callback,)).start()
