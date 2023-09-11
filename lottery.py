from datetime import datetime
from random import SystemRandom
from itertools import repeat
from collections import namedtuple

rnd = SystemRandom()


class Lottery:

    def __init__(self,
                 max_numbers=90,
                 len_numbers=6,
                 max_extra=90,
                 len_extra=1):
        self.max_numbers = max_numbers
        self.max_extra = max_extra
        self.len_numbers = len_numbers
        self.len_extra = len_extra

    @property
    def numbers(self): return self.extraction.numbers

    @property
    def extra(self): return self.extraction.extra

    @property
    def backend(self): return self._backend.__name__

    @property
    def many(self): return self._many

    @staticmethod
    def choice(_len, max):
        if not (_len and max):
            ...

        else:
            numbers = list(range(1, max+1))

            def extraction():
                sample = rnd.choice(numbers)
                numbers.remove(sample)
                return sample

            return frozenset(extraction() for _ in range(_len))

    @staticmethod
    def sample(_len, max):
        if not (_len and max):
            ...

        else:
            numbers = tuple(range(1, max+1))

            return frozenset(rnd.sample(numbers, k=_len))

    @staticmethod
    def randint(_len, max):
        if not (_len and max):
            ...

        else:
            # create an iterator that calls draw() until it returns 0, but
            # since it is impossible to get 0 from draw(), it works as an
            # infinite generator
            def draw(): return rnd.randint(1, max)
            numbers = iter(draw, 0)

            combo = set()
            while len(combo) < _len:
                combo.add(next(numbers))

            return frozenset(combo)

    def extract(self):
        numbers = self._backend(self.len_numbers, self.max_numbers)
        extra = self._backend(self.len_extra, self.max_extra)  # or None

        return numbers, extra

    def manySamples(self):
        '''
        To add further randomness, this method simulates several extractions, 
        among 1 and <many> times, and picks one casually ... hopefully the 
        winning one :D
        '''
        sample = None, None
        size = self._many or 1
        self._stop = rnd.randint(1, size)

        for _ in repeat(None, self._stop):
            sample = self.extract()

        return sample

    def __call__(self, backend='choice', many=None):
        self._many = many

        match backend:
            case 'choice':
                self._backend = self.choice
            case 'randint':
                self._backend = self.randint
            case 'sample':
                self._backend = self.sample
            case _:
                raise Exception('not a valid backend')

        Extraction = namedtuple('Extraction', ['numbers', 'extra'])
        self.extraction = Extraction(*self.manySamples())

        return self

    @property
    def draw(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        print('Estrazione del:', now, '\nNumeri Estratti:',
              *sorted(self.numbers))

        if self.extra is not None:
            print('Superstar:', *sorted(self.extra))
