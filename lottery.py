from collections import namedtuple
from datetime import datetime
from itertools import islice
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
        self.backend = None
        self.extraction = self.Extraction(None, None)
        self._stop = None

    Extraction = namedtuple(
        'Extraction', ('numbers', 'extra'))

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
            case 'sample' | None:
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

        def get_number():
            number = rnd.choice(numbers)
            numbers.remove(number)
            return number

        return frozenset(get_number() for _ in range(len_))

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

        draw = iter(lambda: rnd.randint(1, max_), None)

        extraction = set()
        while len_ - len(extraction):
            number = next(draw)
            extraction.add(number)

        return frozenset(extraction)

    def extract(self):
        numbers = self._backend(self.len_numbers, self.max_numbers)
        extra = self._backend(self.len_extra, self.max_extra)

        return numbers, extra

    def many_samples(self, many):
        '''
        To add further randomness, this method simulates several
        extractions among 1 and <many> times, and picks one casually,
        hopefully the winning one :D
        '''
        self._stop = rnd.randint(1, many or 1)

        extractions = iter(self.extract, None)
        numbers, extra = next(islice(
            extractions, self._stop, self._stop + 1))

        return numbers, extra

    def __call__(self, backend='sample', many=None):
        self.backend = backend
        self.extraction = self.Extraction(*self.many_samples(many))

        return self

    @property
    def draw(self):
        now = datetime.now().strftime("%c")

        if self.extraction.numbers is not None:
            print('Estrazione del:', now,
                  '\nNumeri Estratti:', *sorted(self.extraction.numbers))

        if self.extraction.extra is not None:
            print('Superstar:', *sorted(self.extraction.extra))


if __name__ == '__main__':
    print('Starting...')
    superenalotto = Lottery(max_numbers=90, max_extra=90,
                            len_numbers=6, len_extra=0)
    superenalotto(backend='randint', many=1_000_000).draw
    print(f'Extraction repeated {superenalotto._stop} time(s)')
