class search:
    def __init__(self, values):
        self.val = values

    def search(self, term):
        for i in self.val:
            if term.lower().strip() in i.lower().strip():
                return True