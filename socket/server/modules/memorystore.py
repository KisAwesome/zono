import zono.zonocrypt
import zono.socket.server


class MemorySessionStore:
    def __new__(cls):
        cls = super().__new__(cls)
        cls.crypt = zono.zonocrypt.zonocrypt()
        return dict(
            setup=cls.setup,
            paths=dict(),
            middleware=list(),
            events=dict(
                load_session=cls.load_session,
                get_session=cls.get_session,
                save_session=cls.save_session,
                get_all_sessions=cls.get_all_sessions,
                get_session_id=cls.get_session_id,
                created_session=cls.created_session,
            ),
        )

    def setup(self, ctx):
        ctx.store.sessions = {}
        ctx.app.custom_session_handler = True
        self.server = ctx.app

    def load_session(self, ctx):
        if ctx.addr[0] in ctx.store.sessions:
            return ctx.store.sessions[ctx.addr[0]]

    def created_session(self, ctx):
        s = dict(session_id=self.crypt.create_safe_identifier(str(ctx.addr[0])))
        session = ctx.session.copy()
        session.pop("conn", None)
        s |= session
        ctx.store.sessions[ctx.addr[0]] = s

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
