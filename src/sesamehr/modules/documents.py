from __future__ import annotations

from typing import IO, Any, Union

from .._base import SesameModel
from ..config import ResolvedConfig
from ..errors import SesameError
from ..http import HttpClient
from ..types import Paginated

FileContent = Union[bytes, IO[bytes]]


class Directory(SesameModel):
    id: str | None = None
    name: str | None = None
    type: str | None = None


class SesameDocument(SesameModel):
    id: str | None = None
    name: str | None = None


class DocumentsModule:
    """Document management — browse directories, list/upload/download documents."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def directory(self, directory_id: str) -> Directory:
        """Get directory details by ID."""
        data = self._http.get_data(f"/api/v3/directories/{directory_id}")
        return Directory.model_validate(data)

    def list(
        self,
        *,
        parent_directory_id: str | None = None,
        limit: int | None = None,
        page: int | None = None,
    ) -> Paginated[SesameDocument]:
        """List documents visible to the authenticated employee (paginated)."""
        response = self._http.get(
            "/api/v3/documents",
            {
                "limit": limit if limit is not None else 20,
                "page": page if page is not None else 1,
                "parentDirectoryId": parent_directory_id,
                "viewerReferenceType": "employee",
                "viewerReferenceId": self._config.employee_id,
            },
        )
        return Paginated[SesameDocument].model_validate(response)

    def upload(
        self,
        *,
        directory_id: str,
        file: FileContent,
        file_name: str,
        name: str | None = None,
        original_date: str | None = None,
        notify_employee: bool = False,
    ) -> dict[str, Any]:
        """Upload a document to a specific directory."""
        data: dict[str, Any] = {}
        if name:
            data["name"] = name
        if original_date:
            data["originalDate"] = original_date
        if notify_employee:
            data["notifyEmployee"] = "true"

        return self._http.upload(
            f"/api/v3/directories/{directory_id}/documents",
            data=data,
            files={"document": (file_name, file)},
        )

    def download_url(self, document_id: str) -> str:
        """Get a temporary download URL for a document."""
        response = self._http.get(f"/api/v3/documents/{document_id}/url")
        data = response.get("data") if isinstance(response, dict) else None
        url = data.get("url") if isinstance(data, dict) else None
        if url is None and isinstance(response, dict):
            url = response.get("url")
        if not isinstance(url, str):
            raise SesameError("Invalid download URL response")
        return url
