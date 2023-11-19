import io
import json
import logging

try:
    from jsonformatter import JsonFormatter
except ImportError:
    print("jsonformatter must be installed for tests. aborting")
    exit(1)

from extralog import ExtraLog


def test_init_accepts_logger_or_name():
    logger_name = "foo"
    standard_logger = logging.getLogger(logger_name)
    extralog = ExtraLog(standard_logger)
    assert extralog.logger is standard_logger
    assert ExtraLog(logger_name).logger is standard_logger


def test_update_extra_persists_across_multiple_calls(current_test_name):
    with io.StringIO() as stream:
        extralog = build_extralog_with_stream(current_test_name, stream)
        extralog.info("first log", extra=dict(log="first"))
        extralog.info("second log should not have any extra")
        extralog.update(updated="extra").info("third log should have 'updated':'extra'")
        extralog.info("fourth log also should have 'updated':'extra'")
        extralog.info("fifth log should have 'updated':'extra' and 'log':'fifth'", extra=dict(log="fifth"))
        extralog.info("sixth log should only have 'updated':'extra'")
        extralog.info(
            "seventh log should only have 'updated':'extra implicitly'", extra=dict(updated="extra implicitly")
        )
        extralog.info("eighth log should only have 'updated':'extra implicitly'")
        extralog.update(updated="extra explicitly", have='a cookie')
        extralog.info("ninth log should have 'updated':'extra explicitly' and 'have':'a cookie'")
        extralog.update(updated="extra last time", have='a mars bar').info(
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
        extralog = build_extralog_with_stream(current_test_name, stream)
        extralog.update(foo="bar", baz="qux").info("first log should have 'foo':'bar' and 'baz':'qux'")
        extralog.delete("foo").info("second log should have 'baz':'qux'")
        extralog.delete("baz")
        extralog.info("third log should not have any extra")
        extralog.delete("made up key, but that's fine")
        extralog.info("fourth log should not have any extra")

        stream_value = stream.getvalue()

    first, second, third, fourth = [json.loads(line) for line in stream_value.splitlines()]
    assert first == dict(foo='bar', baz='qux')
    assert second == dict(baz='qux')
    assert third == dict()
    assert fourth == dict()


def test_logs_extra_when_passed_as_kwarg(current_test_name):
    with io.StringIO() as stream:
        extralog = build_extralog_with_stream(current_test_name, stream)
        extralog.info("first log", log="first")
        extralog.info("second log should not have any extra")
        extralog.update(updated="extra").info("third log should have 'updated':'extra'")
        extralog.info("fourth log also should have 'updated':'extra'")
        extralog.info("fifth log should have 'updated':'extra' and 'log':'fifth'", log="fifth")
        extralog.info("sixth log should only have 'updated':'extra'")
        extralog.info("seventh log should only have 'updated':'extra implicitly'", updated="extra implicitly")
        extralog.info("eighth log should only have 'updated':'extra implicitly'")
        extralog.update(updated="extra explicitly", have='a cookie')
        extralog.info("ninth log should have 'updated':'extra explicitly' and 'have':'a cookie'")
        extralog.update(updated="extra last time", have='a mars bar').info(
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
        extralog = build_extralog_with_stream(
            current_test_name, stream, fmt=dict(message="message", funcName="funcName")
        )
        try:
            1 / 0
        except ZeroDivisionError:
            extralog.update(foo="bar").info(
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
        extralog = build_extralog_with_stream(current_test_name, stream)
        extralog.update(hello="world")
        with extralog.scope(foo="bar"):
            extralog.info("first log should have 'foo':'bar' and 'hello':'world'")
        extralog.info("second log should have 'hello':'world'")
        with extralog.scope(first="scope"):
            with extralog.scope(second="scope"):
                extralog.info("third log should have 'first':'scope', 'second':'scope' and 'hello':'world'")
                extralog.info(
                    "fourth log should have 'first':'scope', 'second':'changed' and 'hello':'world'", second='changed'
                )
                extralog.info("fifth log should have 'first':'scope', 'second':'changed' and 'hello':'world'")
                extralog.info(
                    "sixth log should have 'first':'changed from inner', 'second':'changed' and 'hello':'world'",
                    first='changed from inner',
                )
                extralog.update(should='persist outside of scope')
            extralog.info(
                "seventh log should have 'first':'changed from inner', 'hello':'world' and 'should':'persist outside of scope'"
            )
        extralog.info("eigth log should have 'hello':'world' and 'should':'persist outside of scope'")
        with extralog.scope(deleting="manually"):
            extralog.delete("deleting")
        extralog.info("ninth log should not have 'deleting':'manually'")
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
        extralog = build_extralog_with_stream(current_test_name, stream)
        extralog.update(hello="world")
        with extralog(foo="bar") as logger:
            logger.info("first log should have 'foo':'bar' and 'hello':'world'")
            with extralog(baz="qux"):
                logger.info("second log should have 'foo':'bar', 'baz':'qux' and 'hello':'world'")
        extralog.info("third log should have 'hello':'world'")
        stream_value = stream.getvalue()
    first, second, third = [json.loads(line) for line in stream_value.splitlines()]
    assert first == dict(foo='bar', hello='world')
    assert second == dict(foo='bar', hello='world', baz='qux')
    assert third == dict(hello='world')


def test_scope_decorator(current_test_name):
    with io.StringIO() as stream:
        extralog = build_extralog_with_stream(current_test_name, stream)

        @extralog.scope(foo="bar")
        def first(logger):
            logger.info("first log should have 'foo':'bar' and 'hello':'world'")
            second()

        @extralog.scope(baz="qux")
        def second(logger):
            logger.update(hello="world")
            logger.info("second log should have 'foo':'bar', 'baz':'qux' and 'hello':'world'")
            third()

        @extralog.scope(hello="earth")
        def third(logger):
            logger.info("third log should have 'foo':'bar', 'baz':'qux' and 'hello':'earth'")

        first()
        extralog.info("fourth log should not have any extra")
        stream_value = stream.getvalue()
    first, second, third, fourth = [json.loads(line) for line in stream_value.splitlines()]
    assert first == dict(foo='bar')
    assert second == dict(foo='bar', baz='qux', hello='world')
    assert third == dict(foo='bar', baz='qux', hello='earth')
    assert fourth == dict()


def build_extralog_with_stream(logger_name, stream, *, fmt: dict = None):
    wrapped_logger = logging.getLogger(logger_name)
    wrapped_logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(stream)
    fmt = fmt or dict()
    formatter = JsonFormatter(fmt=json.dumps(fmt), mix_extra=True)
    stream_handler.setFormatter(formatter)
    wrapped_logger.addHandler(stream_handler)
    extralog = ExtraLog(wrapped_logger)
    return extralog
