import zono.zonocrypt
import zono.socket.server
from .module_helper import event, ServerModule
import time


class MemorySessionStore(ServerModule):
    def __init__(self):
        self.crypt = zono.zonocrypt.zonocrypt()
        self.sessions = {}

    def setup(self, ctx):
        self.server = ctx.app

    @event()
    def get_session(self, session):
        return self.sessions.get(session, None)

    @event()
    def save_session(self, session_key, session):
        if session_key not in self.sessions:
            return
        self.sessions[session_key] = session

    @event()
    def get_all_sessions(self):
        return self.sessions.copy()

    @event()
    def new_session(self, ctx, session):
        token = self.crypt.create_safe_identifier(str(time.time()) + str(ctx.addr))
        self.sessions[token] = session
        return token
