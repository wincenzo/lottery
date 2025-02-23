import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from itertools import islice, repeat, starmap
from operator import itemgetter
from random import SystemRandom
from typing import ClassVar, Final, Optional, Self, TypeGuard, cast

from tqdm import tqdm

from utils import DrawMethod, Extraction, validate_draw_params


class Lottery:
    BACKENDS: ClassVar[tuple[str, ...]] = (
        'choice', 'randint', 'sample', 'shuffle')
    MAX_NUMBERS: Final = 90
    DEFAULT_DRAW_SIZE: Final = 6

    __slots__ = (
        'max_num',
        'max_ext',
        'draw_sz',
        'xtr_sz',
        'result',
        '_iters',
        '_backend',
        '__dict__',
    )

    rnd = SystemRandom()

    def __init__(self,
                 max_num: int = MAX_NUMBERS,
                 draw_sz: int = DEFAULT_DRAW_SIZE,
                 max_ext: Optional[int] = None,
                 xtr_sz: Optional[int] = None,
                 ) -> None:

        self.max_num = max_num or self.MAX_NUMBERS
        self.max_ext = max_ext or 0
        self.draw_sz = draw_sz or self.DEFAULT_DRAW_SIZE
        self.xtr_sz = xtr_sz or 0
        self._iters: int = 0
        self.result: Extraction = Extraction((), None)

    @property
    def default_backend(self) -> DrawMethod:
        bcknd = self.rnd.sample(self.BACKENDS, k=1)[0]
        return getattr(self, bcknd)

    @property
    def backend(self) -> DrawMethod:
        return self._backend

    @backend.setter
    def backend(self, name: str) -> None:
        if self.is_valid_backend(name):
            self._backend = cast(DrawMethod, getattr(self, name))
        else:
            self._backend = self.default_backend

    @staticmethod
    def is_valid_backend(name: str) -> TypeGuard[str]:
        return name in Lottery.BACKENDS

    def get_numbers(self, max_num) -> list[int]:
        return list(range(1, max_num+1))

    def choice(self, size: int, max_num: int) -> tuple[int, ...]:
        numbers = self.get_numbers(max_num)

        def draw():
            nonlocal max_num
            idx = self.rnd.choice(range(max_num))
            number = numbers.pop(idx)
            max_num -= 1
            return number

        return tuple(starmap(draw, repeat((), size)))

    def sample(self, size: int, max_num: int) -> tuple[int, ...]:
        indexes = itemgetter(*self.rnd.sample(range(max_num), k=size))
        numbers = indexes(self.get_numbers(max_num))

        return numbers if isinstance(numbers, tuple) else (numbers,)

    def randint(self, size: int, max_num: int) -> tuple[int, ...]:
        draw = iter(lambda: self.rnd.randint(1, max_num), None)

        extraction = set()
        while True:
            extraction.add(next(draw))
            if len(extraction) == size:
                break

        return tuple(extraction)

    def shuffle(self, size: int, max_num: int) -> tuple[int, ...]:
        numbers = self.get_numbers(max_num)
        self.rnd.shuffle(numbers)
        grab = slice(None, size, None)

        return tuple(numbers[grab])

    def draw_once(self, size: int, max_num: int) -> tuple[int, ...]:
        return self.backend(size, max_num) if all((size, max_num)) else ()

    @validate_draw_params
    def drawer(self, size: int, max_num: int) -> tuple[int, ...]:
        """
        Adds randomness by simulating multiple draws and grabbing last one.
        """
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.draw_once, size, max_num)
                for _ in tqdm(range(self._iters),
                              desc=f"Backend: {self.backend.__name__} ...",
                              unit="draws",
                              ncols=80,
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
            ]

            draw = next(islice(as_completed(futures), self._iters-1, None))

            return draw.result()

    @contextmanager
    def drawing_session(self):
        """
        Context manager for drawing session.
        """
        draw = self.drawer(self.draw_sz, self.max_num)
        extra = self.drawer(self.xtr_sz, self.max_ext) if self.xtr_sz else ()
        results = Extraction(draw, extra)

        try:
            yield results

        finally:
            del draw, extra

    def __call__(self, backend: str, many: Optional[int] = None) -> Self:
        self.backend = backend
        self._iters = many or self.rnd.randint(1, 100_000)

        with self.drawing_session() as results:
            self.result = results

            return self

    def __str__(self) -> str:
        now = datetime.now()
        draw = ' '.join(map(str, sorted(self.result.draw)))
        result = f'\nEstrazione del {now:%x %X}\nNumeri estratti: {draw}'

        if self.result.extra:
            extra = ' '.join(map(str, sorted(self.result.extra)))
            result += f'\nSuperstar: {extra}'

        return result

    def __repr__(self) -> str:
        return (f'Lottery(max_num={self.max_num}, max_ext={self.max_ext},'
                f' draw_sz={self.draw_sz}, xtr_sz={self.xtr_sz})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lottery number generator')

    parser.add_argument('-m', '--many', action='store', default=None, type=int,
                        help='select how many times to draw')
    parser.add_argument('-n', '--numbers', action='store', default=90, type=int,
                        help='select upper limit for numbers')
    parser.add_argument('-e', '--extras', action='store', default=90, type=int,
                        help='select upper limit for extras')
    parser.add_argument('--numsz', action='store', default=6, type=int,
                        help='select how many numbers to draw')
    parser.add_argument('--xtrsz', action='store', default=0, type=int,
                        help='select how many extra numbers to draw')

    args = parser.parse_args()

    try:
        superenalotto = Lottery(
            max_num=args.numbers, draw_sz=args.numsz,
            max_ext=args.extras, xtr_sz=args.xtrsz
        )

        backend = input(
            'Scegli il backend (choice, randint, sample, shuffle): ')
        print(superenalotto(backend=backend, many=args.many))

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
