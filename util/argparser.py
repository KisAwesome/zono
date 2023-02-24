class Empty:
    pass


def _parse_optionals(_optionals):
    positonals = []
    _empty = Empty()
    for i in _optionals:
        if isinstance(i, tuple):
            positonals.append((i[0], i[1]))
        elif isinstance(i, str):
            positonals.append((i, _empty))

    return positonals


def parse_args(self, positional, optional, args, kwargs):
    optional = _parse_optionals(optional)
    missing = list(positional)[len(args) :]
    x = [i for i in missing if i not in kwargs.keys()]

    if x:
        raise ValueError(f"Required arguments missing", ", ".join(x))

    attrs = {}
    for ind, arg in enumerate(args):
        attrs[positional[ind]] = arg
    attrs |= kwargs
    for k, v in attrs.items():
        setattr(self, k, v)

    for i in optional:
        if (i not in kwargs) and isinstance(i[1], Empty):
            continue
        setattr(self, i[0], kwargs.get(i[0], i[1]))
