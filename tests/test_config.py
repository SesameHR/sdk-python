from sesamehr import SesameConfig, resolve_config
from sesamehr.config import tenant_headers


def test_resolve_defaults():
    resolved = resolve_config(
        SesameConfig(token="t", region="EU1", company_id="c", employee_id="e")
    )
    assert resolved.base_url == "https://back-eu1.sesametime.com"
    assert resolved.bi_base_url == "https://gateway.sesametime.com"
    assert resolved.timeout == 30.0


def test_resolve_respects_overrides():
    resolved = resolve_config(
        SesameConfig(
            token="t",
            region="MX1",
            company_id="c",
            employee_id="e",
            base_url="https://custom.example.com",
            bi_base_url="https://bi.example.com",
            timeout=5,
        )
    )
    assert resolved.base_url == "https://custom.example.com"
    assert resolved.bi_base_url == "https://bi.example.com"
    assert resolved.timeout == 5.0


def test_resolve_preserves_mobile_region():
    resolved = resolve_config(
        SesameConfig(token="t", region="MOBILE-EU1", company_id="c", employee_id="e")
    )
    assert resolved.base_url == "https://back-mobile-eu1.sesametime.com"


def test_config_accepts_camel_case_aliases():
    config = SesameConfig(token="t", region="EU1", companyId="c", employeeId="e")
    assert config.company_id == "c"
    assert config.employee_id == "e"


def test_tenant_headers():
    resolved = resolve_config(
        SesameConfig(token="t", region="EU1", company_id="c-1", employee_id="e-1")
    )
    assert tenant_headers(resolved) == {"CSID": "c-1", "ESID": "e-1"}


def test_tenant_headers_skips_empty():
    resolved = resolve_config(
        SesameConfig(token="t", region="EU1", company_id="", employee_id="e-1")
    )
    assert tenant_headers(resolved) == {"ESID": "e-1"}
