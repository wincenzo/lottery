import argparse
import locale
import random as rnd
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from itertools import compress, repeat
from pathlib import Path
from typing import Iterable, Iterator, Optional, Self

from tqdm import tqdm

from drawers import Drawer
from utils import Config, Extraction, validate_draw_params

locale.setlocale(locale.LC_ALL, locale='it_IT')


class Lottery:
    __slots__ = (
        'CONFIG',
        'init_backend',
        'max_num',
        'max_ext',
        'draw_sz',
        'xtr_sz',
        'result',
        '_iters',
        '_backend',
        'user_nums',
        '_numbers',
        '__dict__',
    )

    def __init__(self,
                 max_num: Optional[int] = None,
                 draw_sz: Optional[int] = None,
                 max_ext: Optional[int] = None,
                 xtr_sz: Optional[int] = None,
                 config_path: Optional[Path | str] = None,
                 user_nums: Optional[list[int]] = None) -> None:
        """
        Initialize a Lottery instance with configuration and user preferences.

        Parameters:
            max_num (Optional[int]): The maximum number that can be drawn. If not provided, uses the value from config.
            draw_sz (Optional[int]): The number of main numbers to draw. If not provided, uses the value from config.
            max_ext (Optional[int]): The maximum number for extra draws. If not provided, uses the value from config.
            xtr_sz (Optional[int]): The number of extra numbers to draw. If not provided, uses the value from config.
            config_path (Optional[Path | str]): Path to a TOML configuration file. If not provided, uses defaults.
            user_nums (Optional[list[int]]): List of user-chosen numbers to always include in the draw.

        Notes:
            - If a parameter is not provided, its value is loaded from the configuration file or defaults.
            - User numbers are excluded from the pool of available numbers for random draws.
        """

        self.CONFIG: Config = (
            Config.load_config(config_path) if config_path else Config())

        self.user_nums: list[int] = user_nums or self.CONFIG.user_nums
        self.max_num: int = max_num or self.CONFIG.max_num
        self.draw_sz: int = draw_sz or self.CONFIG.draw_sz
        self.max_ext: int = max_ext or self.CONFIG.max_ext
        self.xtr_sz: int = xtr_sz or self.CONFIG.xtr_sz
        self.result: Extraction = Extraction(draw=set())
        self._iters: int = 1

    @cached_property
    def numbers(self) -> range:
        return range(1, self.max_num + 1)

    @validate_draw_params
    def drawer(self, max_num: int, size: int, numbers: range) -> Iterable[int]:
        """
        Adds randomness by simulating multiple draws.
        """
        _drawer = Drawer(
            backend_type=self.init_backend,
            user_nums=self.user_nums,
            numbers=numbers,
        )

        with ThreadPoolExecutor() as executor:
            futures = (
                executor.submit(_drawer.draw, max_num, size)
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
    def drawing_session(self) -> Iterator[tuple[set[int], set[int] | None]]:
        try:
            numbers = self.numbers

            if self.user_nums:
                self.draw_sz = self.draw_sz - len(self.user_nums)
                numbers = (
                    filter(lambda n: n not in self.user_nums, self.numbers))

            draw = set(self.drawer(self.max_num, self.draw_sz, numbers))
            draw.update(self.user_nums)

            if all((self.xtr_sz, self.max_ext)):
                self.user_nums = []
                numbers = self.numbers
                extra = self.drawer(self.max_ext, self.xtr_sz, numbers)
            else:
                extra = self.result.extra

            yield draw, extra
        except Exception as e:
            print(f'Error: {e}')
            raise
        finally:
            self._iters = 0
            self._numbers = list(self.numbers)
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
        concorso = input(
            'Seleziona il concorso (eurojackpot, superenalotto): ').lower()

        match concorso:
            case '':
                config = None
                print('Nessun concorso selezionato, usando configurazione predefinita: ')
            case c if 'eurojackpot'.startswith(c.lower()):
                config = Path('eurojackpot.toml')
                print('Concorso Eurojackpot selezionato: ')
            case c if 'superenalotto'.startswith(c.lower()):
                config = Path('superenalotto.toml')
                print('Concorso Superenalotto selezionato: ')
            case _:
                config = None
                print(
                    'Nessun concorso valido selezionato, usando configurazione predefinita: ')

        estrazione = Lottery(max_num=args.numbers, draw_sz=args.numsz,
                             max_ext=args.extras, xtr_sz=args.xtrsz,
                             config_path=config, user_nums=args.user_nums)

        print(repr(estrazione), '\n', )

        backend = input(
            'Scegli il metodo di estrazione (choice, randint, randrange, sample, shuffle) o premi invio: ').lower()

        print(estrazione(backend=backend, many=args.many))

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
