from typing import Any


class Store(dict):
    dictattrs = [
        "__class__",
        "__class_getitem__",
        "__contains__",
        "__delattr__",
        "__delitem__",
        "__dir__",
        "__doc__",
        "__eq__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getitem__",
        "__gt__",
        "__hash__",
        "__init__",
        "__init_subclass__",
        "__ior__",
        "__iter__",
        "__le__",
        "__len__",
        "__lt__",
        "__ne__",
        "__new__",
        "__or__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__reversed__",
        "__ror__",
        "__setattr__",
        "__setitem__",
        "__sizeof__",
        "__str__",
        "__subclasshook__",
        "clear",
        "copy",
        "fromkeys",
        "get",
        "items",
        "keys",
        "pop",
        "popitem",
        "setdefault",
        "update",
        "values",
    ]

    def __setattr__(self, __name: Any, __value: Any) -> None:
        if __name in Store.dictattrs:
            return super().__setattr__(__name, __value)
        return super().__setitem__(__name, __value)

    def __getattribute__(self, __name: Any) -> Any:
        if __name in Store.dictattrs:
            return super().__getattribute__(__name)
        return super().__getitem__(__name)

    def __delattr__(self, __name: Any) -> Any:
        return super().pop(__name, None)
