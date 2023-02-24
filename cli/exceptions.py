class CommandAlreadyRegistered(ValueError):
    pass


class ApplicationError(Exception):
    def __init__(self, *args):
        super().__init__(*args)


class CommandError(ApplicationError):
    def __init__(self, ctx, error, exc_info, *args, **kwargs):
        self.ctx = ctx
        self.error = error
        self.exc_info = exc_info
        self.ctx.exc_info = exc_info
        super().__init__(*args, **kwargs)


class EventError(ApplicationError):
    def __init__(self, ctx, error, exc_info, *args, **kwargs):
        self.ctx = ctx
        self.error = error
        self.exc_info = exc_info
        self.ctx.exc_info = exc_info
        super().__init__(*args, **kwargs)


class ArgumentError(Exception):
    pass
