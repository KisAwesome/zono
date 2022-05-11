import os
from .types import Command, Context,command 
from .module import Module



class BaseCommands(Module):
    def __init__(self):
        pass

    @command(description='Shows this help message',help='When no arguments shows all commands and modules at current path when command is specified command specific help is shown ')
    def help(self, ctx):
        if all(ctx.args) and ctx.args:
            cmd = ctx.app.get_command(ctx.args[0])
            if cmd:
                if cmd.help:
                    print(f'help for {cmd.name}:')
                    print(cmd.help)
                else:
                    print(f'Help for {cmd.name} does not exist')

            else:
                print('Command does not exist')

            return

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

    @command('..','Goes back once','Goes back once in the indentaion tree')
    def back(self, ctx):
        if ctx.app.lock_cli:
            return
        if ctx.app.indentation == []:
            return
        ctx.app.indentation.pop()

    @command('clear','Clears the console','Clears the console')
    def clear(self, ctx):
        if ctx.app.windows:
            return os.system('cls')
        os.system('clear')

    @command('exit','Exits the application','Exits the application')
    def exit(self, ctx):
        if ctx.app.kill_on_exit:
            return ctx.app.kill_app()
        ctx.app.exit_app()

    @command('$','Runs a shell command','Runs a shell command')
    def shell_command(self, ctx):
        os.system(' '.join(ctx.args))

    def _runner_(self, ctx, cmd):
        cmd(ctx)
        print('Finished execution of command in thread')

    @command('thread','Runs a command in thread','Runs the give command in a thread')
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

        @BaseCommands.shell_command.completer
        def shell_completer(self,ctx):
            if not ctx.app.windows:return []
            if not getattr(ctx.app.store, '_shell_commands', None):
                shell_commands = []
                for i in os.getenv('path').split(';'):
                    if not os.path.exists(i):
                        continue
                    for j in os.listdir(i):
                        _type = os.path.splitext(f'{i}\\{j}')[1].lower()
                        if not _type == '.exe' or _type == '.bat':
                            continue
                        shell_commands.append(j)

                ctx.app.store._shell_commands = shell_commands
            return ctx.app.store._shell_commands

        @BaseCommands.run_in_thread.completer
        def thread_completer(self,ctx):
            cmds = ctx.app.indentation[-1].commands[:]
            cmds.extend(ctx.app.base_commands)
            return list(map(lambda x: x.name, cmds))
