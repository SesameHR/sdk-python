from __future__ import annotations

from pydantic import Field

from .._base import SesameModel
from ..config import ResolvedConfig
from ..http import HttpClient


class ExpenseCategory(SesameModel):
    id: str | None = None
    name: str | None = None
    is_default: bool | None = None


class PaymentStatus(SesameModel):
    value: str | None = None
    reason: str | None = None


class Expense(SesameModel):
    id: str | None = None
    concept: str | None = None
    total_import: float | None = None
    currency: str | None = None
    status: str | None = None
    date: str | None = None
    description: str | None = None
    category: ExpenseCategory | None = None
    payment_status: PaymentStatus | None = None


class ExpensePageMeta(SesameModel):
    """The expenses endpoints paginate with `currentPage` (not `page`)."""

    current_page: int = 1
    last_page: int = 1
    total: int = 0
    per_page: int = 0


class ExpensePage(SesameModel):
    """Envelope returned by the expenses endpoints: the list plus aggregate
    totals, plus the pagination `meta`. NOTE: the TS SDK mistypes this as
    `Paginated<Expense>` — the real API nests the list under `data.expenses`
    alongside summary totals. Modeled here from the real response shape."""

    expenses: list[Expense] = Field(default_factory=list)
    total_amount: float | None = None
    total_expenses: int | None = None
    total_amount_accepted: float | None = None
    total_expenses_with_images_incident: int | None = None
    total_expenses_with_pending_info: int | None = None
    total_pending_to_refund: float | None = None
    meta: ExpensePageMeta = Field(default_factory=ExpensePageMeta)


class ExpensesModule:
    """Employee expenses — list personal/company expenses, view details, and get categories."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def list(
        self,
        *,
        from_: str | None = None,
        to: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ) -> ExpensePage:
        """List the authenticated employee's expenses (paginated). Filter by date range or status."""
        response = self._http.get(
            "/api/v3/employee-expenses",
            {
                "limit": limit if limit is not None else 20,
                "page": page if page is not None else 1,
                "from": from_,
                "to": to,
                "status": status,
            },
        )
        return self._page(response)

    def detail(self, expense_id: str) -> Expense:
        """Get expense details by ID."""
        data = self._http.get_data(f"/api/v3/expenses/{expense_id}")
        return Expense.model_validate(data)

    def categories(self) -> list[ExpenseCategory]:
        """Get available expense categories."""
        data = self._http.get_data("/api/v3/expense-categories")
        return [ExpenseCategory.model_validate(item) for item in data]

    def company_expenses(
        self,
        *,
        employee_id: str | None = None,
        from_: str | None = None,
        to: str | None = None,
        status: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ) -> ExpensePage:
        """List all company expenses (admin). Optionally filter by employee, date range, or status."""
        response = self._http.get(
            "/api/v3/expenses",
            {
                "limit": limit if limit is not None else 20,
                "page": page if page is not None else 1,
                "from": from_,
                "to": to,
                "status": status,
                "employeeId": employee_id,
            },
        )
        return self._page(response)

    @staticmethod
    def _page(response: dict) -> ExpensePage:
        data = response.get("data") if isinstance(response, dict) else None
        page = ExpensePage.model_validate(data or {})
        meta = response.get("meta") if isinstance(response, dict) else None
        if meta:
            page.meta = ExpensePageMeta.model_validate(meta)
        return page
