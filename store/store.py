class Store(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __ior__(self, other):
        super().__ior__(other)
        return self

    def __iand__(self, other):
        super().__iand__(other)
        return self

    def __iadd__(self, other):
        super().__iadd__(other)
        return self

    def __isub__(self, other):
        super().__isub__(other)
        return self

    def __imul__(self, other):
        super().__imul__(other)
        return self

    def __itruediv__(self, other):
        super().__itruediv__(other)
        return self

    def __ifloordiv__(self, other):
        super().__ifloordiv__(other)
        return self

    def __imod__(self, other):
        super().__imod__(other)
        return self

    def __ipow__(self, other, modulo=None):
        super().__ipow__(other, modulo)
        return self
    
    def __or__(self, other):
        return Store(super().__or__(other))