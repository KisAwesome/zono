from .workertypes import *

class StoppedWorker(list):
    def __repr__(self):
        return f"Stopped worker: {super().__repr__()}"

    def __str__(self):
        return self.__repr__()


AutoThreads = -1
