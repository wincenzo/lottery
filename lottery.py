import argparse
import locale
import random as rnd
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from itertools import compress, repeat, starmap
from operator import itemgetter
from pathlib import Path
from typing import ClassVar, Iterable, Iterator, Optional, Self

from tqdm import tqdm

from utils import Config, DrawMethod, Extraction, validate_draw_params

locale.setlocale(locale.LC_ALL, locale='it_IT')


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
                 max_num: int = 90,
                 draw_sz: int = 6,
                 max_ext: int = 90,
                 xtr_sz: int = 1,
                 from_config: Optional[Path | str] = None
                 ) -> None:

        self.CONFIG: Config = Config.load_config(
            from_config) if from_config else Config()
        self.max_num: int = self.CONFIG.max_numbers or max_num 
        self.draw_sz: int = self.CONFIG.draw_size or draw_sz
        self.max_ext: int = self.CONFIG.max_ext or max_ext
        self.xtr_sz: int = self.CONFIG.xtr_sz or xtr_sz
        self._iters: int = 1
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
    def randrange(size: int, max_num: int) -> set[int]:
        draw = iter(lambda: rnd.randrange(1, max_num+1), None)

        extraction = set()
        for number in draw:
            extraction.add(number)
            if len(extraction) == size:
                break

        return extraction

    @staticmethod
    def randint(size: int, max_num: int) -> set[int]:
        def draw() -> Iterator[int]:
            for _ in repeat(None):
                yield rnd.randint(1, max_num)

        extraction = {next(draw())}
        while len(extraction) < size:
            extraction.add(next(draw()))

        return extraction

    def choice(self, size: int, max_num: int) -> tuple[int, ...]:
        numbers = list(self.numbers)

        def draw():
            nonlocal max_num
            number = numbers.pop(rnd.choice(range(max_num)))
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
            futures = (
                executor.submit(self.draw_once, size, max_num)
                for _ in tqdm(range(self._iters),
                              desc=f"Estraendo ...",
                              unit="estrazioni",
                              ncols=80,
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
            )

            def selections(length: int) -> Iterator[int]:
                yield from (
                    1 if rnd.random() > 0.5 else 0 for _ in repeat(None, length))

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
        self._iters = many or rnd.randint(
            1, self.CONFIG.max_draw_iters or self._iters)

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
    parser.add_argument('-n', '--numbers', action='store', type=int,
                        help='select upper limit for numbers')
    parser.add_argument('-e', '--extras', action='store', type=int,
                        help='select upper limit for extras')
    parser.add_argument('--numsz', action='store', type=int,
                        help='select how many numbers to draw')
    parser.add_argument('--xtrsz', action='store', default=0, type=int,
                        help='select how many extra numbers to draw')
    parser.add_argument('-c', '--config', action='store', default=Path('config.toml'), type=str,
                        help='path to config file')

    args = parser.parse_args()

    try:
        superenalotto = Lottery(
            max_num=args.numbers, draw_sz=args.numsz,
            max_ext=args.extras, xtr_sz=args.xtrsz,
            from_config=args.config
        )

        backend = input(
            'Scegli il backend (choice, randint, randrange, sample, shuffle): ')

        print(superenalotto(backend=backend, many=args.many))

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
