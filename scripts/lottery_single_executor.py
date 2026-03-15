import argparse
import locale
import random as rnd
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from functools import cached_property
from itertools import compress, repeat
from pathlib import Path
from typing import Iterable, Iterator, Optional, Self

from drawers import Drawer
from tqdm import tqdm
from utils import Config, Extraction, validate_draw_params


class Lottery:
    """
    Alternative implementation that avoids nested ThreadPoolExecutors.
    Uses a single ThreadPoolExecutor at the top level for both main and extra draws.
    This is more efficient and avoids potential issues with nested executors.
    """
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
    def _draw_iterations(self, max_num: int, size: int, numbers: range | list[int]) -> Iterable[int]:
        """
        Performs multiple draw iterations without ThreadPoolExecutor.
        This method handles the iteration logic that was previously in drawer().
        """
        _drawer = Drawer(
            backend_type=self.init_backend,
            user_nums=self.user_nums,
            numbers=numbers,
        )

        # Collect all draw results
        draws = [
            _drawer(max_num, size) for _ in tqdm(
                range(self._iters),
                desc="Estraendo ...",
                unit="estrazioni",
                ncols=80,
                bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]')
        ]

        def selections(length: int) -> Iterator[int]:
            yield from (
                1 if rnd.random() > 0.5 else 0 for _ in repeat(None, length))

        while (length := len(draws)) >= 10:
            draws = list(compress(draws, selections(length)))
        else:
            return rnd.choice(draws)

    @contextmanager
    def drawing_session(self) -> Iterator[tuple[set[int], set[int] | None]]:
        """
        Context manager that performs both main and extra draws concurrently.
        """
        try:
            numbers = self.numbers
            user_nums = self.user_nums

            if self.user_nums:
                self.draw_sz -= len(user_nums)
                numbers = list(
                    filter(lambda n: n not in self.user_nums, numbers))

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures_main = executor.submit(
                    self._draw_iterations,self.max_num, self.draw_sz, numbers)

                if extra := all((self.xtr_sz, self.max_ext)):
                    self.user_nums = []
                    futures_extra = executor.submit(
                        self._draw_iterations, self.max_ext, self.xtr_sz, self.numbers)

            draw = set(futures_main.result()) | set(user_nums)
            extra = set(futures_extra.result()) if extra else self.result.extra

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

    def draw(self, backend: str, many: Optional[int] = None) -> Self:
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
    locale.setlocale(locale.LC_ALL, locale='it_IT')

    parser = argparse.ArgumentParser(
        description='Lottery number generator (Single Executor Version)')

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
            case c if 'eurojackpot'.startswith(c):
                config = Path('config/eurojackpot.toml')
                print('Concorso Eurojackpot selezionato: ')
            case c if 'superenalotto'.startswith(c):
                config = Path('config/superenalotto.toml')
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

        print(estrazione.draw(backend=backend, many=args.many))

    except KeyboardInterrupt:
        print('\n--- MANUALLY STOPPED ---')
        sys.exit(1)
