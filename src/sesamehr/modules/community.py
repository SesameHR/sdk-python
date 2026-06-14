from typing import IO, Any, Generic, TypeVar, Union

from pydantic import Field

from .._base import SesameModel
from ..config import ResolvedConfig
from ..http import HttpClient

T = TypeVar("T")

FileContent = Union[bytes, IO[bytes]]

_BASE = "/private/community/v1"


class CommunityMeta(SesameModel):
    """Pagination envelope returned by the community (wall) API.
    Note: it uses `currentPage` — NOT `page` like the shared `PaginationMeta`."""

    current_page: int = 1
    last_page: int = 1
    total: int = 0
    per_page: int = 0


class CommunityPage(SesameModel, Generic[T]):
    """A paginated community response: `data` plus a `meta` page descriptor."""

    data: list[T] = Field(default_factory=list)
    meta: CommunityMeta = Field(default_factory=CommunityMeta)


class Channel(SesameModel):
    """A wall channel."""

    id: str | None = None
    company_id: str | None = None
    name: str | None = None
    created_by_id: str | None = None
    created_by_name: str | None = None
    # Channel visibility, e.g. "public".
    channel_type: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
    # Number of posts in the channel.
    total: int = 0
    # Whether the current employee is subscribed to the channel.
    subscribed: bool = False
    all_company: bool = False


class Reaction(SesameModel):
    """A reaction on a post or comment. The exact shape is not yet confirmed
    against real data (the captured sample had none) — left open; any fields
    pass through via `model_extra`."""


class CommunityAuthor(SesameModel):
    """Author/employee reference embedded in posts and comments."""

    id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    image_profile_url: str | None = Field(None, alias="imageProfileURL")


class PostChannelRef(SesameModel):
    """Lightweight channel reference embedded in a post."""

    channel_id: str | None = None
    channel_name: str | None = None
    subscribed: bool = False


class Post(SesameModel):
    """A post on the wall."""

    id: str | None = None
    company_id: str | None = None
    channel: PostChannelRef | None = None
    content: str | None = None
    content_updated_at: str | None = None
    created_by: CommunityAuthor | None = None
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
    comments_count: int = 0
    # Reaction shape is not yet confirmed against real data — left open.
    reactions: list[Reaction] = Field(default_factory=list)
    # Whether the current employee has read this post.
    i_read: bool = False
    # Attached image URL, if any.
    image: str | None = None
    # Attached document, if any (shape not yet confirmed).
    document: Any = None
    # Link preview metadata, if any (shape not yet confirmed).
    open_graph: Any = None


class Comment(SesameModel):
    """A comment on a post."""

    id: str | None = None
    author: CommunityAuthor | None = None
    comment: str | None = None
    comment_updated_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    reactions: list[Reaction] = Field(default_factory=list)
    thread_id: str | None = None


class CommunityModule:
    """Access to the Sesame "wall" / Community: read channels, posts and comments,
    and publish posts to a channel."""

    def __init__(self, http: HttpClient, config: ResolvedConfig) -> None:
        self._http = http
        self._config = config

    def channels(self, *, limit: int | None = None, page: int | None = None) -> CommunityPage[Channel]:
        """List the company's channels (paginated)."""
        response = self._http.get(
            f"{_BASE}/company/channels",
            {"limit": limit if limit is not None else 20, "page": page if page is not None else 1},
        )
        return CommunityPage[Channel].model_validate(response)

    def posts(
        self,
        *,
        channel_id: str | None = None,
        employee_id: str | None = None,
        limit: int | None = None,
        page: int | None = None,
        order_by: str | None = None,
    ) -> CommunityPage[Post]:
        """List wall posts for an employee's feed (defaults to the authenticated one),
        ordered by most recent. Pass `channel_id` to read a single channel's posts."""
        employee = employee_id or self._config.employee_id
        params: dict[str, Any] = {
            "limit": limit if limit is not None else 20,
            "page": page if page is not None else 1,
            "orderBy": order_by or "createdAt desc",
        }
        if channel_id:
            params["channelId"] = channel_id
        response = self._http.get(f"{_BASE}/employee/{employee}/posts", params)
        return CommunityPage[Post].model_validate(response)

    def post(self, post_id: str) -> Post:
        """Get a single post by ID."""
        data = self._http.get_data(f"{_BASE}/post/{post_id}")
        return Post.model_validate(data)

    def comments(self, post_id: str, *, limit: int | None = None, page: int | None = None) -> CommunityPage[Comment]:
        """List comments on a post (paginated)."""
        response = self._http.get(
            f"{_BASE}/post/{post_id}/comments",
            {"limit": limit if limit is not None else 20, "page": page if page is not None else 1},
        )
        return CommunityPage[Comment].model_validate(response)

    def create_post(
        self,
        *,
        channel_id: str,
        content: str | None = None,
        file: FileContent | None = None,
        file_name: str | None = None,
        url_link: str | None = None,
    ) -> dict[str, Any]:
        """Publish a post to a channel, optionally with an attachment.
        Returns the new post's ID.

        `file` takes images, videos and documents in the same multipart field
        (`document`); images come back on `Post.image`, the rest on
        `Post.document`. `url_link` attaches a link preview (rendered via
        `Post.open_graph`).
        """
        if file is not None or url_link:
            data: dict[str, Any] = {"channel": channel_id}
            if content is not None:
                data["content"] = content
            if url_link:
                data["urlLink"] = url_link
            files = None
            if file is not None:
                files = {"document": (file_name, file) if file_name else file}
            response = self._http.upload(f"{_BASE}/post", data=data, files=files)
            return response["data"]
        return self._http.post_data(f"{_BASE}/post", {"channel": channel_id, "content": content})
