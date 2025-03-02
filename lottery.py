import argparse
import random as rnd
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from itertools import islice, repeat, starmap
from operator import itemgetter
from typing import ClassVar, Final, Optional, Self

from tqdm import tqdm

from utils import DrawMethod, Extraction, validate_draw_params

MAX_NUMBERS: Final = 90
DEFAULT_DRAW_SIZE: Final = 6


class Lottery:
    BACKENDS: ClassVar[tuple[str, ...]] = (
        'choice', 'randint', 'sample', 'shuffle')

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

    def __init__(self,
                 max_num: int = MAX_NUMBERS,
                 draw_sz: int = DEFAULT_DRAW_SIZE,
                 max_ext: Optional[int] = None,
                 xtr_sz: Optional[int] = None,
                 ) -> None:

        self.max_num = max_num or MAX_NUMBERS
        self.max_ext = max_ext or 0
        self.draw_sz = draw_sz or DEFAULT_DRAW_SIZE
        self.xtr_sz = xtr_sz or 0
        self._iters: int = 0
        self.result: Extraction = Extraction(draw=())

    @cached_property
    def numbers(self) -> range:
        return range(1, self.max_num+1)

    @property
    def backend(self) -> DrawMethod:
        return self._backend

    @backend.setter
    def backend(self, name: str) -> None:
        self._backend = getattr(self, name, self.random_backend())

    def random_backend(self) -> DrawMethod:
        return getattr(self, rnd.sample(self.BACKENDS, k=1)[0])

    @staticmethod
    def randint(size: int, max_num: int) -> tuple[int, ...]:
        draw = iter(lambda: rnd.randint(1, max_num), None)

        extraction = set()
        while True:
            extraction.add(next(draw))
            if len(extraction) == size:
                break

        return tuple(extraction)

    def choice(self, size: int, max_num: int) -> tuple[int, ...]:
        numbers = list(self.numbers)

        def draw():
            nonlocal max_num
            idx = rnd.choice(range(max_num))
            number = numbers.pop(idx)
            max_num -= 1
            return number

        return tuple(starmap(draw, repeat((), size)))

    def sample(self, size: int, max_num: int) -> tuple[int, ...]:
        indexes = itemgetter(*rnd.sample(range(max_num), k=size))
        numbers = indexes(self.numbers)

        return numbers if isinstance(numbers, tuple) else (numbers,)

    def shuffle(self, size: int, *args) -> tuple[int, ...]:
        numbers = list(self.numbers)
        rnd.shuffle(numbers)
        grab = slice(None, size, None)

        return tuple(numbers[grab])

    def draw_once(self, size: int, max_num: int) -> tuple[int, ...]:
        self.backend = self.init_backend
        return self.backend(size, max_num)

    @validate_draw_params
    def drawer(self, size: int, max_num: int) -> tuple[int, ...]:
        """
        Adds randomness by simulating multiple draws and grabbing last one.
        """
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.draw_once, size, max_num)
                for _ in tqdm(range(self._iters),
                              desc=f"Drawing ...",
                              unit="draws",
                              ncols=80,
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
            ]

            draw, = islice(as_completed(futures), self._iters-1, None)

            return draw.result()

    @contextmanager
    def drawing_session(self):
        """
        Context manager for drawing session.
        """
        try:
            draw = self.drawer(self.draw_sz, self.max_num)
            get_extra = all((self.xtr_sz, self.max_ext))
            extra = self.drawer(
                self.xtr_sz, self.max_ext) if get_extra else self.result.extra

            yield draw, extra

        except Exception as e:
            print(f'Error: {e}')

        finally:
            del draw, extra

    def __call__(self, backend: str, many: Optional[int] = None) -> Self:
        self.init_backend = backend
        self._iters = many or rnd.randrange(1, 100_001)

        with self.drawing_session() as results:
            self.result.draw, self.result.extra = results

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
    parser.add_argument('-n', '--numbers', action='store', default=MAX_NUMBERS, type=int,
                        help='select upper limit for numbers')
    parser.add_argument('-e', '--extras', action='store', default=MAX_NUMBERS, type=int,
                        help='select upper limit for extras')
    parser.add_argument('--numsz', action='store', default=DEFAULT_DRAW_SIZE, type=int,
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
