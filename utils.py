import tomllib
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Callable, Iterable, Optional, Protocol


def validate_draw_params(func) -> Callable:
    '''
    Decorator to validate draw parameters, to assure the size is within 
    the range of 1 to max_num. This to avoid repetitions in the draw.
    '''
    @wraps(func)
    def wrapper(self, size: int, max_num: int, *args, **kwargs):
        if not 0 < size <= max_num:
            raise ValueError(
                f"Invalid draw parameters: size={size}, max_num={max_num}")
        return func(self, size, max_num, *args, **kwargs)
    return wrapper


@dataclass(slots=True)
class Extraction:
    draw: tuple[int, ...]
    extra: Optional[tuple[int, ...]] = field(default=None)


@dataclass(frozen=True)
class Config:
    """Configuration settings for lottery draws"""
    max_numbers: int = field(default=90)
    draw_size: int = field(default=6)
    max_ext: int = field(default=90)
    xtr_sz: int = field(default=1)
    max_draw_iters: int = field(default=100_000)

    @classmethod
    def load_config(cls, path: Path | str) -> 'Config':
        try:
            with open(path, 'rb') as f:
                config = tomllib.load(f)
                return cls(
                    max_numbers=config.get(
                        'max_numbers', cls.max_numbers),
                    draw_size=config.get(
                        'draw_size', cls.draw_size),
                    max_ext=config.get(
                        'max_extra_numbers', cls.max_ext),
                    xtr_sz=config.get(
                        'extra_size', cls.xtr_sz),
                    max_draw_iters=config.get(
                        'max_draw_iters', cls.max_draw_iters),
                )
        except (FileNotFoundError, tomllib.TOMLDecodeError) as e:
            print(f"Config error: {e}, using default configs.")
            return cls()


class DrawMethod(Protocol):
    """
    This protocol defines the interface for draw methods, which
    should accept a size and max_num and return Iterable of int.
    """
    __name__: str

    def __call__(self, size: int, max_num: int) -> Iterable[int]: ...
