from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchConfig:
    id: str
    name: str
    platform: str
    url: str
    location: str = ""
    property_type: str = ""
    metric: str = "total_listings_count"
    active: bool = True


@dataclass
class FetchResult:
    success: bool
    content: str = ""
    content_type: str = "markdown"
    provider: str = ""
    status_code: int | None = None
    error_message: str | None = None
    credits_used: int | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation:
    search_id: str
    observed_at: str
    status: str
    provider: str
    total_listings_count: int | None = None
    raw_total_listings_text: str | None = None
    error_message: str | None = None
    credits_used: int | None = None
    created_at: str = ""
