from __future__ import annotations

import re
from dataclasses import dataclass

from .models import SearchIntent


@dataclass(frozen=True, slots=True)
class RouteDecision:
    route: str
    use_local: bool
    use_web: bool
    use_ai: bool
    reason: str


FILE_WORDS = re.compile(
    r"\b(dosya\w*|belge\w*|pdf\w*|deb\w*|appimage\w*|paket\w*|"
    r"indir\w*|klasör\w*|masaüstü\w*|resim\w*|fotoğraf\w*|"
    r"video\w*|müzik\w*|kod\w*|sunum\w*|excel\w*|word\w*)\b"
)
WEB_WORDS = re.compile(
    r"\b(web|internet|haber|güncel|bugünkü|son durum|kimdir|nedir|"
    r"kaç|ne zaman|nerede|hava durumu|dolar|euro|kur)\b"
)
OPEN_WORDS = re.compile(r"\b(aç|çalıştır|başlat)\b")


def route_query(query: str, intent: SearchIntent) -> RouteDecision:
    normalized = query.strip().lower()
    if intent.intent == "action" and intent.action:
        return RouteDecision("action", False, False, False, "sistem işlemi")

    explicit_file = bool(
        intent.file_type
        or intent.date_from
        or FILE_WORDS.search(normalized)
        or "içinde geçen" in normalized
    )
    if explicit_file:
        return RouteDecision("local", True, False, True, "yerel dosya isteği")

    if OPEN_WORDS.search(normalized):
        return RouteDecision("application", True, False, False, "uygulama açma")

    if WEB_WORDS.search(normalized) or normalized.endswith("?"):
        return RouteDecision("web", False, True, True, "güncel/genel bilgi")

    return RouteDecision("hybrid", True, True, True, "birleşik arama")
