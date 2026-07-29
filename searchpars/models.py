from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class SearchIntent:
    raw_query: str
    intent: str = "search"
    keywords: list[str] = field(default_factory=list)
    file_type: Optional[str] = None
    date_filter: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    action: Optional[str] = None
    answer_needed: bool = False


@dataclass(slots=True)
class SearchResult:
    result_type: str
    title: str
    subtitle: str
    target: str
    score: float = 0.0
    snippet: str = ""
    icon: str = "system-search-symbolic"


@dataclass(slots=True)
class IndexStats:
    files: int = 0
    applications: int = 0
    skipped: int = 0
    indexed_at: str = ""


def user_data_dir() -> Path:
    return Path.home() / ".local" / "share" / "searchpars"


def user_config_dir() -> Path:
    return Path.home() / ".config" / "searchpars"
