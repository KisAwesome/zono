from .module_helper import ServerModule, event
import zono.socket.server


class ServerName(ServerModule):
    def __init__(self, name):
        self.name = name

    @event()
    def server_info(self, ctx):
        return dict(name=self.name)


class PersistentSessions(ServerModule):
    def setup(self, ctx):
        self.server = ctx.app
        self.run_event = self.server.run_event
        self.wrap_event = self.server.wrap_event
        self.check_session_store()

    def sanitize_session(self, session):
        for i in ("conn", "key", "event_socket_addr", "event_socket", "_session",'parent_addr'):
            session.pop(i, None)
        return session

    def check_session_store(self):
        for i in ("get_session", "save_session", "new_session"):
            if self.server.isevent(i, True) or not self.server.isevent(i):
                if self.server.isevent(i, True):
                    raise ValueError(
                        f"Session store functions should not be an event group problem in {i}."
                    )
                else:
                    raise ValueError(f"Session store function {i} is not defined")

    def create_session(self, ctx):
        s = self.wrap_event("create_session", ctx) or dict()
        token = self.run_event("new_session", ctx, s)
        s["_session"] = token
        self.server.sessions[ctx.addr] |= s
        return dict(_session=token)

    @event()
    def create_cookies(self, ctx):
        token = ctx.cookies.get("_session", None)
        s = self.run_event("get_session", token)
        if s is None:
            return self.create_session(ctx)

        self.server.sessions[ctx.addr] |= s
        self.server.sessions[ctx.addr]['_session'] = token
        return dict(_session=token)

    @event()
    def on_session_close(self, ctx):
        if self.server.is_event_socket(ctx.addr):
            return
        token = ctx.session.get("_session", None)
        if token is None:
            return
        session = self.sanitize_session(ctx.session)
        self.run_event("save_session", token, session)
        
    def get_connection_info(self,session):
        info = {}
        for s in ("conn", "key", "event_socket_addr", "event_socket",'parent_addr'):
            i =session.get(s,None)
            if i:
                info[s] =i
        return info

    @event()
    def load_session(self,addr,session_id):
        session = self.get_connection_info(self.server.get_session(addr))
        s = self.run_event("get_session", session_id)
        if s is None:
            raise ValueError("Session not found")
        
        self.server.sessions[addr] = session|s
        self.server.sessions[addr]['_session'] = session_id
        
        
        