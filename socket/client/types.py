import pprint


class Context:
    def __init__(self, app, **kwargs):
        self.app = app
        for i in kwargs:
            setattr(self, i, kwargs[i])

        self._dict = dict(app=app, **kwargs)

    def __repr__(self) -> str:
        return pprint.pformat(self._dict)
