import json

import httpx
import pytest

from sesamehr import SesameApiError, SesameSDK, direct_login, verify_auto_login_token

ME_OAUTH_PAYLOAD = {
    "data": [
        {
            "employee": {
                "id": "emp-1",
                "fullName": {"firstName": "Ana", "lastName": "García"},
                "email": {"value": "ana@company.com"},
                "companyView": {"id": "company-1", "name": "ACME"},
            }
        }
    ]
}


def login_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/private/login-finder/v1/pre-login"):
        assert json.loads(request.content) == {"email": "ana@company.com"}
        return httpx.Response(200, json={"data": {"region": "EU1"}})
    if url.endswith("/api/v3/security/login"):
        assert request.url.host == "back-eu1.sesametime.com"
        return httpx.Response(200, json={"data": "user-token"})
    if url.endswith("/api/v3/security/me-oauth"):
        assert request.headers["Authorization"] == "Bearer user-token"
        return httpx.Response(200, json=ME_OAUTH_PAYLOAD)
    return httpx.Response(404, json={"message": f"unexpected url {url}"})


def test_direct_login_full_flow():
    result = direct_login("ana@company.com", "secret", transport=httpx.MockTransport(login_handler))

    assert result.token == "user-token"
    assert result.region == "EU1"
    assert result.employee_id == "emp-1"
    assert result.company_id == "company-1"
    assert result.employee.first_name == "Ana"
    assert result.employee.email == "ana@company.com"
    assert len(result.employees) == 1
    assert result.sdk_config.token == "user-token"
    assert result.sdk_config.employee_id == "emp-1"


def test_sdk_login_builds_working_client():
    sdk = SesameSDK.login("ana@company.com", "secret", transport=httpx.MockTransport(login_handler))
    assert sdk.config.base_url == "https://back-eu1.sesametime.com"
    assert sdk.config.token == "user-token"


def test_direct_login_invalid_credentials():
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/pre-login"):
            return httpx.Response(200, json={"data": {"region": "EU1"}})
        return httpx.Response(200, json={"data": None})

    with pytest.raises(SesameApiError) as exc_info:
        direct_login("ana@company.com", "wrong", transport=httpx.MockTransport(handler))
    assert exc_info.value.status == 401


def auto_login_handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/private/external-app/v1/verify-token"):
        assert request.url.host == "back-mobile-eu1.sesametime.com"
        assert json.loads(request.content) == {"token": "single-use"}
        return httpx.Response(200, json={"data": "user-token"})
    if url.endswith("/api/v3/security/me"):
        assert request.headers["Authorization"] == "Bearer user-token"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "emp-1",
                        "userId": "account-1",
                        "firstName": "Ana",
                        "lastName": "García",
                        "email": "ana@company.com",
                        "groupId": "company-1",
                        "imageProfileURL": None,
                    }
                ]
            },
        )
    return httpx.Response(404, json={"message": f"unexpected url {url}"})


def test_auto_login_preserves_mobile_region():
    result = verify_auto_login_token(
        "single-use", "back-mobile-eu1", transport=httpx.MockTransport(auto_login_handler)
    )

    assert result.token == "user-token"
    assert result.region == "MOBILE-EU1"
    # prefers `id` (employee id) over `userId` (account id)
    assert result.employee_id == "emp-1"
    assert result.company_id == "company-1"
    assert result.profile.first_name == "Ana"


def test_auto_login_rejects_bad_subdomain():
    with pytest.raises(SesameApiError) as exc_info:
        verify_auto_login_token("tok", "evil.example.com/path")
    assert exc_info.value.status == 400
