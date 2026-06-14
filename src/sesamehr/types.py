from typing import Generic, TypeVar

from pydantic import Field

from ._base import SesameModel

T = TypeVar("T")


class PaginationMeta(SesameModel):
    total: int = 0
    page: int = 1
    last_page: int = 1
    per_page: int = 0


class Paginated(SesameModel, Generic[T]):
    """Paginated response from the Sesame REST API."""

    data: list[T] = Field(default_factory=list)
    meta: PaginationMeta = Field(default_factory=PaginationMeta)


def employee_filter(employee: str | None) -> list[dict]:
    """Build where conditions for the employee filter.

    If the value contains @, filters by exact email. Otherwise by name LIKE.
    """
    if not employee:
        return []
    if "@" in employee:
        return [{"field": "core_context_employee.email", "operator": "=", "value": employee}]
    return [{"field": "core_context_employee.name", "operator": "LIKE", "value": f"%{employee}%"}]
