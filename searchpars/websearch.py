from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from xml.etree import ElementTree

from .models import SearchResult


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) "
    "Gecko/20100101 Firefox/140.0 SearchPars/0.2"
)

TCMB_TODAY_XML = "https://www.tcmb.gov.tr/kurlar/today.xml"
TCMB_TODAY_PAGE = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/tr/"
    "tcmb+tr/main+page+site+area/bugun"
)

CURRENCY_TERMS = {
    "USD": ("dolar", "usd", "abd doları"),
    "EUR": ("euro", "avro", "eur"),
    "GBP": ("sterlin", "gbp", "ingiliz sterlini"),
}


class DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.snippets: list[str] = []
        self._capture: str | None = None
        self._href = ""
        self._parts: list[str] = []

    @staticmethod
    def _classes(attributes: list[tuple[str, str | None]]) -> set[str]:
        value = dict(attributes).get("class") or ""
        return set(value.split())

    def handle_starttag(
        self, tag: str, attributes: list[tuple[str, str | None]]
    ) -> None:
        classes = self._classes(attributes)
        if tag == "a" and "result__a" in classes:
            self._capture = "link"
            self._href = dict(attributes).get("href") or ""
            self._parts = []
        elif "result__snippet" in classes:
            self._capture = "snippet"
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._capture == "link" and tag == "a":
            title = " ".join("".join(self._parts).split())
            if title and self._href:
                self.links.append((title, self._href))
            self._capture = None
            self._parts = []
        elif self._capture == "snippet" and tag in {"a", "div", "span"}:
            snippet = " ".join("".join(self._parts).split())
            if snippet:
                self.snippets.append(snippet)
            self._capture = None
            self._parts = []


def _real_url(url: str) -> str:
    if url.startswith("//"):
        url = "https:" + url
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query:
        return urllib.parse.unquote(query["uddg"][0])
    return url


def _domain(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.removeprefix("www.")


class WebSearchProvider:
    def __init__(self, timeout: int = 12) -> None:
        self.timeout = timeout

    def _get(self, url: str) -> bytes:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.6",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read()

    def search(self, query: str, limit: int = 7) -> list[SearchResult]:
        results: list[SearchResult] = []
        seen: set[str] = set()

        for result in self._currency(query):
            results.append(result)
            seen.add(result.target + result.title)

        for result in self._wikipedia(query, limit=2):
            results.append(result)
            seen.add(result.target)

        try:
            url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode(
                {"q": query, "kl": "tr-tr"}
            )
            parser = DuckDuckGoParser()
            parser.feed(self._get(url).decode("utf-8", errors="replace"))
            for index, (title, raw_url) in enumerate(parser.links):
                target = _real_url(raw_url)
                if not target.startswith(("http://", "https://")) or target in seen:
                    continue
                snippet = parser.snippets[index] if index < len(parser.snippets) else ""
                results.append(
                    SearchResult(
                        result_type="web",
                        title=html.unescape(title),
                        subtitle=_domain(target),
                        target=target,
                        score=50 - index,
                        snippet=html.unescape(snippet),
                        icon="web-browser-symbolic",
                    )
                )
                seen.add(target)
                if len(results) >= limit:
                    break
        except (OSError, ValueError, urllib.error.URLError):
            pass
        return results[:limit]

    def _currency(self, query: str) -> list[SearchResult]:
        normalized = query.lower()
        requested = [
            code
            for code, terms in CURRENCY_TERMS.items()
            if any(term in normalized for term in terms)
        ]
        if not requested and "döviz" not in normalized:
            return []
        if not requested:
            requested = ["USD", "EUR", "GBP"]

        try:
            root = ElementTree.fromstring(self._get(TCMB_TODAY_XML))
        except (ElementTree.ParseError, OSError, ValueError, urllib.error.URLError):
            return []

        rate_date = root.attrib.get("Tarih") or root.attrib.get("Date") or "Bugün"
        results: list[SearchResult] = []
        for code in requested:
            node = root.find(f"./Currency[@CurrencyCode='{code}']")
            if node is None:
                continue
            unit_text = (node.findtext("Unit") or "1").strip()
            name = (node.findtext("Isim") or code).strip()
            buying = (node.findtext("ForexBuying") or "").strip()
            selling = (node.findtext("ForexSelling") or "").strip()
            if not buying and not selling:
                continue
            buying_tr = buying.replace(".", ",")
            selling_tr = selling.replace(".", ",")
            results.append(
                SearchResult(
                    result_type="live",
                    title=f"{code}/TRY — Alış {buying_tr}  •  Satış {selling_tr}",
                    subtitle=f"TCMB gösterge kuru • {rate_date}",
                    target=TCMB_TODAY_PAGE,
                    score=200,
                    snippet=(
                        f"{unit_text} {name} için TCMB döviz alış kuru {buying_tr} TL, "
                        f"döviz satış kuru {selling_tr} TL."
                    ),
                    icon="office-chart-line-symbolic",
                )
            )
        return results

    def _wikipedia(self, query: str, limit: int = 2) -> list[SearchResult]:
        parameters = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrlimit": str(limit),
            "prop": "extracts|info",
            "exintro": "1",
            "explaintext": "1",
            "exsentences": "8",
            "inprop": "url",
            "format": "json",
            "formatversion": "2",
        }
        url = "https://tr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(parameters)
        try:
            payload = json.loads(self._get(url).decode("utf-8"))
            pages = payload.get("query", {}).get("pages", [])
        except (OSError, ValueError, urllib.error.URLError):
            return []

        results: list[SearchResult] = []
        for page in pages:
            title = str(page.get("title", "")).strip()
            target = str(page.get("fullurl", "")).strip()
            if not title or not target:
                continue
            extract = re.sub(r"\s+", " ", str(page.get("extract", ""))).strip()
            results.append(
                SearchResult(
                    result_type="web",
                    title=title,
                    subtitle="tr.wikipedia.org",
                    target=target,
                    score=100,
                    snippet=extract,
                    icon="help-about-symbolic",
                )
            )
        return results
