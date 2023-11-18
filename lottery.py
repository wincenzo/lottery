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
                 len_numbers=6,
                 max_extra=90,
                 len_extra=1
                 ):
        self.max_numbers = max_numbers
        self.max_extra = max_extra
        self.len_numbers = len_numbers
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
        if not (len_ and max_):
            return None

        numbers = list(range(1, max_ + 1))

        def get_number():
            number = rnd.choice(numbers)
            numbers.remove(number)
            return number

        return frozenset(starmap(
            get_number, repeat((), len_)))

    @staticmethod
    def sample(len_, max_):
        if not (len_ and max_):
            return None

        all_numbers = tuple(range(1, max_ + 1))

        return frozenset(rnd.sample(all_numbers, k=len_))

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

    @staticmethod
    def shuffle(len_, max_):
        if not (len_ and max_):
            return None

        all_numbers = list(range(1, max_ + 1))
        rnd.shuffle(all_numbers)

        return frozenset(all_numbers[:len_])

    def draw(self, len_, max_):
        while True:
            yield self._backend(len_, max_)

    def __call__(self, backend=None, many=None):
        '''
        To add further randomness, it simulates several extractions,
        and picks one casually among 1 and <many> times. Hopefully,
        the winning one :D
        '''
        self.backend = backend
        self.stop = rnd.randint(1, many or 1)

        extractions = zip(
            self.draw(self.len_numbers, self.max_numbers),
            self.draw(self.len_extra, self.max_extra))

        numbers, extra = next(islice(
            extractions, self.stop, self.stop + 1))

        self.extraction = self.Extraction(numbers, extra)

        return self

    def __str__(self):
        now = datetime.now().strftime("%c")

        numbers, extra = self.extraction

        numbers = ' '.join(map(str, sorted(numbers)))
        numbers = f'Estrazione del {now} \nNumeri estratti: {numbers}'

        if extra is not None:
            extra = ' '.join(map(str, sorted(extra)))
            extra = f'Superstar: {extra}'

            return f'{numbers}\n{extra}'

        else:
            return f'{numbers}'


if __name__ == '__main__':
    superenalotto = Lottery(
        max_numbers=90, len_numbers=6,
        max_extra=90, len_extra=1)

    print('Inizio...')
    print(superenalotto(backend='sample', many=1_000_000))
    print(f'Estrazione ripetuta {superenalotto.stop} volte')
