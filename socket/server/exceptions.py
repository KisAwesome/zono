class ApplicationError(Exception):
    def __init__(self, ctx, error, exc_info, *args, **kwargs):
        if ctx:
            ctx.error = error
            ctx.exc_info = exc_info
        self.ctx = ctx
        self.error = error
        self.exc_info = exc_info
        super().__init__(*args, **kwargs)


class RequestError(ApplicationError):
    pass


class EventError(ApplicationError):
    pass


class MiddlewareError(ApplicationError):
    pass


class ClientError(Exception):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
