class Queue(list):
    def __init__(self, limit=None):
        self.limit = limit

    def append(self, el):
        if self.limit:
            if super().__len__() >= self.limit:
                super().pop(0)
        super().append(el)

class Stack(list):
    def __init__(self, limit=None):
        self.limit = limit
        self.pointer = None

    def push(self, el):
        if self.limit:
            if super().__len__() >= self.limit:
                super().pop(0)
        super().append(el)  

    def pop(self):
        if super().__len__() > 0:
            if self.pointer is None:
                self.pointer = super().__len__()-1
            if self.pointer ==-1:
                raise IndexError("Stack is empty")
            self.pointer-=1
            return super().__getitem__(self.pointer+1)
            
        else:
            raise IndexError("Stack is empty")

    def peek(self):
        l = super().__len__() 
        if l>0 and l > self.pointer:
            if self.pointer ==-1:
                self.pointer =0
            self.pointer += 1
            return super().__getitem__(self.pointer)
        else:
            raise IndexError("Stack cannot be peeked")