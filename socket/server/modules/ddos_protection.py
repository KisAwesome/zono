"""

{
    events:{

    },
    paths:{

    },
    middleware:[

    ],
    setup:function
}
"""


import time
import zono.workers
from .memorystore import MemorySessionStore


class DDOSProtection:
    def __init__(
        self,
        max_packets_per_minute=60,
        max_connections=4,
        block_time=1800,
        max_failed_connect_inits=6,
        session_store=MemorySessionStore,
    ):
        self.max_packets_per_minute = max_packets_per_minute
        self.max_connections = max_connections
        self.block_time = block_time
        self.max_failed_connect_inits = max_failed_connect_inits
        self.session_store = session_store

    def __new__(
        cls,
        max_packets_per_minute=60,
        max_connections=4,
        block_time=1800,
        max_failed_connect_inits=6,
        session_store=MemorySessionStore,
    ):
        cls = super().__new__(cls)
        cls.__init__(
            max_packets_per_minute,
            max_connections,
            block_time,
            max_failed_connect_inits,
            session_store,
        )

        return cls()

    def get_session(self, addr):
        return self.server.run_event("get_session", addr[0])

    def get_session_value(self, addr, value):
        s = self.get_session(addr)
        if s is None:
            return
        return s[value]

    def save_session(self, addr, session):
        return self.server.run_event("save_session", addr[0], session)

    def update_session(self, addr, key, value):
        session = self.get_session(addr)
        session[key] = value
        self.save_session(addr, session)

    def increment_session(self, addr, key, number=1):
        session = self.get_session(addr)
        session[key] += number
        self.save_session(addr, session)

    def append_session(self, addr, key, value):
        session = self.get_session(addr)
        session[key].append(value)
        self.save_session(addr, session)

    def get_all_sessions(self):
        return self.server.run_event("get_all_sessions")

    def pull_session(self, addr, key, value):
        session = self.get_session(addr)
        session[key].remove(value)
        self.save_session(addr, session)

    def session_exists(self, addr):
        if self.get_session(addr):
            return True
        return False

    def block(self, ctx):
        self.update_session(ctx.addr, "blocked", True)
        self.update_session(ctx.addr, "unblock_time", time.time() + self.block_time)

    def connect_check(self, ctx):
        if self.session_exists(ctx.addr):
            if (
                len(self.get_session_value(ctx.addr, "addresses"))
                >= self.max_connections
            ):
                self.block(ctx)

            return not self.get_session_value(ctx.addr, "blocked")

        return True

    def on_disconnect(self, ctx):
        self.pull_session(ctx.addr, "addresses", ctx.addr)
        ctx.app.run_baseevent("on_disconnect", ctx)

    def before_packet(self, ctx):
        self.increment_session(ctx.addr, "sent")
        if self.get_session_value(ctx.addr, "sent") >= self.max_packets_per_minute:
            self.block(ctx)
            return False

        return True

    def setup_new_session(self, ctx):
        return dict(
            sent=0,
            blocked=False,
            addresses=[
                ctx.addr,
            ],
            failed_connections=0,
        )

    def pre_session_load(self, ctx):
        ctx.session["addresses"].append(ctx.addr)
        return ctx.session

    def reset_sent(self):
        curr_time = time.time()
        for addr, session in self.get_all_sessions().items():
            if session["blocked"]:
                if session["unblock_time"] <= curr_time:
                    session["blocked"] = False
            session["sent"] = 0
            self.save_session((addr, None), session)

    def on_start(self, ctx):
        zono.workers.set_interval(60, self.reset_sent)
        ctx.app.run_baseevent("on_start", ctx)

    def setup(self, ctx):
        ctx.app.load_module(self.session_store(ctx.app))
        self.server = ctx.app

    def on_connect_fail(self, ctx):
        self.increment_session(ctx.addr, "failed_connections")
        if (
            self.get_session_value(ctx.addr, "failed_connections")
            >= self.max_failed_connect_inits
        ):
            self.update_session(ctx.addr, "failed_connections", 0)
            self.block(ctx)

        ctx.app.run_baseevent("on_connect_fail", ctx)

    def __call__(self):
        return dict(
            events=dict(
                connect_check=self.connect_check,
                on_start=self.on_start,
                before_packet=self.before_packet,
                on_disconnect=self.on_disconnect,
                on_connect_fail=self.on_connect_fail,
                pre_session_load=self.pre_session_load,
                setup_new_session=self.setup_new_session,
                on_session_close=lambda ctx: None,
            ),
            paths=dict(),
            middleware=list(),
            setup=self.setup,
        )
