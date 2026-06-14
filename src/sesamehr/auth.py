from typing import Any

import httpx
from pydantic import Field

from ._base import SesameModel
from ._fetch import do_fetch, validate_subdomain
from .config import SesameConfig
from .errors import SesameApiError

LOGIN_FINDER_URL = "https://login.sesametime.com"
_PRE_LOGIN_ENDPOINT = "/private/login-finder/v1/pre-login"
_LOGIN_ENDPOINT = "/api/v3/security/login"
_ME_ENDPOINT = "/api/v3/security/me-oauth"


class EmployeeEntry(SesameModel):
    id: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    company_id: str = ""
    company_name: str = ""


class LoginResult(SesameModel):
    token: str
    region: str
    employee_id: str
    company_id: str
    sdk_config: SesameConfig
    employee: EmployeeEntry
    employees: list[EmployeeEntry] = Field(default_factory=list)


def direct_login(email: str, password: str, *, transport: httpx.BaseTransport | None = None) -> LoginResult:
    """Direct login against the Sesame API.
    Same flow the SSO uses internally - no OAuth, no redirects.

    1. POST login-finder -> get region
    2. POST /api/v3/security/login -> get token
    3. GET /api/v3/security/me-oauth -> get employee details
    """
    region = _find_region(email, transport)

    subdomain = f"back-{region.lower()}"
    validate_subdomain(subdomain)
    base_url = f"https://{subdomain}.sesametime.com"
    token = _perform_login(base_url, email, password, transport)

    employees = _get_employees(base_url, token, transport)
    employee = employees[0]

    sdk_config = SesameConfig(
        token=token,
        region=region,
        company_id=employee.company_id,
        employee_id=employee.id,
    )

    return LoginResult(
        token=token,
        region=region,
        employee_id=employee.id,
        company_id=employee.company_id,
        sdk_config=sdk_config,
        employee=employee,
        employees=employees,
    )


def _find_region(email: str, transport: httpx.BaseTransport | None) -> str:
    body = do_fetch(
        f"{LOGIN_FINDER_URL}{_PRE_LOGIN_ENDPOINT}",
        method="POST",
        json_body={"email": email},
        transport=transport,
    )
    data = body.get("data") if isinstance(body, dict) else None
    region = data.get("region") if isinstance(data, dict) else None
    if not region:
        raise SesameApiError(400, {"message": "Could not determine region for this email"})
    return region


def _perform_login(base_url: str, email: str, password: str, transport: httpx.BaseTransport | None) -> str:
    body = do_fetch(
        f"{base_url}{_LOGIN_ENDPOINT}",
        method="POST",
        json_body={"email": email, "password": password},
        transport=transport,
    )
    token = body.get("data") if isinstance(body, dict) else None
    if not token:
        raise SesameApiError(401, {"message": "Invalid credentials"})
    return token


def _get_employees(base_url: str, token: str, transport: httpx.BaseTransport | None) -> list[EmployeeEntry]:
    body = do_fetch(
        f"{base_url}{_ME_ENDPOINT}",
        method="GET",
        headers={"Authorization": f"Bearer {token}"},
        transport=transport,
    )

    # me-oauth returns { data: [{ employee: { id, ... }, accumulatedSeconds, ... }] }
    raw = body.get("data") if isinstance(body, dict) else None
    entries = raw if isinstance(raw, list) else [raw]

    employees: list[EmployeeEntry] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        emp = entry.get("employee") if isinstance(entry.get("employee"), dict) else entry
        if not isinstance(emp, dict) or not emp.get("id"):
            continue
        full_name = emp.get("fullName") if isinstance(emp.get("fullName"), dict) else {}
        email_obj = emp.get("email") if isinstance(emp.get("email"), dict) else {}
        company = emp.get("companyView") if isinstance(emp.get("companyView"), dict) else {}
        employees.append(
            EmployeeEntry(
                id=emp["id"],
                first_name=full_name.get("firstName") or "",
                last_name=full_name.get("lastName") or "",
                email=email_obj.get("value") or "",
                company_id=company.get("id") or "",
                company_name=company.get("name") or "",
            )
        )

    if not employees:
        raise SesameApiError(500, {"message": "Could not retrieve employee details"})

    return employees
