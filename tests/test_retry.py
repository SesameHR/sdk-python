import pytest

from sesamehr import SesameApiError, SesameConnectionError, with_retry


def test_returns_result_on_success():
    assert with_retry(lambda: 42) == 42


def test_retries_on_connection_error(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []

    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise SesameConnectionError("boom")
        return "ok"

    assert with_retry(fn) == "ok"
    assert len(calls) == 3


def test_retries_on_5xx(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []

    def fn():
        calls.append(1)
        raise SesameApiError(503, None)

    with pytest.raises(SesameApiError):
        with_retry(fn)
    assert len(calls) == 3  # initial + 2 retries


def test_no_retry_on_4xx():
    calls = []

    def fn():
        calls.append(1)
        raise SesameApiError(404, None)

    with pytest.raises(SesameApiError):
        with_retry(fn)
    assert len(calls) == 1


def test_no_retry_on_timeout():
    calls = []

    def fn():
        calls.append(1)
        raise SesameConnectionError("request timed out", is_timeout=True)

    with pytest.raises(SesameConnectionError):
        with_retry(fn)
    assert len(calls) == 1


def test_custom_attempts(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []

    def fn():
        calls.append(1)
        raise SesameConnectionError("boom")

    with pytest.raises(SesameConnectionError):
        with_retry(fn, attempts=4)
    assert len(calls) == 5


def test_custom_predicate(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    calls = []

    def fn():
        calls.append(1)
        raise ValueError("custom")

    with pytest.raises(ValueError):
        with_retry(fn, should_retry=lambda e: isinstance(e, ValueError))
    assert len(calls) == 3
