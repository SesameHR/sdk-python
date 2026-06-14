from typing import Any

from ..bi import BiClient, BiQuery
from ..config import ResolvedConfig

# Valid primary tables for BI queries
BI_TABLES = {
    "employees": "core_context_employee",
    "checks": "schedule_context_check",
    "check_requests": "schedule_context_check_request",
    "day_off_requests": "schedule_context_day_off_request",
    "days_off": "schedule_context_day_off",
    "contracts": "contract_context_contract",
    "hour_stats": "schedule_context_computed_hour_stat",
    "calendars": "schedule_context_calendar",
}

# Temporal operations for WHERE clauses
BI_TEMPORAL = {
    "today": "TODAY",
    "yesterday": "YESTERDAY",
    "this_week": "THIS_WEEK",
    "this_month": "THIS_MONTH",
    "last_month": "LAST_MONTH",
    "this_year": "THIS_YEAR",
    "last_year": "LAST_YEAR",
    "last_7_days": "LAST_7_DAYS",
    "last_30_days": "LAST_30_DAYS",
}


class ReportsModule:
    """Raw BI query builder — run custom SQL-like queries against any Sesame BI table.
    Use the BI_TABLES and BI_TEMPORAL constants."""

    def __init__(self, bi: BiClient, config: ResolvedConfig) -> None:
        self._bi = bi
        self._config = config

    def query(self, query: BiQuery | dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a raw BI query. Use BI_TABLES for table names and BI_TEMPORAL for date operations."""
        return self._bi.query(query)
