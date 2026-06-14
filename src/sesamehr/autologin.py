import re
from typing import Any

import httpx
from pydantic import Field

from ._base import SesameModel
from ._fetch import do_fetch, validate_subdomain
from .config import SesameConfig
from .errors import SesameApiError

_VERIFY_TOKEN_ENDPOINT = "/private/external-app/v1/verify-token"
_ME_ENDPOINT = "/api/v3/security/me"


class AutoLoginProfile(SesameModel):
    id: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    company_id: str = ""
    image_profile_url: str | None = Field(None, alias="imageProfileURL")


class AutoLoginResult(SesameModel):
    token: str
    region: str
    employee_id: str
    company_id: str
    sdk_config: SesameConfig
    profile: AutoLoginProfile


def verify_auto_login_token(
    token: str,
    region: str,
    *,
    transport: httpx.BaseTransport | None = None,
) -> AutoLoginResult:
    """Verify an auto-login token from an external Sesame redirect.

    Flow (mirrors sesame-kitchen SesameAuthController::autoLogin):
    1. POST /private/external-app/v1/verify-token -> user token
    2. GET /api/v3/security/me -> employee profile

    `region` is the full subdomain (e.g. "back-eu1", "back-mx1",
    "back-mobile-eu1", ...) — whatever the redirect URL passes as
    `sesameRegion` (lowercased). NOT the region code.
    """
    validate_subdomain(region)

    base_url = f"https://{region}.sesametime.com"

    user_token = _exchange_token(base_url, token, transport)
    profile = _get_profile(base_url, user_token, transport)

    # Extract the region code from the subdomain by stripping only the `back-`
    # prefix. Datacenter-agnostic: "back-eu1" -> "EU1", "back-mobile-eu1" ->
    # "MOBILE-EU1". The `mobile-` segment is preserved so resolve_config()
    # reconstructs the correct subdomain (back-mobile-<id>).
    region_code = re.sub(r"^back-", "", region, flags=re.IGNORECASE).upper()

    sdk_config = SesameConfig(
        token=user_token,
        region=region_code,
        company_id=profile.company_id,
        employee_id=profile.id,
    )

    return AutoLoginResult(
        token=user_token,
        region=region_code,
        employee_id=profile.id,
        company_id=profile.company_id,
        sdk_config=sdk_config,
        profile=profile,
    )


def _exchange_token(base_url: str, token: str, transport: httpx.BaseTransport | None) -> str:
    body = do_fetch(
        f"{base_url}{_VERIFY_TOKEN_ENDPOINT}",
        method="POST",
        json_body={"token": token},
        transport=transport,
    )
    user_token = body.get("data") if isinstance(body, dict) else None
    if not user_token or not isinstance(user_token, str):
        raise SesameApiError(401, {"message": "Token verification failed"})
    return user_token


def _get_profile(base_url: str, user_token: str, transport: httpx.BaseTransport | None) -> AutoLoginProfile:
    body = do_fetch(
        f"{base_url}{_ME_ENDPOINT}",
        method="GET",
        headers={"Authorization": f"Bearer {user_token}"},
        transport=transport,
    )

    # /api/v3/security/me returns either:
    #   - { data: { id, ... } }     (standard backend)
    #   - { data: [{ id, ... }] }   (mobile backend, e.g. back-mobile-eu1)
    # The mobile shape also exposes `userId` (account id) — always prefer `id`
    # (employee id), since `userId` is not accepted by /api/v3/employees/{id}/*.
    raw: Any = body.get("data") if isinstance(body, dict) else None
    record = raw[0] if isinstance(raw, list) and raw else raw
    if not isinstance(record, dict) or not record.get("id"):
        raise SesameApiError(500, {"message": "Could not retrieve employee profile"})

    return AutoLoginProfile(
        id=record["id"],
        first_name=record.get("firstName") or "",
        last_name=record.get("lastName") or "",
        email=record.get("email") or "",
        company_id=record.get("groupId") or "",
        image_profile_url=record.get("imageProfileURL"),
    )
