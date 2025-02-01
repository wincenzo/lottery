import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from itertools import islice, repeat, starmap
from operator import itemgetter
from random import SystemRandom
from typing import Iterable, Optional, Self

from tqdm import tqdm


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
        'backends',
        '_backend',
    )

    rnd = SystemRandom()

    def __init__(self,
                 max_number: int = 90,
                 draw_size: int = 6,
                 max_extra: Optional[int] = None,
                 extra_size: Optional[int] = None,
                 ) -> None:

        self.max_number = max_number or 90
        self.max_extra = max_extra or 0
        self.draw_size = draw_size or 6
        self.extra_size = extra_size or 0
        self._iterations: int = 0
        self.extraction: Extraction = Extraction([], None)
        self.backends = ('choice', 'randint', 'sample', 'shuffle')

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, name: str):
        name = (name if name in self.backends
                else Lottery.rnd.sample(self.backends, 1)[-1])

        match name:
            case 'choice':
                self._backend = self.choice
            case 'randint':
                self._backend = self.randint
            case 'sample':
                self._backend = self.sample
            case 'shuffle':
                self._backend = self.shuffle
            case _:
                raise ValueError('not a valid backend')

        self.backend.name = name

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

        start = Lottery.rnd.randint(0, max_num-size)
        max_numstep = (max_num - start) // size
        step = Lottery.rnd.randint(1, max_numstep)
        stop = start + size * step
        grab = slice(start, stop, step)

        return numbers[grab]

    def draw_once(self, size: int, max_num: int) -> Iterable[int]:
        return self.backend(size, max_num) if all((size, max_num)) else ()

    def drawer(self, size: int, max_num: int) -> Iterable[int]:
        """
        Adds randomness by simulating multiple draws and grabbing last one.
        """
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.draw_once, size, max_num)
                for _ in tqdm(range(self._iterations),
                              desc="Estraendo ...",
                              unit="draws",
                              ncols=80,
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
            ]

        draw = next(islice(as_completed(futures), self._iterations-1, None))

        return draw.result()

    def __call__(self, backend: str, many: Optional[int] = None) -> Self:
        self.backend = backend
        self._iterations = Lottery.rnd.randint(1, many or 1)

        draw = self.drawer(self.draw_size, self.max_number)
        extra = self.drawer(
            self.extra_size, self.max_extra) if self.extra_size else None

        self.extraction = Extraction(sorted(draw), sorted(extra or []))

        print(f"Totale estrazioni: {self._iterations:,}",
              f"Backend: {self.backend.name}",
              sep="\n", end="\n")

        return self

    def __str__(self) -> str:
        now = datetime.now()
        draw = ' '.join(map(str, self.extraction.draw))
        result = f'\nEstrazione del {now:%x %X}\nNumeri estratti: {draw}'

        if self.extraction.extra:
            extra = ' '.join(map(str, self.extraction.extra))
            result += f'\nSuperstar: {extra}'

        return result

    def __repr__(self) -> str:
        return (f'Lottery(max_number={self.max_number}, max_extra={self.max_extra},'
                f' draw_size={self.draw_size}, extra_size={self.extra_size})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-m', '--many', action='store', default=100_000, type=int,
                        help='''select how many times to draw before randomly 
                        choose one extraction''')
    parser.add_argument('-n', '--numbers', action='store', default=90, type=int,
                        help='select upper limit for numbers')
    parser.add_argument('-e', '--extras', action='store', default=90, type=int,
                        help='select upper limit for extras')
    parser.add_argument('--nsize', action='store', default=6, type=int,
                        help='select how many numbers to draw')
    parser.add_argument('--esize', action='store', default=0, type=int,
                        help='select how many extra numbers to draw')

    args = parser.parse_args()

    try:
        superenalotto = Lottery(
            max_number=args.numbers, draw_size=args.nsize,
            max_extra=args.extras, extra_size=args.esize
        )

        backend = input(
            'Scegli il backend (choice, randint, sample, shuffle): ') 

        print(superenalotto(backend=backend, many=args.many))  

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
