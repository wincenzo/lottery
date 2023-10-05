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
                 len_extra=1):
        self.max_numbers = max_numbers
        self.max_extra = max_extra
        self.len_numbers = len_numbers
        self.len_extra = len_extra
        self.backend = 'sample'
        self.extraction = self.Extraction(frozenset(),
                                          frozenset())
        self._many = None
        self._stop = 1

    Extraction = namedtuple('Extraction', ('numbers', 'extra'))

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

    @staticmethod
    def choice(len_, max_):
        if not (len_ and max_):
            return None

        numbers = list(range(1, max_ + 1))

        def drawer():
            sample = rnd.choice(numbers)
            numbers.remove(sample)
            return sample

        return frozenset(drawer() for _ in range(len_))

    @staticmethod
    def sample(len_, max_):
        if not (len_ and max_):
            return None

        numbers = tuple(range(1, max_ + 1))

        return frozenset(rnd.sample(numbers, k=len_))

    @staticmethod
    def randint(len_, max_):
        if not (len_ and max_):
            return None

        # create an iterator that calls random.randint until it returns
        # None, but since it is impossible to get None from it, it works
        # as an infinite generator
        numbers = iter(lambda: rnd.randint(1, max_), None)

        combo = set()
        while len_ - len(combo):
            combo.add(next(numbers))

        return frozenset(combo)

    def extract(self):
        numbers = self._backend(self.len_numbers, self.max_numbers)
        extra = self._backend(self.len_extra, self.max_extra)

        return numbers, extra

    def many_samples(self):
        '''
        To add further randomness, this method simulates several
        extractions among 1 and <many> times, and picks one casually,
        hopefully the winning one :D
        '''
        self._stop = rnd.randint(1, self._many or 1)

        numbers, extra = frozenset(), frozenset()
        for _ in repeat(None, self._stop):
            numbers, extra = self.extract()

        return numbers, extra

    def __call__(self, backend=None, many=None):
        self._many = many
        self.backend = backend

        self.extraction = self.Extraction(*self.many_samples())

        return self

    @property
    def draw(self):
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        if self.extraction is not None:
            print('Estrazione del:', now, '\nNumeri Estratti:',
                  *sorted(self.extraction.numbers))

            if self.extraction.extra is not None:
                print('Superstar:', *sorted(self.extraction.extra))
