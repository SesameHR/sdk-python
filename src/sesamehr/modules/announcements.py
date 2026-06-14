from __future__ import annotations

from .._base import SesameModel
from ..config import ResolvedConfig
from ..http import HttpClient


class Announcement(SesameModel):
    id: str | None = None
    title: str | None = None
    type: str | None = None
    sent_at: str | None = None
    i_read_it: bool | None = None


class AnnouncementsModule:
    """Company announcements — list and view internal communications."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def list(self, *, limit: int | None = None) -> list[Announcement]:
        """List non-archived announcements, ordered by most recent."""
        data = self._http.get_data(
            "/private/notification/v1/employee-announcements",
            {
                "limit": limit if limit is not None else 20,
                "orderBy": "sentAt desc",
                "archivedAt[null]": True,
            },
        )
        return [Announcement.model_validate(item) for item in data]

    def detail(self, announcement_id: str) -> Announcement:
        """Get announcement details by ID."""
        data = self._http.get_data(f"/private/notification/v1/announcements/{announcement_id}")
        return Announcement.model_validate(data)
