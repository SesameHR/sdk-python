from typing import Any, Union

import httpx
from pydantic import Field

from ._base import SesameModel
from ._fetch import connection_error, safe_json
from .config import ResolvedConfig, tenant_headers
from .errors import SesameApiError
from .retry import with_retry


class BiSelectField(SesameModel):
    field: str
    aggregate: str | None = None
    alias: str | None = None
    format: str | None = None


class BiWhereCondition(SesameModel):
    field: str
    operation: str | None = None
    operator: str | None = None
    value: Union[bool, int, float, str, list[str], None] = None


class BiOrderBy(SesameModel):
    field: str
    direction: str | None = None


class BiQuery(SesameModel):
    from_: str = Field(alias="from")
    select: list[BiSelectField]
    where: list[BiWhereCondition] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    order_by: list[BiOrderBy] = Field(default_factory=list)
    limit: int = 50
    offset: int = 0


def _build_body(query: BiQuery) -> dict[str, Any]:
    # The BI endpoint expects explicit nulls, so this body is sent as-is
    # (no None-dropping like the REST client does).
    return {
        "from": query.from_,
        "select": [
            {
                "field": item.field,
                "aggregate": item.aggregate,
                "alias": item.alias,
                "placeholder": None,
                "format": item.format,
            }
            for item in query.select
        ],
        "where": [_normalize_where(condition) for condition in query.where],
        "group_by": query.group_by,
        "order_by": [{"field": item.field, "direction": item.direction if item.direction is not None else "ASC"} for item in query.order_by],
        "limit": query.limit,
        "offset": query.offset,
        "periodicity": None,
        "period_from": None,
        "period_to": None,
    }


def _normalize_where(condition: BiWhereCondition) -> dict[str, Any]:
    normalized: dict[str, Any] = {"field": condition.field}
    if condition.operation:
        normalized["operation"] = condition.operation
    if condition.operator:
        normalized["operator"] = condition.operator
        if condition.value is not None:
            normalized["value"] = condition.value
    return normalized


class BiClient:
    def __init__(self, config: ResolvedConfig, client: httpx.Client) -> None:
        self._config = config
        self._client = client

    def query(self, query: BiQuery | dict[str, Any]) -> list[dict[str, Any]]:
        parsed = query if isinstance(query, BiQuery) else BiQuery.model_validate(query)
        url = f"{self._config.bi_base_url}/analytics/report-query"
        body = _build_body(parsed)
        return with_retry(lambda: self._do_fetch(url, body))

    def _do_fetch(self, url: str, body: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            response = self._client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._config.token}",
                    "x-company-id": self._config.company_id,
                    "X-Region": self._config.region,
                    **tenant_headers(self._config),
                },
                json=body,
            )
            if not response.is_success:
                raise SesameApiError(response.status_code, safe_json(response))
            return response.json()
        except SesameApiError:
            raise
        except Exception as exc:
            raise connection_error(exc) from exc
