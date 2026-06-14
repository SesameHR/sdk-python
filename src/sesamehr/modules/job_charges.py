from __future__ import annotations

from .._base import SesameModel
from ..config import ResolvedConfig
from ..http import HttpClient
from ..types import Paginated


class JobCharge(SesameModel):
    id: str | None = None
    name: str | None = None
    description: str | None = None
    children: list[JobCharge] | None = None


class JobChargeEmployee(SesameModel):
    id: str | None = None
    employee_id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class JobChargesModule:
    """Job positions/charges — list positions, view details and assigned employees."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def list(
        self,
        *,
        name: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ) -> Paginated[JobCharge]:
        """List job positions (paginated). Optionally filter by name."""
        params = {
            "limit": limit if limit is not None else 20,
            "page": page if page is not None else 1,
            "orderBy": "name asc",
        }
        if name:
            params["name[contains]"] = name
        response = self._http.get("/private/core/v3/job-charge", params)
        return Paginated[JobCharge].model_validate(response)

    def detail(self, job_charge_id: str, with_children: bool = False) -> JobCharge:
        """Get job position details by ID. Optionally include child positions."""
        params = {"withChildren": True} if with_children else None
        data = self._http.get_data(f"/private/core/v3/job-charge/{job_charge_id}", params)
        return JobCharge.model_validate(data)

    def employees(
        self,
        job_charge_id: str,
        *,
        limit: int | None = None,
        page: int | None = None,
    ) -> Paginated[JobChargeEmployee]:
        """List employees assigned to a specific job position (paginated)."""
        response = self._http.get(
            f"/private/core/v3/employee-job-charge/{job_charge_id}/employees",
            {"limit": limit if limit is not None else 20, "page": page if page is not None else 1},
        )
        return Paginated[JobChargeEmployee].model_validate(response)
