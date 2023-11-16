import logging
from contextlib import contextmanager
from typing import Union

from typing_extensions import Self


class ContextLogger(logging.LoggerAdapter):
    """
    Persists `extra` across logging calls.
    `extra` can be specified as a kwarg to any logging call, e.g. `logger.info("message", chat_id=123)`
    """

    extra: dict

    def __init__(self, logger_or_name=Union[logging.Logger, str], extra: dict = None):
        if isinstance(logger_or_name, str):
            logger = logging.getLogger(logger_or_name)
        else:
            logger = logger_or_name
        extra = extra or {}
        super().__init__(logger, extra)

    def process(self, msg, kwargs):
        """Overwrites and persists new values to existing keys in self.extra."""
        log_function_kwargs = {}
        for log_function_kwarg in ("exc_info", "stack_info", "stacklevel"):
            if log_function_kwarg in kwargs:
                log_function_kwargs[log_function_kwarg] = kwargs.pop(log_function_kwarg)

        explicit_extra = kwargs.pop('extra', {})
        new_extra = kwargs | explicit_extra

        for k, v in new_extra.items():
            if k in self.extra:
                self.extra[k] = v

        return msg, {"extra": self.extra | new_extra, **log_function_kwargs}

    def update_extra(self, **kwargs) -> Self:
        """
        >>> logger = ContextLogger("example")
        >>> logger.update_extra(chat_id="...").info("hello")
        """
        if self.extra is None:
            self.extra = kwargs
        else:
            self.extra.update(kwargs)
        return self

    def delete_extra(self, *keys) -> Self:
        for key in keys:
            self.extra.pop(key, None)
        return self

    @contextmanager
    def scope(self, **kwargs) -> Self:
        """
        Persist `extra` only in a given scope.

        >>> logger = ContextLogger("example")
        >>> with logger.scope(doing="something"):
        ...     something()
        ...     logger.info("done")
        { 'message': 'done', 'doing': 'something' }
        """
        self.update_extra(**kwargs)
        try:
            yield self
        finally:
            self.delete_extra(*kwargs.keys())

    __call__ = scope
