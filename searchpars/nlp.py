from __future__ import annotations

import re
from datetime import datetime, timedelta

from .models import SearchIntent


STOP_WORDS = {
    "aç",
    "ara",
    "bana",
    "belge",
    "belgesini",
    "belgeleri",
    "bir",
    "bul",
    "dosya",
    "dosyasını",
    "dosyayı",
    "dosyaları",
    "göster",
    "indirdiğim",
    "içinde",
    "ile",
    "ilgili",
    "olan",
    "özet",
    "özetle",
    "son",
    "şu",
    "ve",
}

FILE_TYPES = {
    "kurulum dosyası": "package",
    "kurulum paketi": "package",
    "deb": "package",
    "paket": "package",
    "appimage": "package",
    "pdf": "pdf",
    "resim": "image",
    "fotoğraf": "image",
    "foto": "image",
    "görsel": "image",
    "video": "video",
    "müzik": "audio",
    "ses": "audio",
    "metin": "text",
    "word": "document",
    "excel": "spreadsheet",
    "sunum": "presentation",
    "kod": "code",
}

MONTHS = {
    "ocak": 1,
    "şubat": 2,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayıs": 5,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "ağustos": 8,
    "agustos": 8,
    "eylül": 9,
    "eylul": 9,
    "ekim": 10,
    "kasım": 11,
    "kasim": 11,
    "aralık": 12,
    "aralik": 12,
}

ACTION_PATTERNS = (
    (r"\bbluetooth(?:'u|u)?\s+aç\b", "bluetooth_on"),
    (r"\bbluetooth(?:'u|u)?\s+kapat\b", "bluetooth_off"),
    (r"\bwi-?fi(?:'yi|yi)?\s+aç\b", "wifi_on"),
    (r"\bwi-?fi(?:'yi|yi)?\s+kapat\b", "wifi_off"),
    (r"\bekran görüntüsü (?:al|çek)\b", "screenshot"),
    (r"\b(?:ses|sesi)\s+(?:kapat|sessize al)\b", "mute"),
    (r"\b(?:ses|sesi)\s+aç\b", "unmute"),
    (r"\bçöp kutusunu aç\b", "open_trash"),
    (r"\bayarları aç\b", "open_settings"),
)

LOCAL_SCOPE_PATTERN = re.compile(
    r"\b(?:"
    r"bilgisayar(?:ım|ın|ımız|ınız)?(?:da|de|daki|deki|dan|den)?|"
    r"cihaz(?:ım|ın|ımız|ınız)?(?:da|de|daki|deki|dan|den)?|"
    r"pardus(?:um|un)(?:da|de|daki|deki)?"
    r")\b"
)


def normalize(text: str) -> str:
    normalized = text.strip().lower().replace("’", "'")
    normalized = re.sub(
        r"([a-zçğıöşü0-9]+)'(?:y?[ıiuü]|n?[ıiuü]n|[dt][ae]|[dt]?[ae]n)\b",
        r"\1",
        normalized,
    )
    return re.sub(r"\s+", " ", normalized)


def _date_filter(query: str) -> str | None:
    if "bugün" in query:
        return "today"
    if "dün" in query:
        return "yesterday"
    if "geçen hafta" in query or "son hafta" in query:
        return "last_week"
    if "bu ay" in query:
        return "this_month"
    return None


def _exact_date(query: str) -> tuple[str | None, str | None, str]:
    month_pattern = "|".join(MONTHS)
    match = re.search(
        rf"\b([0-3]?\d)\s+({month_pattern})(?:\s+(\d{{4}}))?\b",
        query,
    )
    if not match:
        return None, None, query
    now = datetime.now()
    day = int(match.group(1))
    month = MONTHS[match.group(2)]
    year = int(match.group(3)) if match.group(3) else now.year
    try:
        start = datetime(year, month, day)
    except ValueError:
        return None, None, query
    end = start + timedelta(days=1)
    cleaned = query[: match.start()] + " " + query[match.end() :]
    return start.date().isoformat(), end.date().isoformat(), cleaned


def parse_local(query: str) -> SearchIntent:
    normalized = normalize(query)
    result = SearchIntent(raw_query=query)

    for pattern, action in ACTION_PATTERNS:
        if re.search(pattern, normalized):
            result.intent = "action"
            result.action = action
            return result

    for token, file_type in FILE_TYPES.items():
        if re.search(rf"\b{re.escape(token)}(?:ler|ları|leri)?\b", normalized):
            result.file_type = file_type
            break
    if (
        result.file_type is None
        and re.search(r"\b(kurulum|yükleme)\b", normalized)
        and re.search(r"\b(dosya|paket|indir|indirdiğim)\b", normalized)
    ):
        result.file_type = "package"

    result.date_filter = _date_filter(normalized)
    result.date_from, result.date_to, normalized_without_date = _exact_date(normalized)
    result.answer_needed = bool(
        re.search(
            r"\b(nedir|ne anlatıyor|özetle|özet|hangi|neden|nasıl|cevapla)\b",
            normalized,
        )
    )

    cleaned = normalized_without_date
    cleaned = LOCAL_SCOPE_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"\b(bugün|dün|geçen hafta|son hafta|bu ay)\b", " ", cleaned)
    for token in FILE_TYPES:
        cleaned = re.sub(rf"\b{re.escape(token)}(?:ler|ları|leri)?\b", " ", cleaned)
    if result.file_type == "package":
        cleaned = re.sub(
            r"\b(kurulum|paket|paketi|paketini|indirme|indirilen)\b", " ", cleaned
        )

    words = re.findall(r"[\wçğıöşüÇĞİÖŞÜ.-]{2,}", cleaned, flags=re.UNICODE)
    result.keywords = [word for word in words if word not in STOP_WORDS][:12]
    return result


def date_bounds(
    date_filter: str | None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[float | None, float | None]:
    if date_from:
        try:
            start = datetime.fromisoformat(date_from)
            end = (
                datetime.fromisoformat(date_to)
                if date_to
                else start + timedelta(days=1)
            )
            return start.timestamp(), end.timestamp()
        except ValueError:
            pass
    if not date_filter:
        return None, None

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_filter == "today":
        start, end = today, today + timedelta(days=1)
    elif date_filter == "yesterday":
        start, end = today - timedelta(days=1), today
    elif date_filter == "last_week":
        start, end = now - timedelta(days=7), now
    elif date_filter == "this_month":
        start = today.replace(day=1)
        end = now
    else:
        return None, None
    return start.timestamp(), end.timestamp()
