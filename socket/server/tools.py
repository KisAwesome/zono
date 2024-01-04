import zono.schema


not_none = lambda x: (False, "") if x is None else (True, "")


def pkt_schema(schema):
    f = zono.schema.Validator(schema)

    def wrapper(func):
        def validate_pkt(cls, ctx):
            v = f.validate(ctx.pkt)
            if v:
                return ctx.send(
                    dict(
                        success=False, code=400, msg="pkt did not match expected format"
                    )
                )
            return func(cls, ctx)

        return validate_pkt

    return wrapper
