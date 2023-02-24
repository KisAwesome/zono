print('Thanks for using zono')




class toggle_bool:
    def __init__(self, original_val):
        if not isinstance(original_val, bool):
            raise TypeError(
                f'Inputed original value must be a bool not a {type(original_val)}'
            )
        self.val = original_val

    def toggle(self):
        self.val = not self.val
