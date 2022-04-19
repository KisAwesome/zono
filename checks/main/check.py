
class Check:
    STR = 'STR'
    FLOAT = 'FLOAT'

    def __init__(self, *refrence, capsense=True, Type='STR'):
        self.cap = capsense
        self.Type = Type
        self.ref = list(refrence)

        if not self.cap:
            if self.Type == 'STR':
                self.ref = [each_string.lower() for each_string in self.ref]

    def check(self, Input):
        # if not self.cap:
        #     if self.Type != float:
        #         Input = Input.upper()
        if self.Type == 'STR':
            # print(self.cap)
            if self.cap == False:
                # print('h')
                if Input.lower() in self.ref:
                    # print(self.ref)
                    return True

            if Input in self.ref:
                return True

        if self.Type == 'FLOAT':
            try:
                Input = float(Input)

            except:
                pass
            else:
                if Input in self.ref:
                    return True
        # return False


class Range:
    def __init__(self, start, end, *args, step=1, hard_input=False):
        self.arg = list(args)
        self.hard = hard_input
        self.hold = []
        self.end = end
        self.start = start
        self.step = step
        self.fin = []
        self.arg.append([self.start, self.end, self.step])

        for i in range(len(self.arg)):
            try:
                hi = self.arg[i][2]

            except:
                self.arg[i].append(1)

            hold = list(range(self.arg[i][0], self.arg[i][1], self.arg[i][2]))
            self.hold.append(hold)

        for i1 in range(len(self.hold)):
            for i3 in range(len(self.hold[i1])):
                self.fin.append(self.hold[i1][i3])

    def check(self, Input):
        try:
            Input = int(Input)
        except:
            if self.hard:
                raise TypeError

        else:
            if Input in self.fin:
                return True


def Avrg(*inputs):
    return sum(list(inputs)) / len(list(inputs))


def rettype(Input, return_as_string=False):
    if isinstance(Input, float):
        if return_as_string:
            return "float"
        return float

    elif isinstance(Input, bool):
        if return_as_string:
            return "bool"
        return bool
    elif isinstance(Input, int):
        if return_as_string:
            return "int"
        return int

    elif isinstance(Input, str):
        if return_as_string:
            return "str"
        return str

    elif isinstance(Input, list):
        if return_as_string:
            return "list"
        return list
    elif isinstance(Input, dict):
        if return_as_string:
            return "dict"
        return dict

    elif isinstance(Input, set):
        if return_as_string:
            return "set"
        return set
    elif isinstance(Input, tuple):
        if return_as_string:
            return "tuple"
        return tuple

    elif isinstance(Input, map):
        if return_as_string:
            return "map"
        return map
