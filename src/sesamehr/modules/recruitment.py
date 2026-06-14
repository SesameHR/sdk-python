from .._base import SesameModel
from ..config import ResolvedConfig
from ..http import HttpClient
from ..types import Paginated


class Vacancy(SesameModel):
    id: str | None = None
    name: str | None = None
    status: str | None = None


class VacancyTotals(SesameModel):
    total: int = 0
    open: int = 0
    closed: int = 0
    draft: int = 0


class Candidate(SesameModel):
    id: str | None = None
    name: str | None = None
    email: str | None = None


class RecruitmentModule:
    """Recruitment — list vacancies, view totals, and browse candidates."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def vacancies(
        self,
        *,
        status: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ) -> Paginated[Vacancy]:
        """List vacancies (paginated). Filter by status or search by name."""
        params: dict = {
            "limit": limit if limit is not None else 20,
            "page": page if page is not None else 1,
            "status": status,
            "orderBy": "createdAt desc",
        }
        if search:
            params["name[contains]"] = search
        response = self._http.get(f"/api/v3/companies/{self._config.company_id}/vacancies", params)
        return Paginated[Vacancy].model_validate(response)

    def totals(self) -> VacancyTotals:
        """Get vacancy count totals (total, open, closed, draft)."""
        data = self._http.get_data("/api/v3/vacancies-totals")
        return VacancyTotals.model_validate(data)

    def vacancy(self, vacancy_id: str) -> Vacancy:
        """Get vacancy details by ID."""
        data = self._http.get_data(f"/api/v3/vacancies/{vacancy_id}")
        return Vacancy.model_validate(data)

    def candidates(
        self,
        vacancy_id: str,
        *,
        search: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ) -> Paginated[Candidate]:
        """List candidates for a specific vacancy (paginated)."""
        params: dict = {
            "vacancyId": vacancy_id,
            "limit": limit if limit is not None else 20,
            "page": page if page is not None else 1,
            "orderBy": "createdAt desc",
        }
        if search:
            params["search"] = search
        response = self._http.get(f"/api/v3/companies/{self._config.company_id}/candidates", params)
        return Paginated[Candidate].model_validate(response)
