import logging
from .module_helper import ServerModule, event
import time

logger = logging.getLogger("zono.server")


class Logging(ServerModule):
    def __init__(self,requests=False):
        self.requests = requests
        
    def setup(self, ctx):
        self.form_addr = ctx.app.form_addr
        
    def module(self, module):
        if self.requests is False:
            module['events'].pop('on_request_processed')
            module['events'].pop('after_packet')

    @event()
    def on_connect(self, ctx):
        if ctx.app.is_event_socket(ctx.addr):
            return logger.info(
                f"{self.form_addr(ctx.session.parent_addr)} event socket connected"
            )
        logger.info(f"{self.form_addr(ctx.addr)} connected")

    @event()
    def on_disconnect(self, ctx):
        if (ctx.session is not None) and ctx.session.get(
            "parent_addr", None
        ) is not None:
            return logger.info(
                f"{self.form_addr(ctx.session.parent_addr)} event socket disconnected"
            )

        logger.info(f"{self.form_addr(ctx.addr)} disconnected")

    @event()
    def on_start(self, ctx):
        logger.info(f"Server listening @{ctx.ip}:{ctx.port}")

    @event()
    def on_client_error(self, ctx):
        logger.error(f"Client error {self.form_addr(ctx.addr)}: {ctx.wrapped_error} {ctx._dict.get('pkt','')}")

    @event()
    def on_connection_refusal(self, ctx):
        logger.error(f"{self.form_addr(ctx.addr)} connection refused")

    @event()
    def on_connect_fail(self, ctx):
        logger.error(f"{self.form_addr(ctx.addr)} connection initiation failed")
    
    @event()
    def after_packet(self,ctx):
        ctx.pkt_time = time.time()
        
    @event()
    def on_request_processed(self,ctx):
        elapsed_time = round((time.time() - ctx.pkt_time) *1000,3)
        logger.info(f'{ctx.app.form_addr(ctx.addr)} /{ctx.pkt.get("path")} {elapsed_time}ms')