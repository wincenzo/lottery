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
        'choice',
        'randint',
        'randrange',
        'sample',
        'shuffle',
    )

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
                 max_num: Optional[int] = None,
                 draw_sz: Optional[int] = None,
                 max_ext: Optional[int] = None,
                 xtr_sz: Optional[int] = None,
                 config_path: Optional[Path | str] = None,
                 user_nums: Optional[list[int]] = None) -> None:

        self.CONFIG: Config = (
            Config.load_config(config_path) if config_path else Config())
        self.user_nums: list[int] = user_nums or self.CONFIG.user_nums
        self.max_num: int = max_num or self.CONFIG.max_num
        self.draw_sz: int = (draw_sz or self.CONFIG.draw_sz)
        self.max_ext: int = max_ext or self.CONFIG.max_ext
        self.xtr_sz: int = xtr_sz or self.CONFIG.xtr_sz
        self._iters: int = 1
        self._size: int = self.draw_sz - len(self.user_nums)
        self.result: Extraction = Extraction(draw=set())

    @cached_property
    def numbers(self) -> list[int]:
        return [n for n in range(1, self.max_num+1) if n not in self.user_nums]

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

    def randrange(self, size: int, max_num: int) -> set[int]:
        draw = iter(lambda: rnd.randrange(1, max_num+1), None)

        extraction = set(self.user_nums)
        for number in draw:
            extraction.add(number)
            if len(extraction) == size:
                break

        return extraction

    def randint(self, size: int, max_num: int) -> set[int]:
        def draw() -> Iterator[int]:
            for _ in repeat(None):
                yield rnd.randint(1, max_num)

        extraction = {*self.user_nums}
        while len(extraction) < size:
            extraction.add(next(draw()))

        return extraction

    def choice(self, *args) -> tuple[int, ...]:
        numbers = self.numbers.copy()
        n_items = len(numbers)

        def draw():
            nonlocal n_items
            number = numbers.pop(rnd.choice(range(n_items)))
            n_items -= 1
            return number

        return tuple(starmap(draw, repeat((), self._size)))

    def sample(self, *args) -> tuple[int, ...]:
        indexes = itemgetter(
            *rnd.sample(range(len(self.numbers)), k=self._size))
        numbers = indexes(self.numbers)

        return numbers if isinstance(numbers, tuple) else (numbers,)

    def shuffle(self, *args) -> list[int]:
        numbers = self.numbers
        rnd.shuffle(numbers)
        start = rnd.randint(0, len(self.numbers)-self._size)
        stop = start + self._size
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
                              desc="Estraendo ...",
                              unit="estrazioni",
                              ncols=80,
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
            )

            def selections(length: int) -> Iterator[int]:
                yield from (
                    1 if rnd.random() > 0.5 else 0 for _ in repeat(None, length))

            draws = [f.result() for f in as_completed(futures)]

            while (length := len(draws)) >= 10:
                draws = list(compress(draws, selections(length)))
            else:
                return rnd.choice(draws)

    @contextmanager
    def drawing_session(self):
        try:
            draw = set(self.drawer(self.draw_sz, self.max_num))
            draw.update(self.user_nums)

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
        return (
            f'Lottery(max_num={self.max_num}, max_ext={self.max_ext},'
            f' draw_sz={self.draw_sz}, xtr_sz={self.xtr_sz})'
        )


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
    parser.add_argument('-c', '--config', action='store', default=Path('config.toml'),
                        type=str, help='path to config file')
    parser.add_argument('-u', '--user_nums', action='store', nargs='*', type=int,
                        help='list of user numbers to include in the draw')

    args = parser.parse_args()

    try:
        superenalotto = Lottery(max_num=args.numbers, draw_sz=args.numsz,
                                max_ext=args.extras, xtr_sz=args.xtrsz,
                                config_path=args.config, user_nums=args.user_nums)

        backend = input(
            'Scegli il backend (choice, randint, randrange, sample, shuffle) o premi invio: ').lower()

        print(superenalotto(backend=backend, many=args.many))

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
