from .module_helper import ServerModule, event
from zono.asynchronous.server.types import Context
from zono.socket.server.exceptions import ClientError, client_errors


client_errors[129] = "Address has no registered event socket"


class EventSocket(ServerModule):
    def setup(self, ctx):
        self.server = ctx.app
        self.run_event = self.server.run_event
        self.wrap_event = self.server.wrap_event
        self.server.is_event_socket = self.is_event_socket
        self.server.send_event = self.send_event
        self.server.event_socket = True
        self.server.has_event_socket = self.has_event_socket

    def is_event_socket(self, addr):
        s = self.server.get_session(addr)
        if s is None:
            return False
        if s.get("parent_addr", None) is not None:
            return True
        return False

    async def _event_socket(self, ctx):
        addr = tuple(ctx.client_info.get("_event_socket_addr", None))
        key = ctx.client_info.get("_event_socket_key", None)
        ctx.event_socket = False
        if not (addr and key):
            return dict(success=False, error=True, info="Incomplete packet")

        user_session = self.server.get_session(addr)
        if user_session is None:
            return dict(success=False, error=True, info="session key or address are incorrect")

        if user_session["key"] != key:
            return dict(success=False, error=True, info="session key or address are incorrect")

        ctx.session["parent_addr"] = addr
        user_session["event_socket"] = ctx.conn
        user_session["event_socket_addr"] = ctx.addr
        ctx.event_socket = True
        await self.run_event(
            "event_socket_registered",
            Context(
                self.server,
                client_session=user_session,
                addr=ctx.addr,
                conn=ctx.conn,
                parent_addr=addr,
            ),
        )
        return dict(
            success=True, error=False, info="Registered event socket successfully"
        )

    @event()
    async def connection_established_info(self, ctx):
        if ctx.client_info.get("_event_socket", False) is False:
            ctx.event_socket = False
            return dict()

        return dict(_event_socket=await self._event_socket(ctx))

    @event()
    async def server_info(self, ctx):
        return dict(event_socket=True)

    @event()
    async def on_session_close(self, ctx):
        if ctx.session.get("event_socket", None) is not None and ctx.app._shutting_down is False:
            await self.server.close_socket(
                ctx.session.event_socket, ctx.session.event_socket_addr
            )
 
    @event()
    async def create_context(self, ctx):
        if ctx._dict.get("addr", None) is not None:
            ctx.send_event = lambda event: self.send_event(ctx.addr, event)

    @event()
    def sanitize_session(self, ctx):
        return ["event_socket_addr", "event_socket", "parent_addr"]

    @event()
    def prepare_user_session(self, ctx):
        return ["event_socket_addr", "event_socket", "parent_addr"]

    @event()
    def start_event_loop(self, ctx):
        if self.is_event_socket(ctx.addr):
            return False

        return True

    async def send_event(self, addr, event):
        session = self.server.get_session(addr)
        if not session:
            raise ValueError("Session not found")

        ev_sock = session.get("event_socket", None)
        ev_addr = session.get("event_socket_addr", None)
        if ev_sock is None or ev_addr is None:
            raise ClientError(
                129, ctx=Context(self.server, addr=addr, event_to_send=event)
            )

        await self.server.send(event, ev_sock, ev_addr)
    def has_event_socket(self,addr):
        session = self.server.get_session(addr)
        if not session:
            raise ValueError("Session not found")
        ev_sock = session.get("event_socket", None)
        ev_addr = session.get("event_socket_addr", None)
        if ev_sock is None or ev_addr is None:
            return False
        return True