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
                f"Invalid draw parameters: {size=}, {max_num=}, size must be between 1 and max value")
        return func(self, size, max_num, *args, **kwargs)
    return wrapper


@dataclass(slots=True)
class Extraction:
    draw: set[int]
    extra: Optional[set[int]] = field(default=None)


@dataclass(frozen=True)
class Config:
    """Configuration settings for lottery draws"""
    max_num: int = field(default=90)
    draw_sz: int = field(default=6)
    max_ext: int = field(default=90)
    xtr_sz: int = field(default=1)
    max_draw_iters: int = field(default=100_000)
    user_nums: list[int] = field(default_factory=list)

    def __post_init__(self):
        if self.max_num < 1:
            raise ValueError("max_numbers must be positive")
        if not 0 < self.draw_sz <= self.max_num:
            raise ValueError("draw_size must be between 1 and max_numbers")
        if not 0 <= self.xtr_sz <= self.max_ext:
            raise ValueError("xtr_size must be between 1 and max_ext")
        if self.max_ext < 0:
            raise ValueError("max_ext cannot be negative")
        if self.max_draw_iters < 1:
            raise ValueError("max_draw_iters must be positive")

    @classmethod
    def load_config(cls, path: Path | str) -> 'Config':
        try:
            with open(path, 'rb') as f:
                config = tomllib.load(f)
                return cls(
                    max_num=config.get('max_numbers', cls.max_num),
                    draw_sz=config.get('draw_size', cls.draw_sz),
                    max_ext=config.get('max_extra_numbers', cls.max_ext),
                    xtr_sz=config.get('extra_size', cls.xtr_sz),
                    max_draw_iters=config.get('max_draw_iters', cls.max_draw_iters),
                    user_nums=config.get('user_numbers', [])
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
