from functools import wraps
from typing import TypeVar

T = TypeVar("T")


def handle_errors(wrapped: T) -> T:
    @wraps(wrapped)
    def _wrapper(*args, **kwargs):
        try:
            return (wrapped(*args, **kwargs), None)
        except Exception as e:
            return (None, e)

    return _wrapper
