from zono.socket import ReceiveError, SendError


client_errors = {404:"Client requested path which does not exist"}


class ApplicationError(Exception):
    def __init__(self, ctx, error, exc_info, *args, **kwargs):
        if ctx is not None:
            ctx.error = error
            ctx.exc_info = exc_info
            ctx.wrapped_error = self
        self.ctx = ctx
        self.error = error
        self.exc_info = exc_info
        super().__init__(*args, **kwargs)


class RequestError(ApplicationError):
    pass


class MiddlewareError(ApplicationError):
    pass


class ClientError(Exception):
    def __init__(self,errorno,raw_err=None,msg=None,ctx=None,exc_info=None):
        if ctx is not None:
            ctx.error = raw_err
            ctx.exc_info = exc_info
            ctx.wrapped_error = self
        self.ctx = ctx
        self.errorno = errorno
        self.errormsg = client_errors.get(errorno, msg or "Unknown error")
        self.raw_err = raw_err
        super().__init__()

    def __str__(self):
        return f"Error {self.errorno} - {self.errormsg}"

