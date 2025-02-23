import argparse
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property, lru_cache
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
        'ext_sz',
        '_iters',
        'result',
        '_method',
    )

    rnd = SystemRandom()

    def __init__(self,
                 max_num: int = MAX_NUMBERS,
                 draw_sz: int = DEFAULT_DRAW_SIZE,
                 max_ext: Optional[int] = None,
                 ext_sz: Optional[int] = None,
                 ) -> None:

        self.max_num = max_num or self.MAX_NUMBERS
        self.max_ext = max_ext or 0
        self.draw_sz = draw_sz or self.DEFAULT_DRAW_SIZE
        self.ext_sz = ext_sz or 0
        self._iters: int = 0
        self.result: Extraction = Extraction((), None)

    @cached_property
    def default(self) -> DrawMethod:
        def_bcknd, = self.rnd.sample(self.BACKENDS, k=1)
        return getattr(self, def_bcknd)

    @property
    def method(self) -> DrawMethod:
        return self._method

    @method.setter
    def method(self, name: str) -> None:
        if not self.is_valid_backend(name):
            self._method = self.default
        self._method = cast(DrawMethod, getattr(self, name))

    @staticmethod
    def is_valid_backend(name: str) -> TypeGuard[str]:
        return name in Lottery.BACKENDS

    @contextmanager
    def drawing_session(self):
        """Context manager for drawing session."""
        try:
            yield self
        finally:
            self._iters = 0
            self.result = Extraction((), None)

    @lru_cache(maxsize=128)
    def get_number_range(self, max_num: int) -> list[int]:
        return list(range(1, max_num + 1))

    @validate_draw_params
    def choice(self, size: int, max_num: int) -> tuple[int, ...]:
        numbers = self.get_number_range(max_num)

        def draw():
            nonlocal max_num
            idx = self.rnd.randrange(max_num)
            number = numbers.pop(idx)
            max_num -= 1
            return number

        return tuple(starmap(draw, repeat((), size)))

    @validate_draw_params
    def sample(self, size: int, max_num: int) -> tuple[int, ...]:
        indexes = itemgetter(*self.rnd.sample(range(max_num), k=size))
        numbers = indexes(self.get_number_range(max_num))

        if isinstance(numbers, tuple):
            return numbers
        else:
            return (numbers,)

    @validate_draw_params
    def randint(self, size: int, max_num: int) -> tuple[int, ...]:
        draw = iter(lambda: self.rnd.randint(1, max_num), None)
        extraction = set()
        while True:
            extraction.add(next(draw))
            if len(extraction) == size:
                break

        return tuple(extraction)

    @validate_draw_params
    def shuffle(self, size: int, max_num: int) -> tuple[int, ...]:
        numbers = self.get_number_range(max_num)
        self.rnd.shuffle(numbers)

        start = Lottery.rnd.randint(0, max_num-size)
        max_numstep = (max_num - start) // size
        step = Lottery.rnd.randint(1, max_numstep)
        stop = start + size * step
        grab = slice(start, stop, step)

        return tuple(numbers[grab])

    def draw_once(self, size: int, max_num: int) -> tuple[int, ...]:
        return self.method(size, max_num) if all((size, max_num)) else ()

    async def drawer(self, size: int, max_num: int) -> tuple[int, ...]:
        """Adds randomness by simulating multiple draws and grabbing last one."""
        loop = asyncio.get_event_loop()

        with ThreadPoolExecutor() as executor:
            futures = [
                loop.run_in_executor(executor, self.draw_once, size, max_num)
                for _ in tqdm(range(self._iters),
                              desc=f"Backend: {self._method.__name__} ...",
                              unit="draws")
            ]
            completed = await asyncio.gather(*futures)

        return next(islice(completed, self._iters-1, None))

    def __call__(self, method: str, many: Optional[int] = None) -> Self:
        with self.drawing_session():
            self.method = method
            self._iters = self.rnd.randint(1, many or 1)

            draw = asyncio.run(self.drawer(self.draw_sz, self.max_num))
            extra = asyncio.run(self.drawer(
                self.ext_sz, self.max_ext)) if self.ext_sz else ()

            self.result = Extraction(draw, extra)

            return self

    def __str__(self) -> str:
        now = datetime.now()
        draw = ' '.join(map(str, self.result.draw))
        result = f'\nEstrazione del {now:%x %X}\nNumeri estratti: {draw}'

        if self.result.extra:
            extra = ' '.join(map(str, self.result.extra))
            result += f'\nSuperstar: {extra}'

        return result

    def __repr__(self) -> str:
        return (f'Lottery(max_num={self.max_num}, max_ext={self.max_ext},'
                f' draw_sz={self.draw_sz}, ext_sz={self.ext_sz})')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Lottery number generator')

    parser.add_argument('-m', '--many', action='store', default=100_000, type=int,
                        help='select how many times to draw')
    parser.add_argument('-n', '--numbers', action='store', default=90, type=int,
                        help='select upper limit for numbers')
    parser.add_argument('-e', '--extras', action='store', default=90, type=int,
                        help='select upper limit for extras')
    parser.add_argument('--nsz', action='store', default=6, type=int,
                        help='select how many numbers to draw')
    parser.add_argument('--esz', action='store', default=0, type=int,
                        help='select how many extra numbers to draw')

    args = parser.parse_args()

    try:
        superenalotto = Lottery(
            max_num=args.numbers, draw_sz=args.nsize,
            max_ext=args.extras, ext_sz=args.esize
        )

        method = input(
            'Scegli il backend (choice, randint, sample, shuffle): ')
        print(superenalotto(method=method, many=args.many))

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
