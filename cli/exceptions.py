class CommandAlreadyRegistered(ValueError):
    pass


class CommandError(Exception):
    def __init__(self, ctx, error, exc_info, *args, **kwargs):
        self.ctx = ctx
        self.error = error
        self.exc_info = exc_info
        self.ctx.exc_info = exc_info
        super().__init__(*args, **kwargs)


class EventError(Exception):
    def __init__(self, ctx, error, exc_info, *args, **kwargs):
        self.ctx = ctx
        self.error = error
        self.exc_info = exc_info
        self.ctx.exc_info = exc_info
        super().__init__(*args, **kwargs)
