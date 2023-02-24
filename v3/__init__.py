print("Thanks for using zono")


class v3:
    def __test__(self, totest):
        try:
            float(totest)
        except:
            raise ValueError("Coordinate must be a float")

    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z
        self.__test__(self.x)
        self.__test__(self.z)
        self.__test__(self.y)

    @property
    def val(self):
        return (self.x, self.y, self.z)

    def __repr__(self):
        return str(self.val)

    def __add__(self, V3):
        new_x = self.x + V3.x
        new_y = self.y + V3.y
        new_z = self.z + V3.z

        new_cord = v3(new_x, new_y, new_z)
        return new_cord

    def __eq__(self, v3):
        if self.x == v3.x and self.y == v3.y and self.z == v3.z:
            return True
        else:
            return False

    def __ne__(self, v3):
        if not self.x == v3.x and self.y == v3.y and self.z == v3.z:
            return True
        else:
            return False

    def __truediv__(self, V3):
        if not isinstance(V3, v3):
            raise TypeError("V3 must be an instance of v3")

        new_x = self.x / V3.x
        new_y = self.y / V3.y
        new_z = self.z / V3.z

        new_cord = v3(new_x, new_y, new_z)
        return new_cord

    def __mul__(self, V3):
        if not isinstance(V3, v3):
            raise TypeError("V3 must be an instance of v3")

        new_x = self.x * V3.x
        new_y = self.y * V3.y
        new_z = self.z * V3.z

        new_cord = v3(new_x, new_y, new_z)
        return new_cord

    def __sub__(self, V3):
        if not isinstance(V3, v3):
            raise TypeError("V3 must be an instance of v3")

        new_x = self.x - V3.x
        new_y = self.y - V3.y
        new_z = self.z - V3.z

        new_cord = v3(new_x, new_y, new_z)
        return new_cord

    def __str__(self):
        return f"(x{self.x},y{self.y},z{self.z})"
