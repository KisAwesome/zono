import logging
from colorama import Fore, Style, init

init()

LOG_LEVEL_PRINT = 21
LOG_LEVEL_IMPORTANT_INFO = 31
MAIN_LOGGERS = []

logging.addLevelName(LOG_LEVEL_PRINT, "PRINT")
logging.addLevelName(LOG_LEVEL_IMPORTANT_INFO, "INFO")


class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        "DEBUG": Fore.GREEN,
        "INFO": Fore.MAGENTA,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED,
    }

    MESSAGE_COLORS = {
        "DEBUG": Fore.RESET,
        "INFO": Fore.CYAN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.MAGENTA,
        "CRITICAL": Fore.MAGENTA,
    }

    def format(self, record):
        levelname = record.levelname
        level_color = self.LEVEL_COLORS.get(levelname, "")
        message_color = self.MESSAGE_COLORS.get(levelname, "")
        message = super().format(record)
        if levelname == "PRINT":
            return message

        name = f"{record.name}." if record.name not in ("root", *MAIN_LOGGERS) else ""
        return f"{level_color}[{name}{levelname}] {message_color}{message}{Style.RESET_ALL}"


def log(msg, p="+"):
    print(f"{Fore.GREEN}[{p}] {Fore.YELLOW}{msg} {Fore.RESET}")


def major_log(msg, p="!"):
    print(f"{Fore.MAGENTA}[{p}] {Fore.BLUE}{msg}{Fore.RESET}")


def error(msg, p="!"):
    print(f"{Fore.RED}[{p}] {Fore.MAGENTA}{msg} {Fore.RESET}")


def info(msg, p="?"):
    print(f"{Fore.MAGENTA}[{p}] {Fore.BLUE}{msg}{Fore.RESET}")


def create_logger(name="", level=logging.ERROR):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.print = lambda *args, **kwargs: logger.log(LOG_LEVEL_PRINT, *args, **kwargs)
    logger.important_log = lambda *args, **kwargs: logger.log(
        LOG_LEVEL_IMPORTANT_INFO, *args, **kwargs
    )

    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(0)
    formatter = ColoredFormatter("%(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger
