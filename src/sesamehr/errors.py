from typing import Any


class SesameError(Exception):
    """Base error for the Sesame SDK."""

    def __init__(self, message: str, status: int | None = None, response: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.response = response


class SesameApiError(SesameError):
    """The API responded with a non-2xx status."""

    def __init__(self, status: int, body: Any) -> None:
        super().__init__(_extract_message(body, status), status, body)
        self.errors: list[Any] = _extract_errors(body)


class SesameConnectionError(SesameError):
    """Network-level failure: DNS, connect, timeout, or unparseable response."""

    def __init__(self, cause: str, *, is_timeout: bool = False, is_connect_error: bool = False) -> None:
        super().__init__(f"Connection failed: {cause}")
        self.is_timeout = is_timeout
        # True when the connection could not be opened (DNS, refused, TLS), so
        # the request never reached the server.
        self.is_connect_error = is_connect_error


def _extract_message(body: Any, status: int) -> str:
    """Extract the error message trying multiple paths, matching
    the pattern from SesameApiException.php."""
    if not isinstance(body, dict):
        return f"Sesame API error: HTTP {status}"

    # 1. Nested: body.error.message
    error = body.get("error")
    if isinstance(error, dict) and "message" in error:
        return _normalize_message(error["message"])

    # 2. Flat: body.message -> body.error -> body.error_description
    for key in ("message", "error", "error_description"):
        if body.get(key) is not None:
            return _normalize_message(body[key])

    return f"Sesame API error: HTTP {status}"


def _extract_errors(body: Any) -> list[Any]:
    if not isinstance(body, dict):
        return []
    error = body.get("error")
    if isinstance(error, dict) and "errors" in error:
        errors = error["errors"]
    else:
        errors = body.get("errors")
    if errors is None:
        errors = []
    return errors if isinstance(errors, list) else []


def _normalize_message(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return _flatten_list(value)
    return str(value)


def _flatten_list(items: list[Any]) -> str:
    parts: list[str] = []
    for item in items:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, list):
            parts.append(_flatten_list(item))
        elif item is not None:
            parts.append(str(item))
    return ", ".join(part for part in parts if part)
