from colorama import Fore, init


def init_color():
    init()


def log(msg,p='+'):
    print(f'{Fore.GREEN}[{p}] {Fore.YELLOW}{msg} {Fore.RESET}')


def major_log(msg,p='!'):
    print(f'{Fore.MAGENTA}[{p}] {Fore.BLUE}{msg}{Fore.RESET}')


def error(msg,p='!'):
    print(f'{Fore.RED}[{p}] {Fore.MAGENTA}{msg} {Fore.RESET}')


def info(msg,p='?'):
    print(f'{Fore.MAGENTA}[{p}] {Fore.BLUE}{msg}{Fore.RESET}')


if __name__ == '__main__':
    import zono.colorlogger as cl

    cl.log('Test log')
    cl.info('Test info')
    cl.major_log('Major info') #gets attention in the console
    cl.error('Test error')