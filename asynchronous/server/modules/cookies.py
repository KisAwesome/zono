from .module_helper import ServerModule, event
import time


class Cookies(ServerModule):
    def __init__(self, expires=None):
        self.expires = expires

    def check_server_name(self):
        if not hasattr(self.server, "name"):
            raise ValueError("Server does not have a name")

    def setup(self, ctx):
        self.server = ctx.app
        
    @event()
    async def startup(self,ctx):
        self.check_server_name()

    @event()
    async def connection_established_info(self, ctx):
        if not isinstance(ctx.client_info, dict):
            return
        ctx.cookies = ctx.client_info.get("cookies", None)
        ctx.session.sent_cookies = isinstance(ctx.cookies,dict)
        ctx.cookies = ctx.cookies or {}
        await ctx.app.run_event('cookies_loaded',ctx)
        cookies = await ctx.app.wrap_event("create_cookies", ctx)
        if self.expires is not None:
            if "expires" not in ctx.cookies: 
                cookies["expires"] = time.time() + self.expires
            else:
                cookies["expires"] = ctx.cookies["expires"]
        ctx.created_cookies = cookies
        await ctx.app.run_event('cookies_created',ctx)
        return dict(cookies=cookies)

