import multiprocessing
import threading


class Process:
    def __init__(self, target, daemon, args):

        self.thread = multiprocessing.Process(
            target=target, daemon=daemon, args=args)

    def start(self):
        return self.thread.start()

    def join(self):
        return self.thread.join()

    def terminate(self):
        self.thread.terminate()

    def kill(self):
        self.thread.kill()

    def close(self):
        self.thread.close()


class Thread:
    def __init__(self, target, daemon, args):
        self.thread = threading.Thread(
            target=target, daemon=daemon, args=args)

    def start(self):
        return self.thread.start()

    def join(self):
        return self.thread.join()

    def terminate(self):
        raise TypeError('Thread cannot be terminated')

    def kill(self):
        raise TypeError('Thread cannot be killed')

    def close(self):
        raise TypeError('Thread cannot be closed')
