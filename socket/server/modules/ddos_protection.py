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


class DDOSProtection:
    def __new__(
        cls,
        max_packets_per_minute=60,
        max_connections=4,
        block_time=1800,
        max_failed_connect_inits=6,
        connection_sent_weight=10,
    ):
        cls = super().__new__(cls)
        cls.max_packets_per_minute = max_packets_per_minute
        cls.max_connections = max_connections
        cls.block_time = block_time
        cls.max_failed_connect_inits = max_failed_connect_inits
        cls.connection_sent_weight = connection_sent_weight

        return dict(
            events=dict(
                connect_check=cls.connect_check,
                on_start=cls.on_start,
                before_packet=cls.before_packet,
                on_disconnect=cls.on_disconnect,
                on_connect_fail=cls.on_connect_fail,
                on_connect=cls.on_connect,
                create_session=cls.create_session,
            ),
            paths=dict(),
            middleware=list(),
            setup=cls.setup,
        )

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

    def push_session(self, addr, key, value):
        session = self.get_session(addr)
        session[key].append(value)
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

    def before_packet(self, ctx):
        if self.get_session_value(ctx.addr, "blocked"):
            return False
        self.increment_session(ctx.addr, "sent")
        if self.get_session_value(ctx.addr, "sent") >= self.max_packets_per_minute:
            self.block(ctx)
            return False

        return True

    def create_session(self, ctx):
        return dict(
            sent=0,
            blocked=False,
            addresses=[
                ctx.addr,
            ],
            failed_connections=0,
        )

    def on_connect(self, ctx):
        print(ctx)
        self.push_session(ctx.addr, "addresses", ctx.addr)

    def reset_sent(self):
        curr_time = time.time()
        for addr, session in self.get_all_sessions()[0].items():
            if session["blocked"]:
                if session["unblock_time"] <= curr_time:
                    session["blocked"] = False
            session["sent"] = 0
            self.save_session((addr, None), session)

    def on_start(self, ctx):
        ctx.app.intervals.append(zono.workers.set_interval(60, self.reset_sent))

    def setup(self, ctx):
        self.server = ctx.app

    def on_connect_fail(self, ctx):
        self.increment_session(ctx.addr, "failed_connections")
        if (
            self.get_session_value(ctx.addr, "failed_connections")
            >= self.max_failed_connect_inits
        ):
            self.update_session(ctx.addr, "failed_connections", 0)
            self.block(ctx)
