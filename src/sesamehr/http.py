from typing import Any

import httpx

from ._fetch import connection_error, safe_json
from .config import ResolvedConfig, tenant_headers
from .errors import SesameApiError
from .retry import with_retry


def _to_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _build_params(params: dict[str, Any] | None) -> list[tuple[str, str]] | None:
    """Query string building, matching the TS SDK: skip None, arrays as key[]."""
    if not params:
        return None
    items: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            items.extend((f"{key}[]", _to_str(item)) for item in value)
        else:
            items.append((key, _to_str(value)))
    return items or None


def _drop_none(value: Any) -> Any:
    """JSON.stringify drops `undefined` values; mirror that by dropping None."""
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


class HttpClient:
    def __init__(self, config: ResolvedConfig, client: httpx.Client) -> None:
        self._config = config
        self._client = client

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def get_data(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET and unwrap the { data: ... } response."""
        return self.get(path, params)["data"]

    def post(self, path: str, body: Any = None) -> Any:
        return self._request("POST", path, body=body)

    def post_data(self, path: str, body: Any = None) -> Any:
        """POST and unwrap the { data: ... } response."""
        return self.post(path, body)["data"]

    def put(self, path: str, body: Any = None) -> Any:
        return self._request("PUT", path, body=body)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)

    def upload(self, path: str, *, data: dict[str, Any] | None = None, files: dict[str, Any] | None = None) -> Any:
        """POST multipart/form-data. `files` follows the httpx convention:
        {"document": file} or {"document": (filename, file)}."""
        url = f"{self._config.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._config.token}",
            "Accept": "application/json",
            **tenant_headers(self._config),
        }
        # FormData in the TS SDK always produces multipart, even with no binary
        # part — mirror that by encoding plain fields as multipart fields when
        # there is no file (httpx would otherwise fall back to urlencoded).
        if not files:
            files = {key: (None, _to_str(value)) for key, value in (data or {}).items()}
            data = None
        return with_retry(lambda: self._send("POST", url, headers=headers, data=data, files=files))

    def _request(self, method: str, path: str, *, body: Any = None, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._config.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._config.token}",
            "Accept": "application/json",
            **tenant_headers(self._config),
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        json_body = _drop_none(body) if body is not None else None
        query = _build_params(params)
        return with_retry(lambda: self._send(method, url, headers=headers, params=query, json_body=json_body))

    def _send(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: list[tuple[str, str]] | None = None,
        json_body: Any = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._client.request(
                method, url, headers=headers, params=params, json=json_body, data=data, files=files
            )
            if not response.is_success:
                raise SesameApiError(response.status_code, safe_json(response))
            if not response.content:
                return None
            return response.json()
        except SesameApiError:
            raise
        except Exception as exc:
            raise connection_error(exc) from exc
