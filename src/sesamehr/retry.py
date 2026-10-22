import time
from typing import Any, Callable, TypeVar

from .errors import SesameApiError, SesameConnectionError

T = TypeVar("T")


def _is_timeout_error(error: Exception) -> bool:
    if isinstance(error, SesameConnectionError):
        if error.is_timeout:
            return True
        message = str(error)
        return "aborted" in message or "timeout" in message
    return False


def default_should_retry(error: Exception) -> bool:
    """Default retry predicate:
    - Connection failures -> retry (except timeouts)
    - Server errors (5xx) -> retry
    - Timeouts -> do NOT retry (would just timeout again)
    - Client errors (4xx) -> do NOT retry
    """
    if _is_timeout_error(error):
        return False
    if isinstance(error, SesameConnectionError):
        return True
    if isinstance(error, SesameApiError) and error.status is not None and error.status >= 500:
        return True
    return False


def retry_if_not_sent(error: Exception) -> bool:
    """Retry predicate for requests that are not safe to repeat (POST).

    Retries only when the connection could not be opened, so the server never
    saw the request. A 5xx, a dropped connection or an unreadable reply can
    arrive after the server has already acted (clocked in, uploaded, approved),
    and sending the POST again would do it twice.
    """
    return (
        isinstance(error, SesameConnectionError)
        and error.is_connect_error
        and not _is_timeout_error(error)
    )


def with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 2,
    delay: float = 0.5,
    should_retry: Callable[[Exception], bool] | None = None,
) -> T:
    """Execute a function with retry logic.

    Mirrors SesameClient.php: 2 retries, 500ms delay,
    retries on connection errors and 5xx only.
    """
    predicate = should_retry or default_should_retry
    last_error: Any = None

    for attempt in range(attempts + 1):
        try:
            return fn()
        except Exception as error:
            last_error = error
            if attempt < attempts and predicate(error):
                time.sleep(delay)
                continue
            raise

    raise last_error  # pragma: no cover - unreachable
