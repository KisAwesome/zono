import logging
from colorama import Fore, Style, init
import time 
import re



init()

LOG_LEVEL_PRINT = 21
LOG_LEVEL_IMPORTANT_INFO = 31

MAIN_LOGGERS = set('root')

logging.addLevelName(LOG_LEVEL_PRINT, "PRINT")
logging.addLevelName(LOG_LEVEL_IMPORTANT_INFO, "MAJOR_INFO")

class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        "DEBUG": Fore.LIGHTBLACK_EX,
        "INFO": Fore.CYAN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.MAGENTA,
        "CRITICAL": Fore.MAGENTA,
        'MAJOR_INFO':Fore.BLUE,
    }

    MESSAGE_COLORS = {
        "DEBUG": Fore.RESET,
        "INFO": Fore.YELLOW,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED,
        'MAJOR_INFO':Fore.YELLOW
    }
    def __init__(self,thread=False, process=False,timefmt='%c',time=False,main_logger=None,fmt=None, datefmt=None, style='%', validate=True, *,defaults=None):
        self.thread = thread
        self.process = process
        self.timefmt = timefmt
        self.time = time
        self.main_logger = main_logger or ''
        assert not (thread and process) ,'Cannot use both thread and process'
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)
        
        
    def format(self, record):
        levelname = record.levelname
        level_color = self.LEVEL_COLORS.get(levelname, "")
        message_color = self.MESSAGE_COLORS.get(levelname, "")
        message = super().format(record)
        if levelname == "PRINT":
            return message
        thread = record.threadName+':' if self.thread else ''
        process = record.processName+':' if self.process else ''
        name = f"{record.name}." if record.name not in MAIN_LOGGERS else ""
        if name and self.main_logger:
            name = f'{self.main_logger}.{name}' 
        log_time = f'{Fore.GREEN}{time.strftime(self.timefmt)}{Fore.RESET} ' if self.time else ''
        return f"{log_time}{level_color}[{name}{process}{thread}{levelname}] {message_color}{message}{Style.RESET_ALL}"


class NoColorFormat(ColoredFormatter):
    def __init__(self,cls):
        self.cls = cls
    
    def format(self, record):
        message = self.cls.format(record)
        message = re.sub(r'\x1b[^m]*m','', message)
        return message
    

def log(msg, p="+"):
    print(f"{Fore.GREEN}[{p}] {Fore.YELLOW}{msg} {Fore.RESET}")


def major_log(msg, p="!"):
    print(f"{Fore.MAGENTA}[{p}] {Fore.BLUE}{msg}{Fore.RESET}")


def error(msg, p="!"):
    print(f"{Fore.RED}[{p}] {Fore.MAGENTA}{msg} {Fore.RESET}")


def info(msg, p="?"):
    print(f"{Fore.MAGENTA}[{p}] {Fore.BLUE}{msg}{Fore.RESET}")


def create_logger(name="", level=logging.ERROR, main=False,**kwargs):
    if main and name != "":
        MAIN_LOGGERS.add(name)
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
    formatter = ColoredFormatter(**kwargs)
    logger.Formatter = formatter
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def add_file_handler(logger, file_path, level=logging.DEBUG, **kwargs):
    if getattr(logging.getLogger(logger),'Formatter', False) is False:
        raise ValueError("Cannot register file handler without an existing ColorFormatter registered")
    fh = logging.FileHandler(file_path)
    fh.setLevel(level)
    fh.setFormatter(NoColorFormat(logging.getLogger(logger).Formatter))
    logging.getLogger(logger).addHandler(fh)