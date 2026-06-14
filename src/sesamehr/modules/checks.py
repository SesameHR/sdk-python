from datetime import datetime
from typing import Any

from .._base import SesameModel
from ..bi import BiClient
from ..config import ResolvedConfig
from ..http import HttpClient
from ..types import employee_filter


class CheckEntry(SesameModel):
    date: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    seconds_worked: int = 0
    # BI returns "1" or "0" for booleans
    is_remote: str | None = None
    type: str | None = None
    employee_name: str | None = None
    department: str | None = None


class CheckAggregation(SesameModel):
    group: str | None = None
    total_seconds: int = 0
    count: int = 0


class Coordinates(SesameModel):
    latitude: float
    longitude: float


class WorkBreak(SesameModel):
    id: str | None = None
    name: str | None = None
    icon: str | None = None
    break_minutes: int = 0
    remunerated: bool = False
    active: bool = False


class CheckResult(SesameModel):
    id: str | None = None
    employee_id: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    origin: str | None = None
    created_at: str | None = None


class CheckRequestEntry(SesameModel):
    status: str | None = None
    type: str | None = None
    comment: str | None = None
    created_at: str | None = None


DEFAULT_COORDINATES = {"latitude": 0.0001, "longitude": 0.0001}

REQUEST_TIMEZONE = "Europe/Madrid"


def _build_check_timestamp(dt: str) -> dict[str, Any]:
    """Build the structured timestamp payload the /check-request-for-* endpoints expect.

    Input: a local datetime string (e.g., "2026-04-16T13:00:00" or "2026-04-16 13:00").
    The string is interpreted as local time (server TZ). For accurate results, run the
    SDK in the same timezone as REQUEST_TIMEZONE or pass a fully-qualified ISO string
    with offset.
    """
    normalized = dt if "T" in dt else dt.replace(" ", "T")
    parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    return {
        "date": int(parsed.timestamp()),
        "origin": "request",
        "timezone": REQUEST_TIMEZONE,
    }


BASE_SELECT: list[dict[str, str]] = [
    {"field": "schedule_context_check.date", "alias": "date"},
    {"field": "schedule_context_check.check_in_check_datetime", "alias": "checkIn"},
    {"field": "schedule_context_check.check_out_check_datetime", "alias": "checkOut"},
    {"field": "schedule_context_check.seconds_worked", "alias": "secondsWorked"},
    {"field": "schedule_context_check.is_remote", "alias": "isRemote"},
    {"field": "schedule_context_check.type", "alias": "type"},
    {"field": "core_context_employee.name", "alias": "employeeName"},
    {"field": "core_context_department.name", "alias": "department"},
]


class ChecksModule:
    """Time tracking — clock in/out, breaks, check history, hours aggregation, and check requests."""

    def __init__(self, bi: BiClient, http: HttpClient, config: ResolvedConfig) -> None:
        self._bi = bi
        self._http = http
        self._config = config

    # --- BI Reads ---

    def history(
        self,
        from_: str,
        to: str,
        *,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[CheckEntry]:
        """Get check entries for a date range. Returns clock-in/out times and seconds worked."""
        return self._query_checks(
            [
                *employee_filter(employee),
                {"field": "schedule_context_check.date", "operator": ">=", "value": from_},
                {"field": "schedule_context_check.date", "operator": "<=", "value": to},
            ],
            limit,
            offset,
        )

    def today(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[CheckEntry]:
        """Get today's check entries."""
        return self._query_checks(
            [
                *employee_filter(employee),
                {"field": "schedule_context_check.check_in_check_datetime", "operation": "TODAY"},
            ],
            limit,
            offset,
        )

    def this_week(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[CheckEntry]:
        """Get this week's check entries."""
        return self._query_checks(
            [
                *employee_filter(employee),
                {"field": "schedule_context_check.check_in_check_datetime", "operation": "THIS_WEEK"},
            ],
            limit,
            offset,
        )

    def this_month(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[CheckEntry]:
        """Get this month's check entries."""
        return self._query_checks(
            [
                *employee_filter(employee),
                {"field": "schedule_context_check.check_in_check_datetime", "operation": "THIS_MONTH"},
            ],
            limit,
            offset,
        )

    def remote_only(
        self,
        from_: str,
        to: str,
        *,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[CheckEntry]:
        """Get only remote check entries for a date range."""
        return self._query_checks(
            [
                *employee_filter(employee),
                {"field": "schedule_context_check.is_remote", "operator": "=", "value": "1"},
                {"field": "schedule_context_check.date", "operator": ">=", "value": from_},
                {"field": "schedule_context_check.date", "operator": "<=", "value": to},
            ],
            limit,
            offset,
        )

    def open_checks(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[CheckEntry]:
        """Get currently open checks (clocked in but not yet clocked out)."""
        return self._query_checks(
            [
                *employee_filter(employee),
                {"field": "schedule_context_check.opened", "operator": "=", "value": "1"},
            ],
            limit,
            offset,
        )

    def hours_by_employee(
        self, from_: str, to: str, *, employee: str | None = None, limit: int | None = None
    ) -> list[CheckAggregation]:
        """Aggregate total hours and check count per employee for a date range."""
        return self._aggregate_by("core_context_employee.name", from_, to, employee, limit)

    def hours_by_department(
        self, from_: str, to: str, *, employee: str | None = None, limit: int | None = None
    ) -> list[CheckAggregation]:
        """Aggregate total hours and check count per department for a date range."""
        return self._aggregate_by("core_context_department.name", from_, to, employee, limit)

    def total_hours(self, from_: str, to: str, *, employee: str | None = None) -> list[CheckAggregation]:
        """Get total hours worked and check count across all employees for a date range."""
        rows = self._bi.query(
            {
                "from": "schedule_context_check",
                "select": [
                    {"field": "schedule_context_check.seconds_worked", "aggregate": "SUM", "alias": "totalSeconds"},
                    {"field": "schedule_context_check.date", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [
                    *employee_filter(employee),
                    {"field": "schedule_context_check.date", "operator": ">=", "value": from_},
                    {"field": "schedule_context_check.date", "operator": "<=", "value": to},
                ],
            }
        )
        return [CheckAggregation.model_validate(row) for row in rows]

    def my_requests(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[CheckRequestEntry]:
        """Get the authenticated employee's pending check requests."""
        rows = self._bi.query(
            {
                "from": "schedule_context_check_request",
                "select": [
                    {"field": "schedule_context_check_request.status", "alias": "status"},
                    {"field": "schedule_context_check_request.type", "alias": "type"},
                    {"field": "schedule_context_check_request.comment", "alias": "comment"},
                    {"field": "schedule_context_check_request.created_at", "alias": "createdAt"},
                ],
                "where": [
                    *employee_filter(employee),
                    {"field": "schedule_context_check_request.status", "operator": "=", "value": "pending"},
                ],
                "order_by": [{"field": "schedule_context_check_request.created_at", "direction": "DESC"}],
                "limit": limit if limit is not None else 50,
                "offset": offset or 0,
            }
        )
        return [CheckRequestEntry.model_validate(row) for row in rows]

    # --- REST Writes ---

    def clock_in(self, coordinates: dict[str, float] | Coordinates | None = None) -> CheckResult:
        """Clock in the authenticated employee. Optionally provide GPS coordinates."""
        data = self._http.post_data(
            f"/api/v3/employees/{self._config.employee_id}/check-in",
            {"origin": "web", "coordinates": _coords(coordinates)},
        )
        return CheckResult.model_validate(data)

    def clock_out(self, coordinates: dict[str, float] | Coordinates | None = None) -> CheckResult:
        """Clock out the authenticated employee. Optionally provide GPS coordinates."""
        data = self._http.post_data(
            f"/api/v3/employees/{self._config.employee_id}/check-out",
            {"origin": "web", "coordinates": _coords(coordinates)},
        )
        return CheckResult.model_validate(data)

    def breaks(self) -> list[WorkBreak]:
        """Work breaks list (REST - not available as BI main table)."""
        data = self._http.get_data(f"/api/v3/employees/{self._config.employee_id}/work-breaks")
        return [WorkBreak.model_validate(item) for item in data]

    def pause(self, work_break_id: str, coordinates: dict[str, float] | Coordinates | None = None) -> CheckResult:
        """Start a work break (pause). Requires the break type ID from breaks()."""
        data = self._http.post_data(
            f"/api/v3/employees/{self._config.employee_id}/pause",
            {"origin": "web", "workBreakId": work_break_id, "coordinates": _coords(coordinates)},
        )
        return CheckResult.model_validate(data)

    def request_create(
        self,
        *,
        check_in: str,
        check_out: str | None = None,
        comment: str | None = None,
        type: str = "work",
        work_break_id: str | None = None,
    ) -> dict[str, Any]:
        """Request to create a new check entry (requires manager approval).
        Default type is 'work'; pass type='pause' with a work_break_id to
        request a past-day break."""
        return self._http.post_data(
            "/api/v3/check-request-for-create",
            {
                "employeeId": self._config.employee_id,
                "type": type,
                "checkIn": _build_check_timestamp(check_in),
                "checkOut": _build_check_timestamp(check_out) if check_out else None,
                "comment": comment,
                "workBreakId": work_break_id,
            },
        )

    def request_edit(
        self,
        check_id: str,
        *,
        check_in: str | None = None,
        check_out: str | None = None,
        comment: str | None = None,
    ) -> None:
        """Request to edit an existing check entry (requires manager approval)."""
        self._http.post(
            "/api/v3/check-request-for-update",
            {
                "employeeId": self._config.employee_id,
                "checkId": check_id,
                "checkType": "work",
                "checkIn": _build_check_timestamp(check_in) if check_in else None,
                "checkOut": _build_check_timestamp(check_out) if check_out else None,
                "comment": comment,
            },
        )

    def request_delete(self, check_id: str, comment: str | None = None) -> None:
        """Request to delete a check entry (requires manager approval)."""
        self._http.post(
            "/api/v3/check-request-for-delete",
            {
                "employeeId": self._config.employee_id,
                "checkId": check_id,
                "checkType": "work",
                "comment": comment,
            },
        )

    # --- Helpers ---

    def _query_checks(self, where: list[dict], limit: int | None, offset: int | None) -> list[CheckEntry]:
        rows = self._bi.query(
            {
                "from": "schedule_context_check",
                "select": BASE_SELECT,
                "where": where,
                "order_by": [{"field": "date", "direction": "DESC"}],
                "limit": limit if limit is not None else 250,
                "offset": offset or 0,
            }
        )
        return [CheckEntry.model_validate(row) for row in rows]

    def _aggregate_by(
        self, field: str, from_: str, to: str, employee: str | None, limit: int | None
    ) -> list[CheckAggregation]:
        rows = self._bi.query(
            {
                "from": "schedule_context_check",
                "select": [
                    {"field": field, "alias": "group"},
                    {"field": "schedule_context_check.seconds_worked", "aggregate": "SUM", "alias": "totalSeconds"},
                    {"field": "schedule_context_check.date", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [
                    *employee_filter(employee),
                    {"field": "schedule_context_check.date", "operator": ">=", "value": from_},
                    {"field": "schedule_context_check.date", "operator": "<=", "value": to},
                ],
                "group_by": [field],
                "order_by": [{"field": "totalSeconds", "direction": "DESC"}],
                "limit": limit if limit is not None else 250,
            }
        )
        return [CheckAggregation.model_validate(row) for row in rows]


def _coords(coordinates: dict[str, float] | Coordinates | None) -> dict[str, float]:
    if coordinates is None:
        return DEFAULT_COORDINATES
    if isinstance(coordinates, Coordinates):
        return coordinates.model_dump()
    return coordinates
