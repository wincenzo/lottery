import argparse
from collections import namedtuple
from datetime import datetime
from itertools import islice, repeat, starmap
from operator import itemgetter
from random import SystemRandom
from typing import Iterable, Iterator, Literal, Optional, Self

rnd = SystemRandom()


class Lottery:

    Extraction = namedtuple(
        'Extraction', ('draw', 'extra'))

    def __init__(self,
                 max_numbers: int = 90,
                 len_draw: int = 6,
                 max_extra: int = 90,
                 len_extra: int = 1,
                 ) -> None:

        self.max_numbers = max_numbers
        self.max_extra = max_extra
        self.len_draw = len_draw
        self.len_extra = len_extra
        self.extraction = self.Extraction(None, None)
        self._stop = 1

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, name):
        match name:
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
    def choice(len_: int, max_: int) -> tuple[int, ...]:
        numbers = list(range(1, max_+1))

        def draw():
            number = rnd.choice(numbers)
            numbers.remove(number)
            return number

        return tuple(starmap(draw, repeat((), len_)))

    @staticmethod
    def sample(len_: int, max_: int) -> tuple[int, ...]:
        indexes = itemgetter(*rnd.sample(range(90), k=len_))

        return tuple(indexes(range(1, max_+1)))

    @staticmethod
    def randint(len_: int, max_: int) -> set[int]:
        draw = iter(lambda: rnd.randint(1, max_), None)

        extraction = set()
        while len_ - len(extraction):
            extraction.add(next(draw))

        return extraction

    @staticmethod
    def shuffle(len_: int, max_: int) -> list[int]:
        numbers = list(range(1, max_+1))
        rnd.shuffle(numbers)

        start = rnd.randint(0, max_-len_)
        step = (max_ - start) // len_
        stop = start + len_ * step
        grab = slice(start, stop, step)

        return numbers[grab]

    def drawer(self,
               len_: int,
               max_: int,
               ) -> Iterator[Iterable[int] | None]:

        valid = len_ and max_

        while True:
            yield self._backend(len_, max_) if valid else None

    def __call__(self,
                 backend: Literal['choice', 'randint',
                                  'sample', 'shuffle'],
                 many: Optional[int] = None) -> Self:
        '''
        To add further randomness, it simulates several extractions
        among 1 and <many> times, and picks one casually. Hopefully,
        the winning one :D
        '''
        self.backend = backend
        self._stop = rnd.randint(1, many or 1)

        extractions = zip(
            self.drawer(self.len_draw, self.max_numbers),
            self.drawer(self.len_extra, self.max_extra)
        )

        extraction = next(
            islice(extractions, self._stop, self._stop+1)
        )

        self.extraction = self.Extraction._make(extraction)

        return self

    def __str__(self) -> str:
        now = datetime.now()

        draw = ' '.join(map(str, sorted(self.extraction.draw)))
        draw = f'Estrazione del {now:%x %X} \nNumeri estratti: {draw}'

        if self.extraction.extra is not None:
            extra = ' '.join(map(str, sorted(self.extraction.extra)))
            extra = f'Superstar: {extra}'

            return f'{draw}\n{extra}'

        else:
            return f'{draw}'

    def __repr__(self) -> str:
        return (f'Lottery(max_numbers={self.max_numbers}, max_extra={self.max_extra},'
                f' len_draw={self.len_draw}, len_extra={self.len_extra})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--backend', action='store', default='sample', type=str,
                        choices=('shuffle', 'sample', 'randint', 'choice'),
                        help='select the desired backend to draw numbers')
    parser.add_argument('-m', '--many', action='store', default='100_000', type=int,
                        help='''select how many times to draw numbers before randomly 
                        choose one extraction''')

    args = parser.parse_args()

    superenalotto = Lottery(
        max_numbers=90, len_draw=6,
        max_extra=90, len_extra=0)

    print('Inizio...')
    print(superenalotto(backend=args.backend, many=args.many),
          f'Estrazione ripetuta {superenalotto._stop} volte',
          f'Backend: {args.backend}',
          sep='\n')
