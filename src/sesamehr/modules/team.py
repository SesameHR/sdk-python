from .._base import SesameModel
from ..bi import BiClient
from ..config import ResolvedConfig
from ..http import HttpClient


class TeamMember(SesameModel):
    name: str | None = None
    email: str | None = None
    status: str | None = None
    work_status: str | None = None
    department: str | None = None
    office: str | None = None
    job_charge: str | None = None


class TeamCheck(SesameModel):
    date: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    seconds_worked: int = 0
    is_remote: str | None = None
    type: str | None = None
    employee_name: str | None = None


class TeamRequestEntry(SesameModel):
    status: str | None = None
    type: str | None = None
    comment: str | None = None
    created_at: str | None = None
    employee_name: str | None = None


class TeamGroupCount(SesameModel):
    group: str | None = None
    count: int = 0


MEMBER_SELECT: list[dict[str, str]] = [
    {"field": "core_context_employee.name", "alias": "name"},
    {"field": "core_context_employee.email", "alias": "email"},
    {"field": "core_context_employee.status", "alias": "status"},
    {"field": "core_context_employee.work_status", "alias": "workStatus"},
    {"field": "core_context_department.name", "alias": "department"},
    {"field": "core_context_office.name", "alias": "office"},
    {"field": "core_context_job_charge.name", "alias": "jobCharge"},
]


class TeamModule:
    """Team/admin module — view team status, manage checks and approve/reject requests for your reports."""

    def __init__(self, bi: BiClient, http: HttpClient, config: ResolvedConfig) -> None:
        self._bi = bi
        self._http = http
        self._config = config

    # --- BI: Employee status ---

    def status(self, *, limit: int | None = None, offset: int | None = None) -> list[TeamMember]:
        """List all active team members with their current work status."""
        return self._query_members(
            [{"field": "core_context_employee.status", "operator": "=", "value": "active"}],
            limit,
            offset,
        )

    def working(self, *, limit: int | None = None, offset: int | None = None) -> list[TeamMember]:
        """Get team members currently working (online or remote)."""
        return self._query_members(
            [{"field": "core_context_employee.work_status", "operator": "IN", "value": ["online", "remote"]}],
            limit,
            offset,
        )

    def status_summary(self) -> list[TeamGroupCount]:
        """Count active employees grouped by work status (online/offline/paused/remote)."""
        rows = self._bi.query(
            {
                "from": "core_context_employee",
                "select": [
                    {"field": "core_context_employee.work_status", "alias": "group"},
                    {"field": "core_context_employee.name", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [{"field": "core_context_employee.status", "operator": "=", "value": "active"}],
                "group_by": ["core_context_employee.work_status"],
                "order_by": [{"field": "count", "direction": "DESC"}],
            }
        )
        return [TeamGroupCount.model_validate(row) for row in rows]

    # --- BI: Checks ---

    def employee_checks(
        self,
        employee_name: str,
        from_: str,
        to: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[TeamCheck]:
        """Get check history for a specific employee by name (partial match) in a date range."""
        rows = self._bi.query(
            {
                "from": "schedule_context_check",
                "select": [
                    {"field": "schedule_context_check.date", "alias": "date"},
                    {"field": "schedule_context_check.check_in_check_datetime", "alias": "checkIn"},
                    {"field": "schedule_context_check.check_out_check_datetime", "alias": "checkOut"},
                    {"field": "schedule_context_check.seconds_worked", "alias": "secondsWorked"},
                    {"field": "schedule_context_check.is_remote", "alias": "isRemote"},
                    {"field": "schedule_context_check.type", "alias": "type"},
                    {"field": "core_context_employee.name", "alias": "employeeName"},
                ],
                "where": [
                    {"field": "core_context_employee.name", "operator": "LIKE", "value": f"%{employee_name}%"},
                    {"field": "schedule_context_check.date", "operator": ">=", "value": from_},
                    {"field": "schedule_context_check.date", "operator": "<=", "value": to},
                ],
                "order_by": [{"field": "date", "direction": "DESC"}],
                "limit": limit if limit is not None else 250,
                "offset": offset or 0,
            }
        )
        return [TeamCheck.model_validate(row) for row in rows]

    # --- BI: Requests ---

    def check_requests(self, *, limit: int | None = None, offset: int | None = None) -> list[TeamRequestEntry]:
        """Get pending check requests from team members awaiting approval."""
        return self._query_requests("schedule_context_check_request", limit, offset)

    def vacation_requests(self, *, limit: int | None = None, offset: int | None = None) -> list[TeamRequestEntry]:
        """Get pending vacation requests from team members awaiting approval."""
        return self._query_requests("schedule_context_day_off_request", limit, offset)

    # --- REST: Check mutations ---

    def create_check(self, employee_id: str, *, check_in: str, check_out: str | None = None) -> None:
        """Create a check entry for a team member (admin action, no approval needed)."""
        self._http.post(
            "/api/v3/checks",
            {"employeeId": employee_id, "checkType": "work", "checkIn": check_in, "checkOut": check_out},
        )

    def edit_check(self, check_id: str, *, check_in: str | None = None, check_out: str | None = None) -> None:
        """Edit a team member's existing check entry (admin action)."""
        self._http.put(
            f"/api/v3/checks/{check_id}",
            {"checkType": "work", "checkIn": check_in, "checkOut": check_out},
        )

    def delete_check(self, check_id: str) -> None:
        """Delete a team member's check entry (admin action)."""
        self._http.delete(f"/api/v3/checks/{check_id}")

    # --- REST: Request approvals ---

    def approve_check_request(self, request_id: str) -> None:
        """Approve a pending check request from a team member."""
        self._http.post(f"/api/v3/accepted-check-requests/{request_id}")

    def reject_check_request(self, request_id: str) -> None:
        """Reject a pending check request from a team member."""
        self._http.post(f"/api/v3/rejected-check-requests/{request_id}")

    def approve_vacation(self, request_id: str) -> None:
        """Approve a pending vacation request from a team member."""
        self._http.post(f"/api/v3/accepted-day-off-requests/{request_id}")

    def reject_vacation(self, request_id: str) -> None:
        """Reject a pending vacation request from a team member."""
        self._http.post(f"/api/v3/rejected-day-off-requests/{request_id}")

    # --- Helpers ---

    def _query_members(self, where: list[dict], limit: int | None, offset: int | None) -> list[TeamMember]:
        rows = self._bi.query(
            {
                "from": "core_context_employee",
                "select": MEMBER_SELECT,
                "where": where,
                "order_by": [{"field": "name", "direction": "ASC"}],
                "limit": limit if limit is not None else 250,
                "offset": offset or 0,
            }
        )
        return [TeamMember.model_validate(row) for row in rows]

    def _query_requests(self, table: str, limit: int | None, offset: int | None) -> list[TeamRequestEntry]:
        rows = self._bi.query(
            {
                "from": table,
                "select": [
                    {"field": f"{table}.status", "alias": "status"},
                    {"field": f"{table}.type", "alias": "type"},
                    {"field": f"{table}.comment", "alias": "comment"},
                    {"field": f"{table}.created_at", "alias": "createdAt"},
                    {"field": "core_context_employee.name", "alias": "employeeName"},
                ],
                "where": [{"field": f"{table}.status", "operator": "=", "value": "pending"}],
                "order_by": [{"field": f"{table}.created_at", "direction": "DESC"}],
                "limit": limit if limit is not None else 50,
                "offset": offset or 0,
            }
        )
        return [TeamRequestEntry.model_validate(row) for row in rows]
