from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional, Protocol


def validate_draw_params(func) -> Callable:
    @wraps(func)
    def wrapper(self, size: int, max_num: int, *args, **kwargs):
        if not 0 < size <= max_num:
            raise ValueError(
                f"Invalid draw parameters: size={size}, max_num={max_num}")
        return func(self, size, max_num, *args, **kwargs)
    return wrapper


class DrawMethod(Protocol):
    __name__: str

    def __call__(self, size: int, max_num: int) -> tuple[int]:
        ...


@dataclass(frozen=True, slots=True)
class Extraction:
    draw: tuple[int, ...]
    extra: Optional[tuple[int, ...]] = None
