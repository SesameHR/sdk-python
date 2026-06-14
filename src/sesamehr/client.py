import httpx

from .auth import LoginResult, direct_login
from .autologin import AutoLoginResult, verify_auto_login_token
from .bi import BiClient
from .config import ResolvedConfig, SesameConfig, resolve_config
from .http import HttpClient
from .modules.announcements import AnnouncementsModule
from .modules.checks import ChecksModule
from .modules.community import CommunityModule
from .modules.contracts import ContractsModule
from .modules.documents import DocumentsModule
from .modules.employees import EmployeesModule
from .modules.evaluations import EvaluationsModule
from .modules.expenses import ExpensesModule
from .modules.job_charges import JobChargesModule
from .modules.notifications import NotificationsModule
from .modules.recruitment import RecruitmentModule
from .modules.reports import ReportsModule
from .modules.team import TeamModule
from .modules.vacations import VacationsModule
from .modules.work_stats import WorkStatsModule


class SesameSDK:
    """Synchronous client for the Sesame HR API.

    Authenticates with a private token — no OAuth required:

        sdk = SesameSDK(token="...", region="EU1", company_id="...", employee_id="...")
        sdk.employees.working()

    Or with email + password (same flow the SSO uses internally):

        sdk = SesameSDK.login("user@company.com", "****")
    """

    def __init__(
        self,
        config: SesameConfig | None = None,
        *,
        token: str | None = None,
        region: str | None = None,
        company_id: str | None = None,
        employee_id: str | None = None,
        base_url: str | None = None,
        bi_base_url: str | None = None,
        timeout: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if config is None:
            config = SesameConfig(
                token=token,
                region=region,
                company_id=company_id,
                employee_id=employee_id,
                base_url=base_url,
                bi_base_url=bi_base_url,
                timeout=timeout,
            )
        self.config: ResolvedConfig = resolve_config(config)
        self._client = httpx.Client(timeout=self.config.timeout, transport=transport)

        http = HttpClient(self.config, self._client)
        bi = BiClient(self.config, self._client)

        self.employees = EmployeesModule(bi, http, self.config)
        self.checks = ChecksModule(bi, http, self.config)
        self.vacations = VacationsModule(bi, http, self.config)
        self.work_stats = WorkStatsModule(http, self.config)
        self.evaluations = EvaluationsModule(http, self.config)
        self.documents = DocumentsModule(http, self.config)
        self.expenses = ExpensesModule(http, self.config)
        self.announcements = AnnouncementsModule(http, self.config)
        self.job_charges = JobChargesModule(http, self.config)
        self.recruitment = RecruitmentModule(http, self.config)
        self.team = TeamModule(bi, http, self.config)
        self.reports = ReportsModule(bi, self.config)
        self.contracts = ContractsModule(bi, self.config)
        self.notifications = NotificationsModule(http, self.config)
        self.community = CommunityModule(http, self.config)

    @classmethod
    def login(cls, email: str, password: str, *, transport: httpx.BaseTransport | None = None) -> "SesameSDK":
        """Login with email + password directly against the Sesame API.
        No OAuth, no redirects, no client registration needed.

            sdk = SesameSDK.login("user@company.com", "****")
            employees = sdk.employees.working()
        """
        result = direct_login(email, password, transport=transport)
        return cls(result.sdk_config, transport=transport)

    @classmethod
    def login_with_details(
        cls, email: str, password: str, *, transport: httpx.BaseTransport | None = None
    ) -> tuple["SesameSDK", LoginResult]:
        """Login and return both the SDK instance and the login details."""
        details = direct_login(email, password, transport=transport)
        return cls(details.sdk_config, transport=transport), details

    @classmethod
    def auto_login(cls, token: str, region: str, *, transport: httpx.BaseTransport | None = None) -> "SesameSDK":
        """Auto-login using a single-use token from a Sesame HR redirect.

            # URL: https://myapp.com/?token=abc123&sesameRegion=back-eu1
            sdk = SesameSDK.auto_login("abc123", "back-eu1")
        """
        result = verify_auto_login_token(token, region, transport=transport)
        return cls(result.sdk_config, transport=transport)

    @classmethod
    def auto_login_with_details(
        cls, token: str, region: str, *, transport: httpx.BaseTransport | None = None
    ) -> tuple["SesameSDK", AutoLoginResult]:
        """Auto-login and return both the SDK instance and the profile details."""
        details = verify_auto_login_token(token, region, transport=transport)
        return cls(details.sdk_config, transport=transport), details

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SesameSDK":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
