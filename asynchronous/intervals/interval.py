import asyncio
import uuid

_intervals = {}
_intervals_lock = asyncio.Lock()


class Interval:
    def __init__(self, tick, handler, daemon=None, *args, **kwargs):
        self.tick = tick
        self.handler = lambda: handler(*args, **kwargs)
        self.daemon = daemon
        self._task = None
        self.running = False
        self.interval_id = str(uuid.uuid4())
        self._loop = asyncio.get_running_loop()

    async def __next_tick(self):
        try:
            await asyncio.sleep(self.tick)
            if self.running:
                await self.handler()
                await self.__next_tick()
        except asyncio.CancelledError:
            pass

    async def start(self):
        async with _intervals_lock:
            _intervals[self.interval_id] = self
        if self.running:
            raise RuntimeError("Interval is already running")
        self.running = True
        self._task = self._loop.create_task(self.__next_tick())

    async def cancel(self):
        if self._task:
            self._task.cancel()
            await self._task

        self.running = False

    async def __aenter__(self):
        async with _intervals_lock:
            _intervals[self.interval_id] = self
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with _intervals_lock:
            _intervals.pop(self.interval_id, None)


async def set_interval(tick, handler, *args, **kwargs):
    inter = Interval(tick, handler, *args, **kwargs)
    await inter.start()
    return inter.interval_id


async def cancel_interval(id):
    async with _intervals_lock:
        inter = _intervals.pop(id, None)
        if inter is None:
            raise RuntimeError("Interval id does not exist")
        await inter.cancel()


async def get_interval(id):
    async with _intervals_lock:
        return _intervals.get(id, None)


async def get_intervals():
    async with _intervals_lock:
        return _intervals.copy()
