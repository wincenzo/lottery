import sys
import tomllib
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Iterable, Optional, Protocol


@dataclass(slots=True)
class Extraction:
    draw: tuple[int, ...]
    extra: Optional[tuple[int, ...]] = field(default=None)


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


class DrawMethod(Protocol):
    """
    This protocol defines the interface for draw methods, which
    should accept a size and max_num and return Iterable of int.
    """
    __name__: str

    def __call__(self, size: int, max_num: int) -> Iterable[int]: ...


def load_config(path: str) -> dict[str, Any]:
    """
    Load configuration from a TOML file.
    """
    try:
        with open(path, 'rb') as c:
            configs = tomllib.load(c)
            return configs
    except FileNotFoundError:
        print("Configuration file not found.")
        sys.exit(1)
    except tomllib.TOMLDecodeError:
        print("Error decoding the configuration file.")
        sys.exit(1)
