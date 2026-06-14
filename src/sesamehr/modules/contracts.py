from __future__ import annotations

from datetime import date, timedelta

from .._base import SesameModel
from ..bi import BiClient
from ..config import ResolvedConfig
from ..types import employee_filter


class Contract(SesameModel):
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    weekly_hours: float | None = None
    fte: float | None = None
    remote_work: str | None = None
    seniority_date: str | None = None
    contract_type: str | None = None
    employee_name: str | None = None


class ContractGroupCount(SesameModel):
    group: str | None = None
    count: int = 0


BASE_SELECT: list[dict[str, str]] = [
    {"field": "contract_context_contract.status", "alias": "status"},
    {"field": "contract_context_contract.start_date", "alias": "startDate"},
    {"field": "contract_context_contract.end_date", "alias": "endDate"},
    {"field": "contract_context_contract.weekly_hours", "alias": "weeklyHours"},
    {"field": "contract_context_contract.fte", "alias": "fte"},
    {"field": "contract_context_contract.remote_work", "alias": "remoteWork"},
    {"field": "contract_context_contract.seniority_date", "alias": "seniorityDate"},
    {"field": "contract_context_contract_type.name", "alias": "contractType"},
    {"field": "core_context_employee.name", "alias": "employeeName"},
]


class ContractsModule:
    """Employee contracts — list, filter by status, find expiring contracts, and get type/status breakdowns."""

    def __init__(self, bi: BiClient, config: ResolvedConfig) -> None:
        self._bi = bi
        self._config = config

    def list(
        self,
        *,
        status: str | None = None,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Contract]:
        """List contracts with optional status filter."""
        where = [*employee_filter(employee)]
        if status:
            where.append({"field": "contract_context_contract.status", "operator": "=", "value": status})

        rows = self._bi.query(
            {
                "from": "contract_context_contract",
                "select": BASE_SELECT,
                "where": where,
                "order_by": [{"field": "core_context_employee.name", "direction": "ASC"}],
                "limit": limit if limit is not None else 50,
                "offset": offset or 0,
            }
        )
        return [Contract.model_validate(row) for row in rows]

    def active(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[Contract]:
        """List only active contracts."""
        return self.list(status="active", employee=employee, limit=limit, offset=offset)

    def expiring_soon(
        self,
        days: int,
        *,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Contract]:
        """Find active contracts expiring within the next N days."""
        today = date.today()
        future = today + timedelta(days=days)

        rows = self._bi.query(
            {
                "from": "contract_context_contract",
                "select": BASE_SELECT,
                "where": [
                    *employee_filter(employee),
                    {"field": "contract_context_contract.status", "operator": "=", "value": "active"},
                    {"field": "contract_context_contract.end_date", "operator": ">=", "value": today.isoformat()},
                    {"field": "contract_context_contract.end_date", "operator": "<=", "value": future.isoformat()},
                ],
                "order_by": [{"field": "contract_context_contract.end_date", "direction": "ASC"}],
                "limit": limit if limit is not None else 50,
                "offset": offset or 0,
            }
        )
        return [Contract.model_validate(row) for row in rows]

    def by_type(self, *, employee: str | None = None, limit: int | None = None) -> list[ContractGroupCount]:
        """Count active contracts grouped by contract type."""
        rows = self._bi.query(
            {
                "from": "contract_context_contract",
                "select": [
                    {"field": "contract_context_contract_type.name", "alias": "group"},
                    {"field": "contract_context_contract.status", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [
                    *employee_filter(employee),
                    {"field": "contract_context_contract.status", "operator": "=", "value": "active"},
                ],
                "group_by": ["contract_context_contract_type.name"],
                "order_by": [{"field": "count", "direction": "DESC"}],
                "limit": limit if limit is not None else 50,
            }
        )
        return [ContractGroupCount.model_validate(row) for row in rows]

    def status_summary(self, *, employee: str | None = None) -> list[ContractGroupCount]:
        """Count contracts grouped by status (active/terminated/previous)."""
        rows = self._bi.query(
            {
                "from": "contract_context_contract",
                "select": [
                    {"field": "contract_context_contract.status", "alias": "group"},
                    {"field": "contract_context_contract.status", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [*employee_filter(employee)],
                "group_by": ["contract_context_contract.status"],
                "order_by": [{"field": "count", "direction": "DESC"}],
            }
        )
        return [ContractGroupCount.model_validate(row) for row in rows]
