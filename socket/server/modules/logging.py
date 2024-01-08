import logging
from .module_helper import ServerModule, event
import time
import yaml


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

    def calculate_send_length(self,pkts):
        length = 0
        for pkt in pkts:
            length+= len(yaml.safe_dump(pkt))
        return self.format_file_size(length)
    
    def format_file_size(self,size_in_bytes):
        units = ['B', 'KB', 'MB', 'GB']
        threshold = 1024

        size = size_in_bytes
        unit_index = 0
        while size >= threshold and unit_index < len(units) - 1:
            size /= threshold
            unit_index += 1
        if int(size) == size:
            size = int(size)
        else:
            size = round(size,2)
        formatted_size = f"{size}{units[unit_index]}"
        return formatted_size


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
        size =self.calculate_send_length(ctx.responses)
        recv_s = self.format_file_size(len(yaml.safe_dump(ctx.raw_pkt)))
        logger.info(f'{ctx.app.form_addr(ctx.addr)} /{ctx.pkt.get("path")} {elapsed_time}ms received {recv_s} sent {size}')