import argparse
from dataclasses import dataclass
from datetime import datetime
from itertools import islice, repeat, starmap
from operator import itemgetter
from random import SystemRandom
from typing import Any, Iterable, Literal, Optional, Self

from joblib import Parallel, delayed

rnd = SystemRandom()


@dataclass(slots=True)
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
        '_backend',
    )

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

        self._stop: int
        self.extraction: Extraction

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
    def choice(_len: int, _max: int) -> tuple[int, ...]:
        numbers = list(range(1, _max+1))

        def draw():
            nonlocal _max
            indexes = range(_max)
            idx = rnd.choice(indexes)
            number = numbers.pop(idx)
            _max -= 1
            return number

        return tuple(starmap(draw, repeat((), _len)))

    @staticmethod
    def sample(_len: int, _max: int) -> tuple[int, ...]:
        indexes = itemgetter(*rnd.sample(range(_max), k=_len))
        numbers = indexes(range(1, _max+1))

        if isinstance(numbers, tuple):
            return numbers
        else:
            return numbers,

    @staticmethod
    def randint(_len: int, _max: int) -> set[int]:
        draw = iter(lambda: rnd.randint(1, _max), None)

        extraction = set()
        while _len - len(extraction):
            extraction.add(next(draw))

        return extraction

    @staticmethod
    def shuffle(_len: int, _max: int) -> list[int]:
        numbers = list(range(1, _max+1))
        rnd.shuffle(numbers)

        start = rnd.randint(0, _max - _len)
        _maxstep = (_max - start) // _len
        step = rnd.randint(1, _maxstep)
        stop = start + _len * step
        grab = slice(start, stop, step)

        return numbers[grab]

    def one_draw(self, _len: int, _max: int) -> Iterable[int] | None:
        return self._backend(_len, _max) if (_len and _max) else None

    def drawer(self, _len: int, _max: int) -> Any:
        '''
        To add further randomness, it simulates several extractions
        among 1 and <many> times, and picks one casually. Hopefully,
        the winning one :D
        '''
        with Parallel(n_jobs=-1,
                      prefer='threads',
                      return_as='generator_unordered',
                      ) as parallel:
            draws = parallel(delayed(
                self.one_draw)(_len, _max) for _ in range(self._stop))

            return next(islice(draws, self._stop - 1, None))

    def __call__(self,
                 backend: Literal['choice', 'randint', 'sample', 'shuffle'],
                 many: Optional[int] = None,
                 ) -> Self:

        self.backend = backend
        self._stop = rnd.randint(1, many or 1)

        draw = self.drawer(self.len_draw, self.max_numbers)
        extra = self.drawer(self.len_extra, self.max_extra)
        self.extraction = Extraction(draw, extra)

        return self

    def __str__(self) -> str:
        now = datetime.now()
        draw = ' '.join(map(str, sorted(self.extraction.draw)))
        result = f'Estrazione del {now:%x %X}\nNumeri estratti: {draw}'

        if self.extraction.extra:
            extra = ' '.join(map(str, sorted(self.extraction.extra)))
            result += f'\nSuperstar: {extra}'

        return result

    def __repr__(self) -> str:
        return (f'Lottery(max_numbers={self.max_numbers}, max_extra={self.max_extra},'
                f' len_draw={self.len_draw}, len_extra={self.len_extra})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-b', '--backend', action='store', default=None, type=str,
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
    parser.add_argument('--lenex', action='store', default=0, type=int,
                        help='select how many extra numbers to draw')

    args = parser.parse_args()

    superenalotto = Lottery(
        max_numbers=args.numbers, len_draw=args.lenum,
        max_extra=args.extras, len_extra=args.lenex)

    print(f'{datetime.now():%x %X} - Estraendo...')
    print(superenalotto(backend=args.backend, many=args.many),
          f'Estrazione ripetuta {superenalotto._stop} volte',
          sep='\n', flush=True)
