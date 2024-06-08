import argparse
from dataclasses import dataclass
from datetime import datetime
from itertools import islice, repeat, starmap
from operator import itemgetter
from random import SystemRandom
from typing import Any, Iterable, Literal, Optional, Self

from joblib import Parallel, delayed

rnd = SystemRandom()


@dataclass
class Extraction:
    draw: Iterable[int]
    extra: Optional[Iterable[int]]


class Lottery:
    __slots__ = (
        'max_numbers',
        'max_extra',
        'len_draw',
        'len_extra',
        '_stop',
        'extraction',
        '_backend')

    def __init__(self,
                 max_numbers: int = 90,
                 len_draw: int = 6,
                 max_extra: Optional[int] = None,
                 len_extra: Optional[int] = None,
                 ) -> None:

        self.max_numbers = max_numbers
        self.max_extra = max_extra or 0
        self.len_draw = len_draw
        self.len_extra = len_extra or 0
        self._stop = 0

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
        numbers = indexes(range(1, max_+1))

        if isinstance(numbers, tuple):
            return numbers
        else:
            return numbers,

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
        max_step = (max_ - start) // len_
        step = rnd.randint(1, max_step)
        stop = start + len_ * step
        grab = slice(start, stop, step)

        return numbers[grab]

    def one_draw(self, len_: int, max_: int) -> Iterable[int] | None:
        return self._backend(len_, max_) if (len_ and max_) else None

    def drawer(self, len_: int, max_: int) -> Any:
        '''
        To add further randomness, it simulates several extractions
        among 1 and <many> times, and picks one casually. Hopefully,
        the winning one :D
        '''
        parallel = Parallel(return_as='generator_unordered', prefer='threads')
        draws = parallel(delayed(self.one_draw)(len_, max_)
                         for _ in range(self._stop))

        return draws

    def __call__(self,
                 backend: Literal['choice', 'randint', 'sample', 'shuffle'],
                 many: Optional[int] = None,
                 ) -> Self:

        self.backend = backend
        self._stop = rnd.randint(1, many or 1)

        extractions = zip(
            self.drawer(self.len_draw, self.max_numbers),
            self.drawer(self.len_extra, self.max_extra)
        )

        extraction = next(islice(extractions, self._stop-1, self._stop))
        self.extraction = Extraction(*extraction)

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
    parser.add_argument('-m', '--many', action='store', default=100_000, type=int,
                        help='''select how many times to draw before randomly 
                        choose one extraction''')
    parser.add_argument('-n', '--numbers', action='store', default=90, type=int,
                        help='select upper linit for numbers')
    parser.add_argument('-e', '--extras', action='store', default=90, type=int,
                        help='select upper limit for extras')
    parser.add_argument('--lenum', action='store', default=6, type=int,
                        help='select how many numbers to draw')
    parser.add_argument('--lenex', action='store', default=None, type=int,
                        help='select how many extra numbers to draw')

    args = parser.parse_args()

    superenalotto = Lottery(
        max_numbers=args.numbers, len_draw=args.lenum,
        max_extra=args.extras, len_extra=args.lenex)

    print('Estraendo...')
    print(superenalotto(backend=args.backend, many=args.many),
          f'Estrazione ripetuta {superenalotto._stop} volte',
          f'Backend: {superenalotto.backend}', sep='\n', flush=True)
