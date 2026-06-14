from __future__ import annotations

from typing import Any

from pydantic import Field

from .._base import SesameModel
from ..config import ResolvedConfig
from ..http import HttpClient


class Evaluation(SesameModel):
    """An evaluation. Different endpoints return different identifier/title
    fields (`list`/`detail` use `id`/`title`; `my_evaluations` uses
    `evaluationId`/`evaluationTitle`), so every field is optional and the rest
    pass through via `model_extra` — mirroring the TS SDK's non-validating cast."""

    id: str | None = None
    evaluation_id: str | None = None
    title: str | None = None
    evaluation_title: str | None = None
    form_title: str | None = None
    form_type: str | None = None
    evaluation_type: str | None = None
    type: str | None = None
    publish_type: str | None = None
    status: str | None = None


class EvaluationResults(SesameModel):
    evaluation_id: str | None = None
    total_answers: int = 0
    answers: list[dict[str, Any]] = Field(default_factory=list)


class EvaluationsModule:
    """Performance evaluations — list, view details, results, and pending evaluations."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def list(
        self,
        *,
        form_type: str | None = None,
        publish_type: str | None = None,
        limit: int | None = None,
    ) -> list[Evaluation]:
        """List all evaluations with optional filters by form type or publish status."""
        data = self._http.get_data(
            "/private/poll/v1/evaluations",
            {
                "limit": limit if limit is not None else 20,
                "formType": form_type,
                "publishType": publish_type,
            },
        )
        return [Evaluation.model_validate(item) for item in data]

    def detail(self, evaluation_id: str) -> Evaluation:
        """Get evaluation details by ID."""
        data = self._http.get_data(f"/private/poll/v1/evaluations/{evaluation_id}")
        return Evaluation.model_validate(data)

    def results(self, evaluation_id: str) -> EvaluationResults:
        """Get aggregated results/answers for an evaluation."""
        data = self._http.get_data(f"/private/poll/v1/form-answers/evaluations-results/{evaluation_id}")
        return EvaluationResults.model_validate(data)

    def my_evaluations(self, *, search: str | None = None, limit: int | None = None) -> list[Evaluation]:
        """Get evaluations assigned to the authenticated employee."""
        data = self._http.get_data(
            "/private/poll/v1/evaluations/employees-all-forms",
            {
                "limit": limit if limit is not None else 20,
                "orderType": "desc",
                "publishType": "active",
                "search": search,
            },
        )
        return [Evaluation.model_validate(item) for item in data]

    def pending(self) -> list[Evaluation]:
        """Get evaluations pending the authenticated employee's response."""
        data = self._http.get_data("/private/poll/v1/entity-reference-evaluations")
        return [Evaluation.model_validate(item) for item in data]
