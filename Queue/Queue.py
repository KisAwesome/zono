class Queue(list):
    def __init__(self,limit=None):
        self.limit = limit

    def append(self,el):
        if self.limit:
            if super().__len__() >= self.limit:
                super().pop(0)
        super().append(el)
