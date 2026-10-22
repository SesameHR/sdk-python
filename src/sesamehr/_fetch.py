"""Shared low-level HTTP used by the auth flows (direct_login, auto-login)."""

import re
from typing import Any

import httpx

from .errors import SesameApiError, SesameConnectionError
from .retry import with_retry

_SUBDOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")


def validate_subdomain(value: str) -> None:
    """Validate that a string is a safe subdomain (SSRF prevention)."""
    if not _SUBDOMAIN_PATTERN.match(value):
        raise SesameApiError(400, {"message": f"Invalid subdomain format: {value}"})


def safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return None


def connection_error(exc: Exception) -> SesameConnectionError:
    if isinstance(exc, httpx.TimeoutException):
        return SesameConnectionError(str(exc) or "request timed out", is_timeout=True)
    return SesameConnectionError(
        str(exc) or type(exc).__name__, is_connect_error=isinstance(exc, httpx.ConnectError)
    )


def do_fetch(
    url: str,
    *,
    method: str,
    json_body: Any = None,
    headers: dict[str, str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> Any:
    """Wraps an HTTP call with retry, timeout, JSON parsing, and error mapping."""

    def attempt() -> Any:
        try:
            with httpx.Client(timeout=30.0, transport=transport) as client:
                response = client.request(
                    method,
                    url,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        **(headers or {}),
                    },
                    json=json_body,
                )
            if not response.is_success:
                raise SesameApiError(response.status_code, safe_json(response))
            return response.json()
        except SesameApiError:
            raise
        except Exception as exc:
            raise connection_error(exc) from exc

    return with_retry(attempt)
