from .module_helper import ServerModule, event, EventGroup
import time


class Cookies(ServerModule):
    def __init__(self, expires=None):
        self.expires = expires

    @event()
    def connection_established_info(self, ctx):
        if not isinstance(ctx.client_info, dict):
            return
        ctx.cookies = ctx.client_info.get("cookies", {})
        cookies = ctx.app.wrap_event("create_cookies", ctx)
        if self.expires is not None:
            if "expires" not in ctx.cookies:
                cookies["expires"] = time.time() + self.expires
            else:
                cookies["expires"] = ctx.cookies["expires"]
        return dict(cookies=cookies)

    def module(self, module):
        module["events"]["create_cookies"] = EventGroup("create_cookies")
