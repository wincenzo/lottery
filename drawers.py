import random as rnd
from itertools import repeat, starmap
from operator import itemgetter
from typing import ClassVar, Iterable, Iterator

from utils import DrawMethod


class Drawer():
    BACKENDS: ClassVar[tuple[str, ...]] = (
        'choice',
        'randint',
        'randrange',
        'sample',
        'shuffle',
    )

    __slots__ = (
        'backend_type',
        'user_nums',
        'numbers',
        '_backend'
    )

    def __init__(self,
                 backend_type: str,
                 user_nums: list[int],
                 numbers: range | list[int]) -> None:
        self.backend_type = backend_type
        self.user_nums = user_nums
        self.numbers = numbers

    @property
    def backend(self) -> DrawMethod:
        return self._backend

    @backend.setter
    def backend(self, name: str) -> None:
        self._backend = getattr(self, name, self.random_backend())

    def random_backend(self) -> DrawMethod:
        return getattr(self, rnd.choice(self.BACKENDS))

    def randint(self, max_num: int, size: int) -> set[int]:
        draw = iter(lambda: rnd.randint(1, max_num), None)

        extraction = set(self.user_nums)
        for number in draw:
            extraction.add(number)
            if len(extraction) == size + len(self.user_nums):
                break

        return extraction

    def randrange(self, max_num: int, size: int) -> set[int]:
        def draw() -> Iterator[int]:
            for _ in repeat(None):
                yield rnd.randrange(1, max_num+1)

        extraction = {*self.user_nums}
        while len(extraction) < size + len(self.user_nums):
            extraction.add(next(draw()))

        return extraction

    def choice(self, max_num: int, size: int) -> tuple[int, ...]:
        # don't need to .copy() self._numbers because of slicing
        # creating a new object
        pool = (
            list(self.numbers[:max_num])
            if isinstance(self.numbers, range)
            else self.numbers[:max_num]
        )
        n_items = len(pool)

        def draw():
            nonlocal n_items
            number = pool.pop(rnd.choice(range(n_items)))
            n_items -= 1
            return number

        return tuple(starmap(draw, repeat((), size)))

    def sample(self, max_num: int, size: int) -> tuple[int, ...]:
        pool = self.numbers[:max_num]
        indexes = itemgetter(*rnd.sample(range(len(pool)), k=size))

        return (indexes(pool),) if size == 1 else indexes(pool)

    def shuffle(self, max_num: int, size: int) -> list[int]:
        pool = list(self.numbers)[:max_num]
        rnd.shuffle(pool)
        start = rnd.randint(0, len(pool)-size)
        stop = start + size
        grab = slice(start, stop, None)

        return pool[grab]

    def __call__(self, max_num: int, size: int) -> Iterable[int]:
        self.backend = self.backend_type
        return self.backend(max_num, size)
