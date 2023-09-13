from collections import namedtuple
from datetime import datetime
from itertools import repeat
from random import SystemRandom

rnd = SystemRandom()


class Lottery:
    def __init__(self,
                 max_numbers=90,
                 len_numbers=6,
                 max_extra=90,
                 len_extra=1,):
        self.max_numbers = max_numbers
        self.max_extra = max_extra
        self.len_numbers = len_numbers
        self.len_extra = len_extra
        self._stop = 0
        self._many = 1

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, value):
        match value:
            case 'choice':
                self._backend = self.choice
            case 'randint':
                self._backend = self.randint
            case 'sample':
                self._backend = self.sample
            case _:
                raise ValueError('not a valid backend')

    @backend.getter
    def backend(self):
        return self._backend.__name__

    @property
    def extraction(self):
        return self._extraction

    @extraction.setter
    def extraction(self, combos):
        self._extraction = combos

    @staticmethod
    def choice(_len, _max):
        if not (_len and _max):
            return None

        numbers = list(range(1, _max+1))

        def extraction():
            sample = rnd.choice(numbers)
            numbers.remove(sample)
            return sample

        return frozenset(extraction() for _ in range(_len))

    @staticmethod
    def sample(_len, _max):
        if not (_len and _max):
            return None

        numbers = tuple(range(1, _max+1))

        return frozenset(rnd.sample(numbers, k=_len))

    @staticmethod
    def randint(_len, _max):
        if not (_len and _max):
            return None

        # create an iterator that calls random.randint until it returns
        # None, but since it is impossible to get None from it, it works
        # as an infinite generator
        numbers = iter(lambda: rnd.randint(1, _max), None)

        combo = set()
        while len(combo) < _len:
            combo.add(next(numbers))

        return frozenset(combo)

    def extract(self):
        numbers = self._backend(self.len_numbers, self.max_numbers)
        extra = self._backend(self.len_extra, self.max_extra)

        return numbers, extra

    def many_samples(self):
        '''
        To add further randomness, this method simulates several extractions
        among 1 and <many> times, and picks one casually ... hopefully the
        winning one :D
        '''
        sample = frozenset(), frozenset()
        size = self._many or 1
        self._stop = rnd.randint(1, size)

        for _ in repeat(None, self._stop):
            sample = self.extract()

        return sample

    def __call__(self, backend='choice', many=None):
        self._many = many
        self.backend = backend

        Extraction = namedtuple('Extraction', ['numbers', 'extra'])
        self._extraction = Extraction(*self.many_samples())

        return self

    @property
    def draw(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        print('Estrazione del:', now, '\nNumeri Estratti:',
              *sorted(self.extraction.numbers))

        if self.extraction.extra is not None:
            print('Superstar:', *sorted(self.extraction.extra))
