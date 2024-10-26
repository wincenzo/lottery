import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from itertools import repeat, starmap
from operator import itemgetter
from random import SystemRandom
from typing import Any, Iterable, Literal, Optional, Self


@dataclass(slots=True)
class Extraction:
    draw: Iterable[int]
    extra: Optional[Iterable[int]]


class Lottery:
    __slots__ = (
        'max_number',
        'max_extra',
        'draw_size',
        'extra_size',
        '_iterations',
        'extraction',
        '_backend',
    )

    rnd = SystemRandom()

    def __init__(self,
                 max_number: int = 90,
                 draw_size: int = 6,
                 max_extra: Optional[int] = None,
                 extra_size: Optional[int] = None,
                 ) -> None:

        self.max_number = max_number
        self.max_extra = max_extra or 0
        self.draw_size = draw_size
        self.extra_size = extra_size or 0

        self._iterations: int
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
    def choice(size: int, max_num: int) -> tuple[int, ...]:
        numbers = list(range(1, max_num+1))

        def draw():
            nonlocal max_num
            indexes = range(max_num)
            idx = Lottery.rnd.choice(indexes)
            number = numbers.pop(idx)
            max_num -= 1
            return number

        return tuple(starmap(draw, repeat((), size)))

    @staticmethod
    def sample(size: int, max_num: int) -> tuple[int, ...]:
        indexes = itemgetter(*Lottery.rnd.sample(range(max_num), k=size))
        numbers = indexes(range(1, max_num+1))

        if isinstance(numbers, tuple):
            return numbers
        else:
            return numbers,

    @staticmethod
    def randint(size: int, max_num: int) -> set[int]:
        draw = iter(lambda: Lottery.rnd.randint(1, max_num), None)

        extraction = set()
        while len(extraction) < size:
            extraction.add(next(draw))

        return extraction

    @staticmethod
    def shuffle(size: int, max_num: int) -> list[int]:
        numbers = list(range(1, max_num+1))
        Lottery.rnd.shuffle(numbers)

        start = Lottery.rnd.randint(0, max_num - size)
        max_numstep = (max_num - start) // size
        step = Lottery.rnd.randint(1, max_numstep)
        stop = start + size * step
        grab = slice(start, stop, step)

        return numbers[grab]

    def draw_once(self, size: int, max_num: int) -> Iterable[int] | None:
        return self._backend(size, max_num) if (size and max_num) else None

    def drawer(self, count: int, max_num: int) -> Any:
        """
        Adds randomness by simulating multiple draws and randomly selecting one.
        """
        with ThreadPoolExecutor() as executor:
            futures = (executor.submit(self.draw_once, count, max_num)
                       for _ in range(self._iterations))
            draws = tuple(future.result() for future in as_completed(futures))

        return draws[-1]

    def __call__(self,
                 backend: Literal['choice', 'randint', 'sample', 'shuffle'],
                 many: Optional[int] = None,
                 ) -> Self:

        self.backend = backend
        self._iterations = Lottery.rnd.randint(1, many or 1)

        draw = self.drawer(self.draw_size, self.max_number)
        extra = self.drawer(self.extra_size, self.max_extra)
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
        return (f'Lottery(max_number={self.max_number}, max_extra={self.max_extra},'
                f' draw_size={self.draw_size}, extra_size={self.extra_size})')


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
        max_number=args.numbers, draw_size=args.lenum,
        max_extra=args.extras, extra_size=args.lenex)

    print('Estraendo...')
    print(superenalotto(backend=args.backend, many=args.many),
          f'Estrazione ripetuta {superenalotto._iterations} volte',
          sep='\n', flush=True)
