from .module_helper import ServerModule, event
from zono.asynchronous.server.types import Context


class ServerName(ServerModule):
    def __init__(self, name):
        self.name = name

    def setup(self, ctx):
        ctx.app.name = self.name

    @event()
    async def server_info(self, ctx):
        return dict(name=self.name)


class PersistentSessions(ServerModule):
    def __init__(self, cookie_name=None):
        self.cookie_name = cookie_name or "_session"

    def setup(self, ctx):
        self.server = ctx.app
        self.run_event = self.server.run_event
        self.wrap_event = self.server.wrap_event


    async def sanitize_session(self, session):
        for i in (
            "conn",
            "key",
            'sent_cookies',
            self.cookie_name,
            *(
                await self.server.wrap_list_event(
                    "sanitize_session", Context(self.server, session=session)
                )
                or []
            ),
        ):
            session.pop(i, None)
        return session

    def check_cookies(self):
        if not self.server.isevent("create_cookies"):
            raise ValueError("Cookie handler event create_cookies is not available")

    def check_session_store(self):
        for i in ("get_session", "save_session", "new_session"):
            if self.server.isevent(i):
                if self.server.handlers_registered(i)>1:
                    raise ValueError(
                        f"Session store functions should not be an event group problem in {i}."
                    )
            else:
                raise ValueError(f"Session store function {i} is not defined")

    async def create_session(self, ctx):
        s = await self.wrap_event("create_session", ctx) or dict()
        token = await self.run_event("new_session", ctx, s)
        s[self.cookie_name] = token
        self.server.sessions[ctx.addr] |= s
        return {self.cookie_name: token}

    @event()
    async def create_cookies(self, ctx):
        token = ctx.cookies.get(self.cookie_name, None)
        s = await self.run_event("get_session", token)
        if s is None:
            return await self.create_session(ctx)

        self.server.sessions[ctx.addr] |= s
        self.server.sessions[ctx.addr][self.cookie_name] = token
        return {self.cookie_name: token}

    @event()
    async def on_session_close(self, ctx):
        if self.server.is_event_socket(ctx.addr):
            return
        token = ctx.session.get(self.cookie_name, None)
        if token is None:
            return
        session = await self.sanitize_session(ctx.session.copy())
        await self.run_event("save_session", token, session)
        
    @event()
    async def startup(self,ctx):
        self.check_session_store()
        self.check_cookies()

