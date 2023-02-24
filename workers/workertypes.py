import multiprocessing
import threading


class Thread(threading.Thread):
    def terminate(self):
        if self._tstate_lock.locked():
            self._tstate_lock.release()
        self._stop()

        if self._ident in threading.enumerate():
            self._delete()


# def wrap_conv(func):
#     return func()
#     # if __name__ == "__main__":


class Process:
    def __init__(self, *args, **kwds):
        raise NotImplementedError
        # self.thread = multiprocessing.Process(*args, **kwds)

    # def start(self):
    #     return wrap_conv(self.thread.start)

    # def join(self):
    #     return wrap_conv(self.thread.join)

    # def terminate(self):
    #     wrap_conv(self.thread.terminate)
