import io
import json
import logging

try:
    from jsonformatter import JsonFormatter
except ImportError:
    print("jsonformatter must be installed for tests. aborting")
    exit(1)

from context_logger import ContextLogger


def test_init_accepts_logger_or_name():
    logger_name = "foo"
    standard_logger = logging.getLogger(logger_name)
    ctx_logger = ContextLogger(standard_logger)
    assert ctx_logger.logger is standard_logger
    assert ContextLogger(logger_name).logger is standard_logger


def test_update_extra_persists_across_multiple_calls(current_test_name):
    with io.StringIO() as stream:
        ctx_logger = build_ctx_logger_with_stream(current_test_name, stream)
        ctx_logger.info("first log", extra=dict(log="first"))
        ctx_logger.info("second log should not have any extra")
        ctx_logger.update_extra(updated="extra").info("third log should have 'updated':'extra'")
        ctx_logger.info("fourth log also should have 'updated':'extra'")
        ctx_logger.info("fifth log should have 'updated':'extra' and 'log':'fifth'", extra=dict(log="fifth"))
        ctx_logger.info("sixth log should only have 'updated':'extra'")
        ctx_logger.info(
            "seventh log should only have 'updated':'extra implicitly'", extra=dict(updated="extra implicitly")
        )
        ctx_logger.info("eighth log should only have 'updated':'extra implicitly'")
        ctx_logger.update_extra(updated="extra explicitly", have='a cookie')
        ctx_logger.info("ninth log should have 'updated':'extra explicitly' and 'have':'a cookie'")
        ctx_logger.update_extra(updated="extra last time", have='a mars bar').info(
            "tenth log should have 'updated':'extra last time', 'have':'a mars bar' and 'test_is':'over'",
            extra=dict(test_is='over'),
        )

        stream_value = stream.getvalue()

    first, second, third, fourth, fifth, sixth, seventh, eighth, ninth, tenth = [
        json.loads(line) for line in stream_value.splitlines()
    ]
    assert first == dict(log='first')
    assert second == dict()
    assert third == dict(updated='extra')
    assert fourth == dict(updated='extra')
    assert fifth == dict(updated='extra', log='fifth')
    assert sixth == dict(updated='extra')
    assert seventh == dict(updated='extra implicitly')
    assert eighth == dict(updated='extra implicitly')
    assert ninth == dict(updated='extra explicitly', have='a cookie')
    assert tenth == dict(updated='extra last time', have='a mars bar', test_is='over')


def test_delete_extra(current_test_name):
    with io.StringIO() as stream:
        ctx_logger = build_ctx_logger_with_stream(current_test_name, stream)
        ctx_logger.update_extra(foo="bar", baz="qux").info("first log should have 'foo':'bar' and 'baz':'qux'")
        ctx_logger.delete_extra("foo").info("second log should have 'baz':'qux'")
        ctx_logger.delete_extra("baz")
        ctx_logger.info("third log should not have any extra")
        ctx_logger.delete_extra("made up key, but that's fine")
        ctx_logger.info("fourth log should not have any extra")

        stream_value = stream.getvalue()

    first, second, third, fourth = [json.loads(line) for line in stream_value.splitlines()]
    assert first == dict(foo='bar', baz='qux')
    assert second == dict(baz='qux')
    assert third == dict()
    assert fourth == dict()


def test_logs_extra_when_passed_as_kwarg(current_test_name):
    with io.StringIO() as stream:
        ctx_logger = build_ctx_logger_with_stream(current_test_name, stream)
        ctx_logger.info("first log", log="first")
        ctx_logger.info("second log should not have any extra")
        ctx_logger.update_extra(updated="extra").info("third log should have 'updated':'extra'")
        ctx_logger.info("fourth log also should have 'updated':'extra'")
        ctx_logger.info("fifth log should have 'updated':'extra' and 'log':'fifth'", log="fifth")
        ctx_logger.info("sixth log should only have 'updated':'extra'")
        ctx_logger.info("seventh log should only have 'updated':'extra implicitly'", updated="extra implicitly")
        ctx_logger.info("eighth log should only have 'updated':'extra implicitly'")
        ctx_logger.update_extra(updated="extra explicitly", have='a cookie')
        ctx_logger.info("ninth log should have 'updated':'extra explicitly' and 'have':'a cookie'")
        ctx_logger.update_extra(updated="extra last time", have='a mars bar').info(
            "tenth log should have 'updated':'extra last time', 'have':'a mars bar', 'test_is':'over' and 'good':'bye'",
            test_is='over',
            extra=dict(good='bye'),
        )

        stream_value = stream.getvalue()

    first, second, third, fourth, fifth, sixth, seventh, eighth, ninth, tenth = [
        json.loads(line) for line in stream_value.splitlines()
    ]
    assert first == dict(log='first')
    assert second == dict()
    assert third == dict(updated='extra')
    assert fourth == dict(updated='extra')
    assert fifth == dict(updated='extra', log='fifth')
    assert sixth == dict(updated='extra')
    assert seventh == dict(updated='extra implicitly')
    assert eighth == dict(updated='extra implicitly')
    assert ninth == dict(updated='extra explicitly', have='a cookie')
    assert tenth == dict(updated='extra last time', have='a mars bar', test_is='over', good='bye')


def test_standard_log_function_kwargs_work(current_test_name):
    with io.StringIO() as stream:
        ctx_logger = build_ctx_logger_with_stream(
            current_test_name, stream, fmt=dict(message="message", funcName="funcName")
        )
        try:
            1 / 0
        except ZeroDivisionError:
            ctx_logger.update_extra(foo="bar").info(
                "", baz="qux", extra=dict(hi="bye"), exc_info=True, stack_info=True, stacklevel=4
            )
        stream_value = stream.getvalue()
    first = json.loads(stream_value)
    message = first.pop("message")
    funcName = first.pop("funcName")
    assert first == dict(foo='bar', baz='qux', hi='bye')
    assert funcName != current_test_name
    assert 'Traceback (most recent call last):' in message
    assert 'Stack (most recent call last):' in message


def test_scope(current_test_name):
    with io.StringIO() as stream:
        ctx_logger = build_ctx_logger_with_stream(current_test_name, stream)
        ctx_logger.update_extra(hello="world")
        with ctx_logger.scope(foo="bar"):
            ctx_logger.info("first log should have 'foo':'bar' and 'hello':'world'")
        ctx_logger.info("second log should have 'hello':'world'")
        with ctx_logger.scope(first="scope"):
            with ctx_logger.scope(second="scope"):
                ctx_logger.info("third log should have 'first':'scope', 'second':'scope' and 'hello':'world'")
                ctx_logger.info(
                    "fourth log should have 'first':'scope', 'second':'changed' and 'hello':'world'", second='changed'
                )
                ctx_logger.info("fifth log should have 'first':'scope', 'second':'changed' and 'hello':'world'")
                ctx_logger.info(
                    "sixth log should have 'first':'changed from inner', 'second':'changed' and 'hello':'world'",
                    first='changed from inner',
                )
                ctx_logger.update_extra(should='persist outside of scope')
            ctx_logger.info(
                "seventh log should have 'first':'changed from inner', 'hello':'world' and 'should':'persist outside of scope'"
            )
        ctx_logger.info("eigth log should have 'hello':'world' and 'should':'persist outside of scope'")
        with ctx_logger.scope(deleting="manually"):
            ctx_logger.delete_extra("deleting")
        ctx_logger.info("ninth log should not have 'deleting':'manually'")
        stream_value = stream.getvalue()
    first, second, third, fourth, fifth, sixth, seventh, eigth, ninth = [
        json.loads(line) for line in stream_value.splitlines()
    ]
    assert first == dict(foo='bar', hello='world')
    assert second == dict(hello='world')
    assert third == dict(first='scope', second='scope', hello='world')
    assert fourth == dict(first='scope', second='changed', hello='world')
    assert fifth == dict(first='scope', second='changed', hello='world')
    assert sixth == dict(first='changed from inner', second='changed', hello='world')
    assert seventh == dict(first='changed from inner', hello='world', should='persist outside of scope')
    assert eigth == dict(hello='world', should='persist outside of scope')
    assert ninth == dict(hello='world', should='persist outside of scope')


def test_start_scope_by_calling_logger_instance(current_test_name):
    with io.StringIO() as stream:
        ctx_logger = build_ctx_logger_with_stream(current_test_name, stream)
        ctx_logger.update_extra(hello="world")
        with ctx_logger(foo="bar") as logger:
            logger.info("first log should have 'foo':'bar' and 'hello':'world'")
            with ctx_logger(baz="qux"):
                logger.info("second log should have 'foo':'bar', 'baz':'qux' and 'hello':'world'")
        ctx_logger.info("third log should have 'hello':'world'")
        stream_value = stream.getvalue()
    first, second, third = [json.loads(line) for line in stream_value.splitlines()]
    assert first == dict(foo='bar', hello='world')
    assert second == dict(foo='bar', hello='world', baz='qux')
    assert third == dict(hello='world')


def build_ctx_logger_with_stream(logger_name, stream, *, fmt: dict = None):
    wrapped_logger = logging.getLogger(logger_name)
    wrapped_logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(stream)
    fmt = fmt or dict()
    formatter = JsonFormatter(fmt=json.dumps(fmt), mix_extra=True)
    stream_handler.setFormatter(formatter)
    wrapped_logger.addHandler(stream_handler)
    ctx_logger = ContextLogger(wrapped_logger)
    return ctx_logger
