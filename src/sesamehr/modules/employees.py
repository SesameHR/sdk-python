from __future__ import annotations

from typing import Any, Union

from pydantic import Field

from .._base import SesameModel
from ..bi import BiClient
from ..config import ResolvedConfig
from ..http import HttpClient
from ..types import employee_filter


class Employee(SesameModel):
    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    status: str | None = None
    work_status: str | None = None
    department: str | None = None
    office: str | None = None
    job_charge: str | None = None
    code: Union[int, str, None] = None
    image_profile_url: str | None = Field(None, alias="imageProfileURL")


class EmployeeGroupCount(SesameModel):
    group: str | None = None
    count: int = 0


class EntityPermission(SesameModel):
    """A granular per-section permission grant returned by /me (e.g. payroll, registration)."""

    id: str | None = None
    # Permission scope, e.g. "payroll.complements", "payroll.registration".
    section: str | None = None
    # Entity the grant is scoped to (the employee/department/office id).
    entity_reference_id: str | None = None
    # Entity kind, e.g. "employee".
    entity_reference_type: str | None = None
    read: bool = False
    write: bool = False
    admin: bool = False


class EntityRole(SesameModel):
    """A custom role assigned per entity. Empty for built-in roles (owner/admin/etc.);
    populated when the company defines custom roles. Shape is left open since it
    varies by configuration — common fields are typed, the rest pass through
    via `model_extra`."""

    id: str | None = None
    name: str | None = None
    entity_reference_id: str | None = None
    entity_reference_type: str | None = None


class PermissionVisibilities(SesameModel):
    """Feature-visibility flags returned by /me. Well-known keys are typed for
    autocomplete; the rest pass through via `model_extra`, mirroring the TS
    index signature (`[key: string]: boolean | undefined`)."""

    vacations: bool | None = None
    other_employees_hours: bool | None = None
    other_employees_extra_hours: bool | None = None
    whosin: bool | None = None
    timeline: bool | None = None
    document: bool | None = None
    shift: bool | None = None
    timer: bool | None = None
    employee_view_other_vacations: bool | None = None
    coworkers: bool | None = None
    statistics: bool | None = None
    expenses: bool | None = None
    show_organization_chart: bool | None = None
    birthday_visibility: bool | None = None


class MeProfile(SesameModel):
    id: str | None = None
    work_status: str | None = None
    status: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_id: str | None = None
    last_check_in: str | None = None
    last_check_out: str | None = None
    gender: str | None = None
    identity_number_type: str | None = None
    nif: str | None = None
    date_of_birth: str | None = None
    phone: str | None = None
    image_profile_url: str | None = Field(None, alias="imageProfileURL")

    # --- Roles & permissions (returned by /api/v3/security/me) ---
    # Effective top-level role, e.g. "owner", "admin", "supervisor", "basic".
    highest_role: str | None = None
    highest_role_type: str | None = None
    # Custom roles assigned to this employee (empty for built-in roles).
    entity_roles: list[EntityRole] | None = None
    # All custom roles in scope, including inherited ones.
    all_entity_roles: list[EntityRole] | None = None
    # Granular per-section read/write/admin grants.
    entity_permissions: list[EntityPermission] | None = None
    # Feature-visibility flags keyed by feature name.
    permission_visibilities: PermissionVisibilities | None = None
    is_super_admin: bool | None = None
    is_group_owner: bool | None = None
    is_reseller_admin: bool | None = None
    is_validator: bool | None = None
    is_expense_team_validator: bool | None = None
    public_api: bool | None = None


BASE_SELECT: list[dict[str, str]] = [
    {"field": "core_context_employee.name", "alias": "name"},
    {"field": "core_context_employee.first_name", "alias": "firstName"},
    {"field": "core_context_employee.last_name", "alias": "lastName"},
    {"field": "core_context_employee.email", "alias": "email"},
    {"field": "core_context_employee.phone", "alias": "phone"},
    {"field": "core_context_employee.status", "alias": "status"},
    {"field": "core_context_employee.work_status", "alias": "workStatus"},
    {"field": "core_context_department.name", "alias": "department"},
    {"field": "core_context_office.name", "alias": "office"},
    {"field": "core_context_job_charge.name", "alias": "jobCharge"},
    {"field": "core_context_employee.code", "alias": "code"},
    {"field": "core_context_employee.image_profile_url", "alias": "imageProfileURL"},
]


class EmployeesModule:
    """Manage company employees — list, filter by status/department, search, and get counts."""

    def __init__(self, bi: BiClient, http: HttpClient, config: ResolvedConfig) -> None:
        self._bi = bi
        self._http = http
        self._config = config

    def list(
        self,
        *,
        status: str | None = None,
        department: str | None = None,
        office: str | None = None,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Employee]:
        """List employees with optional filters by status, department, or office."""
        where = [*employee_filter(employee)]
        if status:
            where.append({"field": "core_context_employee.status", "operator": "=", "value": status})
        if department:
            where.append({"field": "core_context_department.name", "operator": "LIKE", "value": f"%{department}%"})
        if office:
            where.append({"field": "core_context_office.name", "operator": "LIKE", "value": f"%{office}%"})
        return self._query_employees(where, limit, offset)

    def working(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[Employee]:
        """Get employees currently working (online or remote)."""
        return self._query_employees(
            [
                *employee_filter(employee),
                {"field": "core_context_employee.work_status", "operator": "IN", "value": ["online", "remote"]},
            ],
            limit,
            offset,
        )

    def on_break(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[Employee]:
        """Get employees currently on a break (paused)."""
        return self._query_employees(
            [
                *employee_filter(employee),
                {"field": "core_context_employee.work_status", "operator": "=", "value": "paused"},
            ],
            limit,
            offset,
        )

    def remote(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[Employee]:
        """Get employees currently working remotely."""
        return self._query_employees(
            [
                *employee_filter(employee),
                {"field": "core_context_employee.work_status", "operator": "=", "value": "remote"},
            ],
            limit,
            offset,
        )

    def offline(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[Employee]:
        """Get employees currently offline (not clocked in)."""
        return self._query_employees(
            [
                *employee_filter(employee),
                {"field": "core_context_employee.work_status", "operator": "=", "value": "offline"},
            ],
            limit,
            offset,
        )

    def search(self, query: str, *, limit: int | None = None, offset: int | None = None) -> list[Employee]:
        """Search employees by name (partial match)."""
        return self._query_employees(
            [{"field": "core_context_employee.name", "operator": "LIKE", "value": f"%{query}%"}],
            limit,
            offset,
        )

    def by_department(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[EmployeeGroupCount]:
        """Count active employees grouped by department."""
        return self._count_grouped_by("core_context_department.name", employee, limit, offset)

    def by_office(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[EmployeeGroupCount]:
        """Count active employees grouped by office."""
        return self._count_grouped_by("core_context_office.name", employee, limit, offset)

    def by_job_charge(self, *, employee: str | None = None, limit: int | None = None, offset: int | None = None) -> list[EmployeeGroupCount]:
        """Count active employees grouped by job position."""
        return self._count_grouped_by("core_context_job_charge.name", employee, limit, offset)

    def count(self) -> list[EmployeeGroupCount]:
        """Count employees grouped by status (active/inactive)."""
        return self._count_grouped_by("core_context_employee.status")

    def me(self) -> MeProfile:
        """Full profile of the authenticated employee (REST).

        Returns work_status ("online" | "offline" | "paused" | "remote"), status,
        last check, and the employee's roles & permissions (`highest_role`,
        `entity_permissions`, `permission_visibilities`, and capability flags
        like `is_group_owner`/`is_validator`).
        """
        data = self._http.get_data("/api/v3/security/me")
        # Endpoint returns an array with one entry — unwrap it
        record = data[0] if isinstance(data, list) else data
        return MeProfile.model_validate(record)

    # --- Helpers ---

    def _query_employees(self, where: list[dict], limit: int | None, offset: int | None) -> list[Employee]:
        rows = self._bi.query(
            {
                "from": "core_context_employee",
                "select": BASE_SELECT,
                "where": where,
                "order_by": [{"field": "name", "direction": "ASC"}],
                "limit": limit if limit is not None else 250,
                "offset": offset or 0,
            }
        )
        return [Employee.model_validate(row) for row in rows]

    def _count_grouped_by(
        self,
        field: str,
        employee: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[EmployeeGroupCount]:
        rows = self._bi.query(
            {
                "from": "core_context_employee",
                "select": [
                    {"field": field, "alias": "group"},
                    {"field": "core_context_employee.name", "aggregate": "COUNT", "alias": "count"},
                ],
                "where": [
                    {"field": "core_context_employee.status", "operator": "=", "value": "active"},
                    *employee_filter(employee),
                ],
                "group_by": [field],
                "order_by": [{"field": "count", "direction": "DESC"}],
                "limit": limit if limit is not None else 100,
                "offset": offset or 0,
            }
        )
        return [EmployeeGroupCount.model_validate(row) for row in rows]
