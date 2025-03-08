import argparse
import random as rnd
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from itertools import compress, repeat, starmap
from operator import itemgetter
from typing import ClassVar, Final, Iterable, Iterator, Optional, Self

from tqdm import tqdm

from utils import DrawMethod, Extraction, validate_draw_params

MAX_NUMBERS: Final = 90
DEFAULT_DRAW_SIZE: Final = 6
MAX_DRAW_ITERS: Final = 100_000


class Lottery:
    BACKENDS: ClassVar[tuple[str, ...]] = (
        'choice', 'randint', 'randrange', 'sample', 'shuffle')

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

        self.max_num: int = max_num or MAX_NUMBERS
        self.max_ext: int = max_ext or 0
        self.draw_sz: int = draw_sz or DEFAULT_DRAW_SIZE
        self.xtr_sz: int = xtr_sz or 0
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
        match name:
            case 'choice' | 'randint' | 'randrange' | 'sample' | 'shuffle':
                self._backend = getattr(self, name)
            case _:
                self._backend = self.random_backend()

    def random_backend(self) -> DrawMethod:
        return getattr(self, rnd.choice(self.BACKENDS))

    @staticmethod
    def randint(size: int, max_num: int) -> set[int]:
        draw = iter(lambda: rnd.randint(1, max_num), None)

        extraction = {next(draw)}
        while len(extraction) < size:
            extraction.add(next(draw))

        return extraction

    @staticmethod
    def randrange(size: int, max_num: int) -> set[int]:
        def draw() -> Iterator[int]:
            for _ in repeat(None):
                yield rnd.randrange(1, max_num+1)

        extraction = set()
        for number in draw():
            extraction.add(number)
            if len(extraction) == size:
                break

        return extraction

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

    def shuffle(self, size: int, *args) -> list[int]:
        numbers = list(self.numbers)
        rnd.shuffle(numbers)
        start = rnd.randint(0, self.max_num-size)
        stop = start + size
        grab = slice(start, stop, None)

        return numbers[grab]

    def draw_once(self, size: int, max_num: int) -> Iterable[int]:
        self.backend = self.init_backend

        return self.backend(size, max_num)

    @validate_draw_params
    def drawer(self, size: int, max_num: int) -> Iterable[int]:
        """
        Adds randomness by simulating multiple draws.
        """
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.draw_once, size, max_num)
                for _ in tqdm(range(self._iters),
                              desc=f"Estraendo ...",
                              unit="estrazioni",
                              ncols=80,
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
            ]

            def selections(length: int) -> Iterator[int]: 
                yield from (1 if rnd.random() > 0.5 else 0 for _ in range(length))

            draws = [f.result() for f in as_completed(futures)]

            while (length := len(draws)) >= 10:
                draws = tuple(compress(draws, selections(length)))

            return rnd.choice(draws)

    @contextmanager
    def drawing_session(self):
        try:
            draw = self.drawer(self.draw_sz, self.max_num)
            get_extra = all((self.xtr_sz, self.max_ext))
            extra = self.drawer(
                self.xtr_sz, self.max_ext) if get_extra else self.result.extra
            yield draw, extra
        except Exception as e:
            print(f'Error: {e}')
            raise
        finally:
            self._iters = 0

            try:
                del draw, extra
            except UnboundLocalError:
                pass

    def __call__(self, backend: str, many: Optional[int] = None) -> Self:
        self.init_backend = backend
        self._iters = many or rnd.randint(1, MAX_DRAW_ITERS)

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
            'Scegli il backend (choice, randint, randrange, sample, shuffle): ')

        print(superenalotto(backend=backend, many=args.many))

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
