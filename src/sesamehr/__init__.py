from .auth import EmployeeEntry, LoginResult, direct_login
from .autologin import AutoLoginProfile, AutoLoginResult, verify_auto_login_token
from .bi import BiClient, BiOrderBy, BiQuery, BiSelectField, BiWhereCondition
from .client import SesameSDK
from .config import ResolvedConfig, SesameConfig, resolve_config
from .errors import SesameApiError, SesameConnectionError, SesameError
from .http import HttpClient
from .modules.announcements import Announcement, AnnouncementsModule
from .modules.checks import (
    CheckAggregation,
    CheckEntry,
    CheckRequestEntry,
    CheckResult,
    ChecksModule,
    Coordinates,
    WorkBreak,
)
from .modules.community import (
    Channel,
    Comment,
    CommunityAuthor,
    CommunityMeta,
    CommunityModule,
    CommunityPage,
    Post,
    PostChannelRef,
    Reaction,
)
from .modules.contracts import Contract, ContractGroupCount, ContractsModule
from .modules.documents import Directory, DocumentsModule, SesameDocument
from .modules.employees import (
    Employee,
    EmployeeGroupCount,
    EmployeesModule,
    EntityPermission,
    EntityRole,
    MeProfile,
    PermissionVisibilities,
)
from .modules.evaluations import Evaluation, EvaluationResults, EvaluationsModule
from .modules.expenses import Expense, ExpenseCategory, ExpensePage, ExpensesModule
from .modules.job_charges import JobCharge, JobChargeEmployee, JobChargesModule
from .modules.notifications import NotificationsModule
from .modules.recruitment import Candidate, RecruitmentModule, Vacancy, VacancyTotals
from .modules.reports import BI_TABLES, BI_TEMPORAL, ReportsModule
from .modules.team import TeamCheck, TeamGroupCount, TeamMember, TeamModule, TeamRequestEntry
from .modules.vacations import DayOff, DayOffGroupCount, DayOffRequest, VacationCalendar, VacationsModule
from .modules.work_stats import WorkStatsModule, WorkStatsResult
from .retry import with_retry
from .types import Paginated, PaginationMeta, employee_filter

__version__ = "0.1.0"

__all__ = [
    # Client
    "SesameSDK",
    # Auth
    "direct_login",
    "EmployeeEntry",
    "LoginResult",
    # Autologin
    "verify_auto_login_token",
    "AutoLoginProfile",
    "AutoLoginResult",
    # Config
    "SesameConfig",
    "ResolvedConfig",
    "resolve_config",
    # Shared types
    "Paginated",
    "PaginationMeta",
    "employee_filter",
    # Errors
    "SesameError",
    "SesameApiError",
    "SesameConnectionError",
    # Clients
    "HttpClient",
    "BiClient",
    "BiQuery",
    "BiSelectField",
    "BiWhereCondition",
    "BiOrderBy",
    # Retry
    "with_retry",
    # Modules
    "EmployeesModule",
    "ChecksModule",
    "VacationsModule",
    "WorkStatsModule",
    "EvaluationsModule",
    "DocumentsModule",
    "ExpensesModule",
    "AnnouncementsModule",
    "JobChargesModule",
    "RecruitmentModule",
    "TeamModule",
    "ReportsModule",
    "BI_TABLES",
    "BI_TEMPORAL",
    "ContractsModule",
    "NotificationsModule",
    "CommunityModule",
    # Module models
    "Employee",
    "EmployeeGroupCount",
    "MeProfile",
    "EntityPermission",
    "EntityRole",
    "PermissionVisibilities",
    "CheckEntry",
    "CheckAggregation",
    "CheckResult",
    "CheckRequestEntry",
    "Coordinates",
    "WorkBreak",
    "VacationCalendar",
    "DayOff",
    "DayOffRequest",
    "DayOffGroupCount",
    "WorkStatsResult",
    "Evaluation",
    "EvaluationResults",
    "Directory",
    "SesameDocument",
    "Expense",
    "ExpenseCategory",
    "ExpensePage",
    "Announcement",
    "JobCharge",
    "JobChargeEmployee",
    "Vacancy",
    "VacancyTotals",
    "Candidate",
    "TeamMember",
    "TeamCheck",
    "TeamRequestEntry",
    "TeamGroupCount",
    "Contract",
    "ContractGroupCount",
    "Channel",
    "Post",
    "PostChannelRef",
    "Comment",
    "CommunityAuthor",
    "CommunityPage",
    "CommunityMeta",
    "Reaction",
]
