from ._base import SesameModel


class SesameConfig(SesameModel):
    """SDK credentials and connection options.

    `timeout` is in seconds (the TypeScript SDK uses milliseconds).
    """

    token: str
    region: str
    company_id: str
    employee_id: str
    base_url: str | None = None
    bi_base_url: str | None = None
    timeout: float | None = None


class ResolvedConfig(SesameModel):
    token: str
    region: str
    company_id: str
    employee_id: str
    base_url: str
    bi_base_url: str
    timeout: float


def tenant_headers(config: ResolvedConfig) -> dict[str, str]:
    """Tenant context headers the Sesame API uses to resolve "which entity is
    acting": CSID (company) + ESID (employee). The native Sesame app sends them
    on every call; without them a multi-company user's token silently resolves
    to its default employee/company, ignoring the company_id/employee_id the
    SDK was configured with (REST reads act as the wrong employee and BI
    queries return the default company's data).
    """
    headers: dict[str, str] = {}
    if config.company_id:
        headers["CSID"] = config.company_id
    if config.employee_id:
        headers["ESID"] = config.employee_id
    return headers


def resolve_config(config: SesameConfig) -> ResolvedConfig:
    return ResolvedConfig(
        token=config.token,
        region=config.region,
        company_id=config.company_id,
        employee_id=config.employee_id,
        base_url=config.base_url or f"https://back-{config.region.lower()}.sesametime.com",
        bi_base_url=config.bi_base_url or "https://gateway.sesametime.com",
        timeout=config.timeout if config.timeout is not None else 30.0,
    )
