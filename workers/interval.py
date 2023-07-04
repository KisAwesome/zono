import threading
import uuid


_intervals = {}
_intervals_lock = threading.RLock()


class Interval(object):
    def __init__(self, tick, handler, *args, **kwargs):
        self.tick = tick
        self.handler = lambda: handler(*args, **kwargs)
        self._timer = None
        self.running = False
        self.interval_id = str(uuid.uuid4())
        with _intervals_lock:
            _intervals[self.interval_id] = self

    def __next_tick(self):
        self._timer = threading.Timer(self.tick, self.__on_tick)
        self._timer.start()

    def __on_tick(self):
        if not self.running:
            return
        
        self.handler()
        self.__next_tick()

    def start(self):
        if self.running:
            raise RuntimeError("Interval is already running")
        self.running = True
        self.__next_tick()

    def cancel(self):
        if not self._timer is None:
            self._timer.cancel()
            self._timer = None
        self.running = False


def set_interval(tick, handler, *args, **kwargs):
    inter = Interval(tick, handler, *args, **kwargs)
    inter.start()
    return inter.interval_id


def cancel_interval(id):
    with _intervals_lock:
        inter = _intervals.pop(id, None)
        if inter is None:
            raise RuntimeError("Interval id does not exist")

        inter.cancel()


def get_interval(id):
    with _intervals_lock:
        return _intervals.get(id, None)


def get_intervals():
    with _intervals_lock:
        return _intervals.copy()
