import logging
from functools import partial, wraps
from typing import Union

from typing_extensions import Self


class creates_scope:
    def __init__(self, func):
        wraps(func)(self)
        self.func = func

    def __get__(self, obj, objtype):
        """Support instance methods."""
        return partial(self.__call__, obj)

    def __call__(self, *args, **kwargs):
        bound_gen = self.func(*args, **kwargs)
        return _ContextManagerDecorator(bound_gen)


class _ContextManagerDecorator:
    def __init__(self, bound_gen):
        self.bound_gen = bound_gen

    def __enter__(self):
        return next(self.bound_gen)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            next(self.bound_gen)
        except StopIteration:
            return False
        else:
            raise RuntimeError("Generator didn't terminate as expected.")

    def __call__(self, fn):
        """Implement decorator functionality with the logger passed to the decorated function."""

        @wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = self.__enter__()
            try:
                return fn(ctx, *args, **kwargs)
            finally:
                self.__exit__(None, None, None)

        return wrapper


class ContextLogger(logging.LoggerAdapter):
    extra: dict

    def __init__(self, logger_or_name=Union[logging.Logger, str], extra: dict = None):
        if isinstance(logger_or_name, str):
            logger = logging.getLogger(logger_or_name)
        else:
            logger = logger_or_name
        extra = extra or {}
        super().__init__(logger, extra)

    def process(self, msg, kwargs):
        """
        Existing keys in `self.extra` are updated and persisted.
        Keys not previously in `self.extra` are included only for the duration of this call.

        The following are treated the same:
        >>> log.info("message", request_id=123)
        >>> log.info("message", extra={'request_id' : 123})
        """
        log_function_arg_names = ("exc_info", "stack_info", "stacklevel")
        log_function_kwargs = {}
        for log_function_arg_name in log_function_arg_names:
            if log_function_arg_name in kwargs:
                log_function_kwargs[log_function_arg_name] = kwargs.pop(log_function_arg_name)

        explicit_extra = kwargs.pop('extra', {})
        new_extra = kwargs | explicit_extra

        for k, v in new_extra.items():
            if k in self.extra:
                self.extra[k] = v

        return msg, {"extra": self.extra | new_extra, **log_function_kwargs}

    def update_extra(self, **kwargs) -> Self:
        """
        Persist `extra` across logging calls.

        >>> log = ContextLogger("example")
        >>> log.update_extra(chat_id="...").info("hello")
        """
        if not self.extra:
            self.extra = kwargs
        else:
            self.extra.update(kwargs)
        return self

    def delete_extra(self, *keys) -> Self:
        for key in keys:
            self.extra.pop(key, None)
        return self

    @creates_scope
    def scope(self, **kwargs) -> Self:
        """
        Persist `extra` only in a given scope.

        >>> log = ContextLogger("example")
        >>> with log.scope(doing="something"):
        ...     something()
        ...     log.info("done")
        { 'message': 'done', 'doing': 'something' }

        # Alternatively, as a decorator:

        >>> @log.scope(doing="something")
        ... def something(logger):
        ...     logger.info("done")
        >>> something()
        { 'message': 'done', 'doing': 'something' }
        """
        self.update_extra(**kwargs)
        try:
            yield self
        finally:
            self.delete_extra(*kwargs.keys())

    def __call__(self, **kwargs):
        """
        Shortcut for `logger.scope`.

        >>> log = ContextLogger("example")
        >>> with log(doing="something"):
        ...     something()
        ...     log.info("done")
        { 'message': 'done', 'doing': 'something' }

        # Alternatively, as a decorator:

        >>> @log(doing="something")
        ... def something(logger):
        ...     logger.info("done")
        >>> something()
        { 'message': 'done', 'doing': 'something' }
        """
        return self.scope(**kwargs)
