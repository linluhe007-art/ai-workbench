"""
Phase 4.21 tests - ObservabilityLogger
Covers: JSON structured logging, context variables, all levels
"""
import json
import io
import pytest

from app.observability.logger import (
    ObservabilityLogger,
    get_observability_logger,
    reset_observability_logger,
    set_request_context,
    clear_request_context,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_observability_logger()
    clear_request_context()
    yield
    reset_observability_logger()
    clear_request_context()


class TestObservabilityLogger:
    def test_logger_creates_json_output(self):
        stream = io.StringIO()
        log = ObservabilityLogger(stream=stream)
        log.info("test message")
        output = stream.getvalue().strip()
        record = json.loads(output)
        assert record["level"] == "INFO"
        assert record["message"] == "test message"
        assert "timestamp" in record
        assert record["logger"] == "observability"

    def test_logger_warning_level(self):
        stream = io.StringIO()
        log = ObservabilityLogger(stream=stream)
        log.warning("warning message")
        record = json.loads(stream.getvalue().strip())
        assert record["level"] == "WARNING"

    def test_logger_error_level(self):
        stream = io.StringIO()
        log = ObservabilityLogger(stream=stream)
        log.error("error message")
        record = json.loads(stream.getvalue().strip())
        assert record["level"] == "ERROR"

    def test_logger_with_extra_fields(self):
        stream = io.StringIO()
        log = ObservabilityLogger(stream=stream)
        log.info("task done", task_id="t1", agent_id="mock", duration_ms=150)
        record = json.loads(stream.getvalue().strip())
        assert record["task_id"] == "t1"
        assert record["agent_id"] == "mock"
        assert record["duration_ms"] == 150

    def test_logger_exception(self):
        stream = io.StringIO()
        log = ObservabilityLogger(stream=stream)
        try:
            raise ValueError("test error")
        except ValueError:
            log.exception("something went wrong")
        record = json.loads(stream.getvalue().strip())
        assert record["level"] == "ERROR"
        assert "traceback" in record
        assert "ValueError" in record["traceback"]

    def test_logger_exception_without_traceback(self):
        stream = io.StringIO()
        log = ObservabilityLogger(stream=stream)
        log.exception("error without trace", exc_info=False)
        record = json.loads(stream.getvalue().strip())
        assert "traceback" not in record

    def test_logger_multiple_lines(self):
        stream = io.StringIO()
        log = ObservabilityLogger(stream=stream)
        log.info("first")
        log.info("second")
        lines = stream.getvalue().strip().split("\n")
        assert len(lines) == 2
        r1 = json.loads(lines[0])
        r2 = json.loads(lines[1])
        assert r1["message"] == "first"
        assert r2["message"] == "second"


class TestRequestContext:
    def test_set_and_use_request_context(self):
        stream = io.StringIO()
        set_request_context(request_id="req-1", tenant_id="t-1", user_id="u-1")
        log = ObservabilityLogger(stream=stream)
        log.info("contextual message")
        record = json.loads(stream.getvalue().strip())
        assert record["request_id"] == "req-1"
        assert record["tenant_id"] == "t-1"
        assert record["user_id"] == "u-1"

    def test_clear_request_context(self):
        stream = io.StringIO()
        set_request_context(request_id="req-1")
        clear_request_context()
        log = ObservabilityLogger(stream=stream)
        log.info("no context")
        record = json.loads(stream.getvalue().strip())
        assert "request_id" not in record

    def test_fields_override_context(self):
        stream = io.StringIO()
        set_request_context(request_id="ctx-req")
        log = ObservabilityLogger(stream=stream)
        log.info("override", request_id="explicit-req")
        record = json.loads(stream.getvalue().strip())
        assert record["request_id"] == "explicit-req"


class TestObservabilityLoggerSingleton:
    def test_singleton_returns_same_instance(self):
        a = get_observability_logger()
        b = get_observability_logger()
        assert a is b

    def test_singleton_reset(self):
        a = get_observability_logger()
        reset_observability_logger()
        b = get_observability_logger()
        assert a is not b