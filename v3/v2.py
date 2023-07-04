def valid_coords(coords):
    if isinstance(coords, list) or isinstance(coords, tuple):
        if len(coords) == 2:
            [v2.__test__(None,i) for i in coords ]
            return True

def operator_wrapper(f):
    def wrapper(self,inp):
        if not isinstance(inp,v2):
            if not valid_coords(inp):
                raise ValueError("Input must be v2 when adding to a v2")
            
            inp = v2(*inp)
        
        return f(self,inp)
    
    return wrapper

class v2:
    def __test__(self, totest):
        try:
            float(totest)
        except:
            raise ValueError("Coordinate must be a float")

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
        [self.__test__(i) for i in self.val ]


    @property
    def val(self):
        return (self.x, self.y)

    def __repr__(self):
        return str(self.val)

    @operator_wrapper
    def __add__(self, V2):
        new_x = self.x + V2.x
        new_y = self.y + V2.y

        new_cord = v2(new_x, new_y)
        return new_cord
    @operator_wrapper
    def __eq__(self, v2):
        if self.x == v2.x and self.y == v2.y:
            return True
        else:
            return False
    @operator_wrapper
    def __ne__(self, v2):
        return not self.__eq__(v2)
    @operator_wrapper
    def __truediv__(self, V2):
        new_x = self.x / V2.x
        new_y = self.y / V2.y


        new_cord = v2(new_x, new_y)
        return new_cord
    @operator_wrapper
    def __mul__(self, V2):
        new_x = self.x * V2.x
        new_y = self.y * V2.y

        new_cord = v2(new_x, new_y)
        return new_cord
    @operator_wrapper
    def __sub__(self, V2):
        if not isinstance(V2, v2):
            raise TypeError("V2 must be an instance of v2")

        new_x = self.x - V2.x
        new_y = self.y - V2.y

        new_cord = v2(new_x, new_y)
        return new_cord

    def __str__(self):
        return str(self.val)


    @property
    def magnitude(self):
        return (self.x**2+self.y**2)**0.5