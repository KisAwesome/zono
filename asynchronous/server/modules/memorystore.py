import zono.zonocrypt
import zono.socket.server
from .module_helper import event, ServerModule
import time
import asyncio

class MemorySessionStore(ServerModule):
    def __init__(self):
        self.crypt = zono.zonocrypt.zonocrypt()
        self.sessions = {}

    def setup(self, ctx):
        self.server = ctx.app

    @event()
    async def get_session(self, session):
        return self.sessions.get(session, None)

    @event()
    async def save_session(self, session_key, session):
        if session_key not in self.sessions:
            return
        self.sessions[session_key] = session

    @event()
    async def get_all_sessions(self):
        return self.sessions

    @event()
    async def new_session(self, ctx, session):
        token = await asyncio.to_thread(self.crypt.create_safe_identifier,str(time.time()) + str(ctx.addr))
        self.sessions[token] = session
        return token
