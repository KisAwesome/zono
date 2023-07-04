class ToggleBool:
    def __init__(self, original_val):
        self.val = bool(original_val)

    def toggle(self):
        self.val = not self.val

    def __and__(self, other):
        return self.val and other

    def __or__(self, other):
        return self.val or other

    def __xor__(self, other):
        return self.val != bool(other)

    def __invert__(self):
        return not self.val

    def __eq__(self, other):
        return self.val == bool(other)

    def __ne__(self, other):
        return self.val != bool(other)

    def __lt__(self, other):
        return self.val < bool(other)

    def __le__(self, other):
        return self.val <= bool(other)

    def __gt__(self, other):
        return self.val > bool(other)

    def __ge__(self, other):
        return self.val >= bool(other)

    def __add__(self, other):
        return int(self.val) + other

    def __radd__(self, other):
        return other + int(self.val)

    def __sub__(self, other):
        return int(self.val) - other

    def __rsub__(self, other):
        return other - int(self.val)

    def __mul__(self, other):
        return int(self.val) * other

    def __rmul__(self, other):
        return other * int(self.val)

    def __truediv__(self, other):
        return int(self.val) / other

    def __rtruediv__(self, other):
        return other / int(self.val)

    def __floordiv__(self, other):
        return int(self.val) // other

    def __rfloordiv__(self, other):
        return other // int(self.val)

    def __mod__(self, other):
        return int(self.val) % other

    def __rmod__(self, other):
        return other % int(self.val)

    def __pow__(self, other, modulo=None):
        return int(self.val) ** other

    def __rpow__(self, other, modulo=None):
        return other ** int(self.val)
