import logging
from collections.abc import Callable
from time import perf_counter
from typing import Union

from .extralog import ExtraLog


class PerformanceLog(ExtraLog):
    def timeit(
        self,
        function: Callable = None,
        *,
        level: Union[str, int] = logging.INFO,
        time_exceptions: bool = False,
        description: str = None,
        mimimum_seconds_threshold: float = 0.05,
    ):
        if isinstance(level, str):
            level = logging.getLevelName(level.upper())

        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                start = perf_counter()
                try:
                    result = func(*args, **kwargs)
                    elapsed_seconds = round(perf_counter() - start, 3)
                    if elapsed_seconds >= mimimum_seconds_threshold:
                        self._log_time(level, func, elapsed_seconds)
                    return result
                except Exception as e:
                    elapsed_seconds = round(perf_counter() - start, 3)
                    if time_exceptions and elapsed_seconds >= mimimum_seconds_threshold:
                        description_with_error = f"{description or func.__qualname__} ({type(e).__name__}: {e})"
                        self._log_time(level, func, elapsed_seconds, description_with_error)
                    raise

            return wrapper

        if function:
            return decorator(function)
        return decorator

    def _log_time(self, level: Union[str, int], func: Callable, elapsed_seconds: float, description: str = None):
        if not description:
            description = func.__qualname__
        self.log(
            level,
            f"{description} took {elapsed_seconds:.3f}s",
            extra=dict(
                performance={
                    'measured': func.__qualname__,
                    'elapsed_seconds': elapsed_seconds,
                    'description': description,
                }
            ),
            stacklevel=4,
        )
