from functools import partial, wraps


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
