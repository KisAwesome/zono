from .module_helper import ServerModule, event
from zono.socket.server.types import Context
from zono.socket.server.exceptions import ClientError


class EventSocket(ServerModule):
    def setup(self, ctx):
        self.server = ctx.app
        self.run_event = self.server.run_event
        self.wrap_event = self.server.wrap_event
        self.server.is_event_socket = self.is_event_socket
        self.server.send_event = self.send_event
        self.server.event_socket = True

    def is_event_socket(self, addr):
        s = self.server.get_session(addr)
        if s is None:
            return False
        if s.get("parent_addr", None) is not None:
            return True
        return False

    def _event_socket(self, ctx):
        addr = tuple(ctx.client_info.get("_event_socket_addr", None))
        key = ctx.client_info.get("_event_socket_key", None)

        if not (addr and key):
            return dict(success=False, error=True, info="Incomplete packet")

        user_session = self.server.get_session(addr)
        if user_session is None:
            return dict(success=False, error=True, info="session does not exist")

        if user_session["key"] != key:
            return dict(success=False, error=True, info="Session key does not match")

        ctx.session["parent_addr"] = addr
        user_session["event_socket"] = ctx.conn
        user_session["event_socket_addr"] = ctx.addr
        self.run_event(
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
    def connection_established_info(self, ctx):
        if ctx.client_info.get("_event_socket", False) is False:
            return dict()

        return dict(_event_socket=self._event_socket(ctx))

    @event()
    def server_info(self, ctx):
        return dict(event_socket=True)

    @event()
    def on_session_close(self, ctx):
        if ctx.session.get("event_socket", None) is not None:
            self.server.close_socket(
                ctx.session.event_socket, ctx.session.event_socket_addr
            )

    def send_event(self, addr, event):
        session = self.server.get_session(addr)
        if not session:
            raise ValueError("Session not found")

        ev_sock = session.get("event_socket", None)
        ev_addr = session.get("event_socket_addr", None)
        if ev_sock is None or ev_addr is None:
            raise ClientError(f"{addr} has no event socket registered")

        self.server.send(event, ev_sock, ev_addr)
