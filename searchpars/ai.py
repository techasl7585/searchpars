from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from .models import SearchIntent, SearchResult
from .nlp import parse_local


SYSTEM_PROMPT = """Sen SearchPars'ın Türkçe arama niyeti çözümleyicisisin.
Yalnızca geçerli JSON döndür. Şema:
{"intent":"search|action","keywords":["..."],"file_type":null|"package"|"pdf"|"image"|"video"|"audio"|"text"|"document"|"spreadsheet"|"presentation"|"code","date_filter":null|"today"|"yesterday"|"last_week"|"this_month","date_from":null|"YYYY-MM-DD","date_to":null|"YYYY-MM-DD","action":null|"bluetooth_on"|"bluetooth_off"|"wifi_on"|"wifi_off"|"screenshot"|"mute"|"unmute"|"open_trash"|"open_settings","answer_needed":false}
Kullanıcının asıl kavramlarını keywords alanında kısa biçimde koru. Eş anlamlı en fazla 3
faydalı kelime ekleyebilirsin. Sistem işlemi değilse intent search olmalı."""


class OllamaProvider:
    def __init__(self) -> None:
        self.base_url = os.environ.get("SEARCHPARS_OLLAMA_URL", "http://127.0.0.1:11434")
        self.model = os.environ.get("SEARCHPARS_MODEL", "qwen3.5:4b")
        self._availability: tuple[float, bool] | None = None

    def _request(self, payload: dict, timeout: int = 35) -> dict:
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def available(self) -> bool:
        now = time.monotonic()
        if self._availability and now - self._availability[0] < 10:
            return self._availability[1]
        try:
            request = urllib.request.Request(
                f"{self.base_url.rstrip('/')}/api/tags", method="GET"
            )
            with urllib.request.urlopen(request, timeout=1.5) as response:
                data = json.loads(response.read().decode("utf-8"))
            available = any(
                item.get("name", "") == self.model
                or item.get("model", "") == self.model
                for item in data.get("models", [])
            )
        except (OSError, ValueError, urllib.error.URLError):
            available = False
        self._availability = (now, available)
        return available

    def parse_intent(self, query: str) -> SearchIntent:
        fallback = parse_local(query)
        try:
            data = self._request(
                {
                    "model": self.model,
                    "stream": False,
                    "think": False,
                    "format": "json",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": query},
                    ],
                    "options": {"temperature": 0.1},
                }
            )
            content = data["message"]["content"]
            parsed = json.loads(content)
            allowed_types = {
                None, "package", "pdf", "image", "video", "audio", "text", "document",
                "spreadsheet", "presentation", "code",
            }
            if parsed.get("file_type") not in allowed_types:
                parsed["file_type"] = fallback.file_type
            keywords = [
                str(item) for item in parsed.get("keywords", fallback.keywords)
            ][:12]
            if (
                fallback.file_type
                and (fallback.date_from or fallback.date_filter)
                and not fallback.keywords
            ):
                keywords = []
            return SearchIntent(
                raw_query=query,
                intent=parsed.get("intent", fallback.intent),
                keywords=keywords,
                file_type=parsed.get("file_type") or fallback.file_type,
                date_filter=parsed.get("date_filter") or fallback.date_filter,
                date_from=parsed.get("date_from") or fallback.date_from,
                date_to=parsed.get("date_to") or fallback.date_to,
                action=parsed.get("action", fallback.action),
                answer_needed=bool(parsed.get("answer_needed", fallback.answer_needed)),
            )
        except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError):
            return fallback

    def answer(self, query: str, results: list[SearchResult]) -> str | None:
        excerpts = []
        for result in results[:5]:
            if result.result_type != "file":
                continue
            excerpts.append(
                f"DOSYA: {result.title}\nYOL: {result.target}\nİÇERİK: {result.snippet[:800]}"
            )
        if not excerpts:
            return None
        try:
            data = self._request(
                {
                    "model": self.model,
                    "stream": False,
                    "think": False,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Yalnızca verilen dosya sonuçlarına dayan. Kısa Türkçe cevap ver. "
                                "Yeterli bilgi yoksa bunu açıkça söyle. Dosya adını belirt."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"SORU: {query}\n\nSONUÇLAR:\n" + "\n\n".join(excerpts),
                        },
                    ],
                    "options": {"temperature": 0.2},
                },
                timeout=55,
            )
            return str(data["message"]["content"]).strip()
        except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError):
            return None

    def general_answer(self, query: str) -> str | None:
        try:
            data = self._request(
                {
                    "model": self.model,
                    "stream": False,
                    "think": False,
                    "keep_alive": "10m",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "SearchPars içindeki Türkçe yapay zekâ asistanısın. "
                                "Kullanıcının yazdığı kişi, konu veya soruya doğrudan, doğru "
                                "ve 8-12 cümlelik anlaşılır, ayrıntılı Türkçe cevap ver. "
                                "Önce kısa tanım, sonra önemli ayrıntılar ve son olarak dikkat "
                                "edilmesi gereken noktaları ayrı paragraflarda anlat. "
                                "Emin olmadığın bilgiyi kesinmiş gibi yazma."
                            ),
                        },
                        {"role": "user", "content": query},
                    ],
                    "options": {"temperature": 0.2},
                },
                timeout=90,
            )
            return str(data["message"]["content"]).strip()
        except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError):
            return None

    def answer_with_sources(
        self,
        query: str,
        local_results: list[SearchResult],
        web_results: list[SearchResult],
    ) -> str | None:
        sources: list[str] = []
        source_number = 1
        for result in web_results[:6]:
            sources.append(
                f"[{source_number}] WEB\nBAŞLIK: {result.title}\n"
                f"ADRES: {result.target}\nİÇERİK: {result.snippet[:900]}"
            )
            source_number += 1
        for result in local_results[:4]:
            if result.result_type != "file":
                continue
            sources.append(
                f"[{source_number}] YEREL DOSYA\nDOSYA: {result.title}\n"
                f"YOL: {result.target}\nİÇERİK: {result.snippet[:900]}"
            )
            source_number += 1

        if not sources:
            return self.general_answer(query)

        try:
            data = self._request(
                {
                    "model": self.model,
                    "stream": False,
                    "think": False,
                    "keep_alive": "10m",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "SearchPars'ın Türkçe cevap motorusun. Yalnızca verilen "
                                "kaynaklara dayan. 8-14 cümlelik ayrıntılı ama anlaşılır cevap "
                                "ver. Yanıtı 'Kısa Bilgi', 'Ayrıntılar' ve uygunsa 'Güncel "
                                "Durum' başlıklarıyla paragraflara ayır. Her önemli bilginin "
                                "sonuna [1] biçiminde kaynak numarası ekle. Markdown tablosu "
                                "kullanma. Kaynaklar yetmiyorsa bunu açıkça söyle."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"SORU: {query}\n\nKAYNAKLAR:\n" + "\n\n".join(sources),
                        },
                    ],
                    "options": {"temperature": 0.1},
                },
                timeout=90,
            )
            return str(data["message"]["content"]).strip()
        except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError):
            return None

    def describe(self) -> dict:
        return {"provider": "Ollama", "model": self.model, "available": self.available()}
