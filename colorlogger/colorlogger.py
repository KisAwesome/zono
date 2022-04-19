from colorama import Fore, init


def init_color():
    init()


def log(msg):
    print(f'{Fore.GREEN}[+] {Fore.YELLOW}{msg} {Fore.RESET}')


def major_log(msg):
    print(f'{Fore.MAGENTA}[!] {Fore.BLUE}{msg}{Fore.RESET}')


def error(msg):
    print(f'{Fore.RED}[!] {Fore.MAGENTA}{msg} {Fore.RESET}')


def info(msg):
    print(f'{Fore.MAGENTA}[?] {Fore.BLUE}{msg}{Fore.RESET}')
