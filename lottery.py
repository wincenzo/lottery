from collections import namedtuple
from datetime import datetime
from itertools import islice, repeat, starmap
from random import SystemRandom

rnd = SystemRandom()


class Lottery:
    Extraction = namedtuple(
        'Extraction', ('numbers', 'extra'))

    def __init__(self,
                 max_numbers=90,
                 len_draw=6,
                 max_extra=90,
                 len_extra=1,
                 ):
        self.max_numbers = max_numbers
        self.max_extra = max_extra
        self.len_draw = len_draw
        self.len_extra = len_extra
        self.extraction = self.Extraction(None, None)
        self.backend = None
        self.stop = None

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
            case 'shuffle':
                self._backend = self.shuffle
            case _:
                raise ValueError('not a valid backend')

    @backend.getter
    def backend(self):
        return self._backend.__name__

    @staticmethod
    def choice(len_, max_):
        numbers = list(range(1, max_ + 1))

        def get_number():
            number = rnd.choice(numbers)
            numbers.remove(number)
            return number

        return frozenset(starmap(
            get_number, repeat((), len_)))

    @staticmethod
    def sample(len_, max_):
        numbers = tuple(range(1, max_ + 1))

        return frozenset(rnd.sample(numbers, k=len_))

    @staticmethod
    def randint(len_, max_):
        draw = iter(lambda: rnd.randint(1, max_), None)

        extraction = set()
        while len_ - len(extraction):
            number = next(draw)
            extraction.add(number)

        return frozenset(extraction)

    @staticmethod
    def shuffle(len_, max_):
        numbers = list(range(1, max_ + 1))
        rnd.shuffle(numbers)

        return frozenset(numbers[:len_])

    def drawer(self, len_, max_):
        while True:
            if len_ and max_:
                yield self._backend(len_, max_)
            else:
                yield None

    def __call__(self, backend=None, many=None):
        '''
        To add further randomness, it simulates several extractions,
        and picks one casually among 1 and <many> times. Hopefully,
        the winning one :D
        '''
        self.backend = backend
        self.stop = rnd.randint(1, many or 1)

        extractions = zip(
            self.drawer(self.len_draw, self.max_numbers),
            self.drawer(self.len_extra, self.max_extra))

        draw, extra = next(islice(
            extractions, self.stop, self.stop + 1))

        self.extraction = self.Extraction(draw, extra)

        return self

    def __str__(self):
        now = datetime.now().strftime("%c")

        draw, extra = self.extraction

        draw = ' '.join(map(str, sorted(draw)))
        draw = f'Estrazione del {now} \nNumeri estratti: {draw}'

        if extra is not None:
            extra = ' '.join(map(str, sorted(extra)))
            extra = f'Superstar: {extra}'

            return f'{draw}\n{extra}'

        else:
            return f'{draw}'


if __name__ == '__main__':
    superenalotto = Lottery(
        max_numbers=90, len_draw=6,
        max_extra=90, len_extra=1)

    print('Inizio...')
    print(superenalotto(backend='sample', many=1_000_000))
    print(f'Estrazione ripetuta {superenalotto.stop} volte')
