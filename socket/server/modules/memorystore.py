import zono.zonocrypt
import zono.socket.server


class MemorySessionStore:
    def __init__(self, *args, **kwargs):
        self.crypt = zono.zonocrypt.zonocrypt()

    def setup(self, ctx):
        ctx.store.sessions = {}
        ctx.app.custom_session_handler = True
        self.server = ctx.app

    def create_session(self, ctx):
        if ctx.addr[0] in ctx.store.sessions:
            ctx.session = ctx.store.sessions[ctx.addr[0]]
            return ctx.app.run_event("pre_session_load", ctx)
        else:
            _s = ctx.app.run_event("setup_new_session", ctx)
            s = dict(session_id=self.crypt.create_safe_identifier(str(ctx.addr)))
            if isinstance(_s, zono.socket.server.EventGroupReturn) or isinstance(
                _s, list
            ):
                for i in _s:
                    s |= i
            elif isinstance(_s, dict):
                s |= _s
            ctx.store.sessions[ctx.addr[0]] = s
            return s

    def __new__(cls, *args, **kwargs):
        cls = super().__new__(cls)
        cls.__init__(*args, **kwargs)
        return cls()

    def pre_session_save(self, ctx):
        return ctx.session

    def pre_session_load(self, ctx):
        return ctx.session

    def on_session_close(self, ctx):
        ctx.session.pop("conn", None)
        ctx.session.pop("key", None)
        ctx.session = ctx.app.run_event("pre_session_save", ctx)
        ctx.store.sessions[ctx.addr[0]] = ctx.session

    def get_session(self, session):
        return self.server.store.sessions.get(session, None)

    def save_session(self, session_key, session):
        if session_key not in self.server.store.sessions:
            return
        self.server.store.sessions[session_key] = session

    def get_all_sessions(self):
        return self.server.store.sessions

    def get_session_id(self, session_id):
        for addr, session in self.server.store.sessions.items():
            if session["session_id"] == session_id:
                session["address"] = addr
                return session

    def __call__(self):
        return dict(
            setup=self.setup,
            paths=dict(),
            middleware=list(),
            events=dict(
                create_session=self.create_session,
                setup_new_session=zono.socket.server.EventGroup("setup_new_session"),
                pre_session_save=self.pre_session_save,
                on_session_close=self.on_session_close,
                get_session=self.get_session,
                save_session=self.save_session,
                get_all_sessions=self.get_all_sessions,
                pre_session_load=self.pre_session_load,
                get_session_id=self.get_session_id,
            ),
        )
