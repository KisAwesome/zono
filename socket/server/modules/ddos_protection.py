
from .module_helper import event, ServerModule
import zono.zonocrypt
import zono.workers
import time


class DDOSProtection(ServerModule):
    def __init__(self,max_packets_per_minute=60,block_time=3600,max_failed_connect_inits=5,max_connections=2):
        self.max_packets_per_minute = max_packets_per_minute
        self.block_time=block_time
        self.max_failed_connect_inits = max_failed_connect_inits
        self.max_connections = max_connections

    def setup(self, ctx):
        self.server = ctx.app
        self.ipsessions = dict()
        ctx.app.intervals.add(zono.workers.Interval(60, self.reset_sent))


    def session_exists(self,addr):
        return addr[0] in self.ipsessions

    def create_session(self,addr):
        self.ipsessions[addr[0]] = dict(connections=set(),blocked=False,unblock_time=None,failed_connections=0,sent=0)

    def increment_session(self,addr,field,x=1):
        self.ipsessions[addr[0]][field] +=x

    def get_session(self,addr):
        return self.ipsessions.get(addr[0],None)
    
    def update_session(self,addr,k,value):
        self.ipsessions[addr[0]][k] = value
    
    def get_session_value(self,addr,value):
        return self.get_session(addr)[value]
    
    def save_session(self,addr,s):
        self.ipsessions[addr] = s


    def block(self, ctx,r=''):
        self.update_session(ctx.addr, "blocked", True)
        self.update_session(ctx.addr, "unblock_time", time.time() + self.block_time)

        for addr in self.get_session(ctx.addr)['connections'].copy():
            s = self.server.get_session(addr)
            if s is not None:
                self.server.close_socket(s['conn'],addr)
        self.server.logger.info(f'Blocked {ctx.addr[0]} for {self.block_time} seconds for reason: {r}')

    @event()
    def on_connect(self,ctx):
        if not self.session_exists(ctx.addr):
            self.create_session(ctx.addr)
        self.ipsessions[ctx.addr[0]]['connections'].add(ctx.addr)

    @event()
    def before_packet(self, ctx):
        s= self.get_session(ctx.addr)
        if s['blocked']:
            return False
        
        self.increment_session(ctx.addr, "sent")
        if s['sent'] >= self.max_packets_per_minute:
            self.block(ctx,'Too many packets per minute')
            return False
        return True

    @event()
    def on_disconnect(self,ctx):
        self.ipsessions[ctx.addr[0]]['connections'].remove(ctx.addr)

    @event()
    def on_connect_fail(self, ctx):
        if not self.session_exists(ctx.addr):
            self.create_session(ctx.addr)
        self.increment_session(ctx.addr, "failed_connections")
        if (
            self.get_session_value(ctx.addr, "failed_connections")
            >= self.max_failed_connect_inits
        ):
            self.update_session(ctx.addr, "failed_connections", 0)
            self.block(ctx,'Too many failed connections')

    @event()
    def connect_check(self, ctx):
        if self.session_exists(ctx.addr):
            if (
                len(self.get_session_value(ctx.addr, "connections"))
                >= self.max_connections
            ):
                self.block(ctx,'Too many active connections')

            return not self.get_session_value(ctx.addr, "blocked")

        return True
    

    def reset_sent(self):
        curr_time = time.time()
        for addr, session in self.ipsessions.copy().items():
            if session["blocked"]:
                if session["unblock_time"] <= curr_time:
                    session["blocked"] = False
            session["sent"] = 0
            session['failed_connections'] = 0 
            self.save_session((addr, None), session)
