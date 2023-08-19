class search:
    def __init__(self, values):
        self.val = values

    def search(self, term):
        for i in self.val:
            i = str(i)
            term = str(term)
            if term.lower().strip() in i.lower().strip():
                return True