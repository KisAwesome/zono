from os import cpu_count
from .workertypes import *
import tqdm
import zono.events
import traceback
import sys
import warnings
import threading


class AutoThreadsBase:
    pass


class StoppedWorker(list):
    def __repr__(self):
        return f"Stopped worker: {super().__repr__()}"

    def __str__(self):
        return self.__repr__()


AutoThreads = AutoThreadsBase()
