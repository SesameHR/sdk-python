from pydantic import Field

from .._base import SesameModel
from ..config import ResolvedConfig
from ..http import HttpClient


class ChecksOrigin(SesameModel):
    mobile: int = 0
    web: int = 0


class ChecksOutsideOffice(SesameModel):
    inside: int = 0
    outside: int = 0


class ChecksGeo(SesameModel):
    with_: int = Field(0, alias="with")
    without: int = 0


class WorkStatsResult(SesameModel):
    seconds_worked: int = 0
    seconds_to_work: int = 0
    balance: int = 0
    worked_days: int = 0
    days_to_work: int = 0
    avg_in_seconds: int = 0
    avg_out_seconds: int = 0
    avg_work_break_seconds: int = 0
    checks_count: int = 0
    work_breaks_count: int = 0
    vacations_count: int = 0
    permissions_count: int = 0
    avg_schedule_seconds: int = 0
    checks_origin: ChecksOrigin = Field(default_factory=ChecksOrigin)
    checks_outside_office: ChecksOutsideOffice = Field(default_factory=ChecksOutsideOffice)
    checks_geo: ChecksGeo = Field(default_factory=ChecksGeo)


class WorkStatsModule:
    """Work statistics — hours worked vs expected, balance, averages, and check origin breakdowns."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def summary(self, from_: str, to: str, *, employee_id: str | None = None) -> WorkStatsResult:
        """Employee statistics via REST (same endpoint as MCP)."""
        response = self._http.post(
            "/api/v3/employees-statistics",
            {
                "employeeIds": [employee_id if employee_id is not None else self._config.employee_id],
                "from": from_,
                "to": to,
            },
        )
        return WorkStatsResult.model_validate(response["data"])
