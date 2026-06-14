from datetime import date
from typing import Any

from .._base import SesameModel
from ..bi import BiClient
from ..config import ResolvedConfig
from ..http import HttpClient
from ..types import employee_filter


class VacationCalendar(SesameModel):
    year: int | None = None
    max_days_off: float | None = None
    remaining_days_off: float | None = None
    calendar_type: str | None = None
    employee_name: str | None = None


class DayOff(SesameModel):
    date: str | None = None
    name: str | None = None
    seconds: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    employee_name: str | None = None
    absence_type: str | None = None


class DayOffRequest(SesameModel):
    status: str | None = None
    type: str | None = None
    comment: str | None = None
    created_at: str | None = None
    employee_name: str | None = None


class DayOffGroupCount(SesameModel):
    group: str | None = None
    count: int = 0


class VacationsModule:
    """Vacation and absence management — calendars, day-off history, pending requests, and vacation booking."""

    def __init__(self, bi: BiClient, http: HttpClient, config: ResolvedConfig) -> None:
        self._bi = bi
        self._http = http
        self._config = config

    # --- BI: schedule_context_calendar ---

    def calendars(
        self,
        *,
        year: int | None = None,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[VacationCalendar]:
        """Get vacation calendars showing max and remaining days off per employee."""
        where: list[dict] = [
            *employee_filter(employee),
            {"field": "schedule_context_calendar.calendar_type_type", "operator": "=", "value": "vacation"},
        ]
        if year:
            where.append({"field": "schedule_context_calendar.year", "operator": "=", "value": str(year)})

        rows = self._bi.query(
            {
                "from": "schedule_context_calendar",
                "select": [
                    {"field": "schedule_context_calendar.year", "alias": "year"},
                    {"field": "schedule_context_calendar.max_days_off", "alias": "maxDaysOff"},
                    {"field": "schedule_context_calendar.remaining_days_off", "alias": "remainingDaysOff"},
                    {"field": "schedule_context_calendar.calendar_type_type", "alias": "calendarType"},
                    {"field": "core_context_employee.name", "alias": "employeeName"},
                ],
                "where": where,
                "order_by": [{"field": "core_context_employee.name", "direction": "ASC"}],
                "limit": limit if limit is not None else 500,
                "offset": offset or 0,
            }
        )
        return [VacationCalendar.model_validate(row) for row in rows]

    def balance_by_employee(
        self,
        *,
        year: int | None = None,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[VacationCalendar]:
        """Get vacation balance per employee for a specific year (defaults to current year)."""
        return self.calendars(
            year=year if year is not None else date.today().year,
            employee=employee,
            limit=limit,
            offset=offset,
        )

    # --- BI: schedule_context_day_off ---

    def history(
        self,
        from_: str,
        to: str,
        *,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[DayOff]:
        """Get day-off history for a date range. Includes absence type, start/end times."""
        rows = self._bi.query(
            {
                "from": "schedule_context_day_off",
                "select": [
                    {"field": "schedule_context_day_off.date", "alias": "date"},
                    {"field": "schedule_context_day_off.name", "alias": "name"},
                    {"field": "schedule_context_day_off.seconds", "alias": "seconds"},
                    {"field": "schedule_context_day_off.start_time", "alias": "startTime"},
                    {"field": "schedule_context_day_off.end_time", "alias": "endTime"},
                    {"field": "core_context_employee.name", "alias": "employeeName"},
                    {"field": "schedule_context_absence_type.name", "alias": "absenceType"},
                ],
                "where": [
                    *employee_filter(employee),
                    {"field": "schedule_context_day_off.date", "operator": ">=", "value": from_},
                    {"field": "schedule_context_day_off.date", "operator": "<=", "value": to},
                ],
                "order_by": [{"field": "date", "direction": "DESC"}],
                "limit": limit if limit is not None else 250,
                "offset": offset or 0,
            }
        )
        return [DayOff.model_validate(row) for row in rows]

    def by_type(
        self,
        from_: str,
        to: str,
        *,
        employee: str | None = None,
        limit: int | None = None,
    ) -> list[DayOffGroupCount]:
        """Count days off grouped by absence type for a date range."""
        rows = self._bi.query(
            {
                "from": "schedule_context_day_off",
                "select": [
                    {"field": "schedule_context_absence_type.name", "alias": "group"},
                    {"field": "schedule_context_day_off.date", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [
                    *employee_filter(employee),
                    {"field": "schedule_context_day_off.date", "operator": ">=", "value": from_},
                    {"field": "schedule_context_day_off.date", "operator": "<=", "value": to},
                ],
                "group_by": ["schedule_context_absence_type.name"],
                "order_by": [{"field": "count", "direction": "DESC"}],
                "limit": limit if limit is not None else 50,
            }
        )
        return [DayOffGroupCount.model_validate(row) for row in rows]

    # --- BI: schedule_context_day_off_request ---

    def pending_requests(
        self,
        *,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[DayOffRequest]:
        """Get pending day-off requests awaiting approval."""
        return self._query_requests(
            [
                *employee_filter(employee),
                {"field": "schedule_context_day_off_request.status", "operator": "=", "value": "pending"},
            ],
            limit,
            offset,
        )

    def requests_by_employee(
        self,
        *,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[DayOffGroupCount]:
        """Count pending day-off requests grouped by employee."""
        rows = self._bi.query(
            {
                "from": "schedule_context_day_off_request",
                "select": [
                    {"field": "core_context_employee.name", "alias": "group"},
                    {"field": "schedule_context_day_off_request.status", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [
                    *employee_filter(employee),
                    {"field": "schedule_context_day_off_request.status", "operator": "=", "value": "pending"},
                ],
                "group_by": ["core_context_employee.name"],
                "order_by": [{"field": "count", "direction": "DESC"}],
                "limit": limit if limit is not None else 100,
                "offset": offset or 0,
            }
        )
        return [DayOffGroupCount.model_validate(row) for row in rows]

    # --- REST Writes ---

    def request(self, *, calendar_id: str, dates: list[str], comment: str | None = None) -> dict[str, Any]:
        """Submit a vacation request for specific dates. Requires a calendar_id from calendars()."""
        return self._http.post_data(
            "/api/v3/day-off-requests",
            {
                "employeeId": self._config.employee_id,
                "calendarId": calendar_id,
                "dates": dates,
                "comment": comment,
            },
        )

    def cancel(self, request_id: str) -> None:
        """Cancel a previously submitted vacation request."""
        self._http.delete(f"/api/v3/day-off-requests/{request_id}")

    # --- Helper ---

    def _query_requests(self, where: list[dict], limit: int | None, offset: int | None) -> list[DayOffRequest]:
        rows = self._bi.query(
            {
                "from": "schedule_context_day_off_request",
                "select": [
                    {"field": "schedule_context_day_off_request.status", "alias": "status"},
                    {"field": "schedule_context_day_off_request.type", "alias": "type"},
                    {"field": "schedule_context_day_off_request.comment", "alias": "comment"},
                    {"field": "schedule_context_day_off_request.created_at", "alias": "createdAt"},
                    {"field": "core_context_employee.name", "alias": "employeeName"},
                ],
                "where": where,
                "order_by": [{"field": "schedule_context_day_off_request.created_at", "direction": "DESC"}],
                "limit": limit if limit is not None else 50,
                "offset": offset or 0,
            }
        )
        return [DayOffRequest.model_validate(row) for row in rows]
