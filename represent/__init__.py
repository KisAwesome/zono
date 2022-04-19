print('Thanks for using zono')

__all__ = ['BASIC', 'BASICPLUS']

BASIC = 'BASIC'
BASICPLUS = 'BASICPLUS'


class representation:

    BASIC = 'BASIC'
    BASICPLUS = 'BASICPLUS'

    def __init__(self,
                 representation=BASIC,
                 pair_name='Pair number',
                 key_name='Key',
                 value_name='Value',
                 count_number='Entity',
                 sep='\n',
                 value_sep=' : '):
        global __all__
        if not representation in __all__:
            raise TypeError('reprentation can only be BASIC or BASICPLUS')
        self.representation = representation
        self.pair_name = pair_name
        self.key_name = key_name
        self.value_name = value_name
        self.count_number = count_number
        self.value_sep = value_sep
        self.sep = sep
        self.additions = {}

        ind = 0
        for i in self.pair_name:
            if i == r'/':
                if self.pair_name[ind + 1] == 'i':
                    self.additions['pairname'] = ind
            ind += 1

        ind = 0
        for i in self.key_name:
            if i == r'/':
                if self.key_name[ind + 1] == 'i':
                    self.additions['keyname'] = ind
            ind += 1

        ind = 0
        for i in self.value_name:
            if i == r'/':
                if self.value_name[ind + 1] == 'i':
                    self.additions['valuename'] = ind
            ind += 1
        ind = 0
        for i in self.sep:
            if i == r'/':
                if self.sep[ind + 1] == 'i':
                    self.additions['sep'] = ind
            ind += 1
        ind = 0
        for i in self.value_sep:
            if i == r'/':
                if self.value_sep[ind + 1] == 'i':
                    self.additions['valuesep'] = ind
            ind += 1

    def represent(self, entity):
        if isinstance(entity, dict):
            fin = ''
            num = 1
            if self.representation == 'BASIC':

                for i in entity:
                    if isinstance(i, str):
                        i2 = f'\'{i}\''
                    else:
                        i2 = i

                    hold = f'{num}{self.value_sep}{i2}{self.value_sep}{entity[i]}'

                    fin = f'{fin}{self.sep}{hold}'
                    num += 1

                return fin
            elif self.representation == 'BASICPLUS':
                fin = ''
                num = 1

                for i in entity:
                    if isinstance(i, str):
                        i2 = f'\'{i}\''
                    else:
                        i2 = i

                    hold = f'{self.pair_name}{self.value_sep}{num}{self.value_sep}{self.key_name}{self.value_sep}{i2}{self.value_sep}{self.value_name}{self.value_sep}{entity[i]}'

                    fin = f'{fin}{self.sep}{hold}'
                    num += 1

                return fin
        elif isinstance(entity, list):
            if self.representation == 'BASIC':
                fin = ''
                count = 0
                for i in entity:
                    hold = f'{count}{self.value_sep}{i}'
                    if count == 0:
                        fin = hold
                        count += 1
                        continue
                    fin += self.sep + hold
                return fin

            if self.representation == 'BASICPLUS':
                fin = ''
                count = 0
                for i in entity:
                    hold = f'{self.count_number}{self.value_sep}{count}{self.value_sep}{self.value_name}{self.value_sep}{i}'
                    if count == 0:
                        fin = hold
                        count += 1
                        continue
                    fin += self.sep + hold
                return fin
