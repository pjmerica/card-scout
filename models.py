from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

NOW = datetime.now(timezone.utc)


@dataclass
class Item:
    """One card/points news post or card-linked offer (from RSS or Slickdeals).
    feeds.parse_feed fills the raw fields; news.py fills the derived ones."""
    title: str
    link: str
    source: str
    kind: str = "card"
    published: str = ""
    age_days: float = 0.0
    summary: str = ""
    image: str = ""
    store: str = ""
    price: float | None = None
    votes: int | None = None
    comments: int | None = None
    staff_pick: bool = False
    expires: str = ""
    feed_tags: list[str] = field(default_factory=list)
    thread_id: str = ""
    boost: float = 0.0
    # derived
    retailers: list[str] = field(default_factory=list)
    card_category: str = ""
    bonus_value: int | None = None
    is_bf: bool = False
    is_new: bool = False
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    score: float = 0.0
    sources: list[str] = field(default_factory=list)
