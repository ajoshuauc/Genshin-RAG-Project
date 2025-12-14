# pipeline/harvest/mediawiki.py
from __future__ import annotations

import time
import math
import logging
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote

import requests
from requests import Response

logger = logging.getLogger(__name__)


class MediaWikiError(RuntimeError):
    """Raised for non-retryable MediaWiki client errors."""


class MediaWikiClient:
    """
    Minimal MediaWiki client tailored for Fandom's Genshin Impact Wiki.

    What it does (and why it fits our pipeline):
      • Lists pages in categories (Books, Archon/Story/World Quests, Characters)
      • Fetches rendered article HTML via REST (cleaner than front-end scrape)
      • Pulls sections and basic page info for richer metadata
      • Retries politely and rate-limits (be a good citizen)

    Dependencies: only `requests`.
    """

    def __init__(
        self,
        base_url: str = "https://genshin-impact.fandom.com",
        user_agent: str = "genshin-rag/1.0 (contact: ajoshuauc@gmail.com)",
        timeout_s: int = 30,
        max_retries: int = 5,
        rate_limit_rps: float = 2.0,  # gentle
        session: Optional[requests.Session] = None,
    ):
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.api_url = f"{self.base_url}/api.php"
        self.rest_url = f"{self.base_url}/rest.php/v1"
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.rate_limit_rps = rate_limit_rps
        self._min_interval = 1.0 / rate_limit_rps if rate_limit_rps > 0 else 0.0
        self._last_request_ts = 0.0

        self.session = session or requests.Session()
        # Use simple curl-like headers to ensure API returns JSON instead of HTML
        # Default to curl/8.7.1 if user_agent doesn't look like curl
        if "curl" not in user_agent.lower():
            default_ua = "curl/8.7.1"
        else:
            default_ua = user_agent
        self.session.headers.update(
            {
                "User-Agent": default_ua,
                "Accept": "*/*",
            }
        )

    # -------------------- Internal HTTP helpers -------------------- #

    def _respect_rate_limit(self) -> None:
        if self._min_interval <= 0:
            return
        now = time.time()
        wait = self._min_interval - (now - self._last_request_ts)
        if wait > 0:
            time.sleep(wait)

    def _request(self, method: str, url: str, **kwargs) -> Response:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            self._respect_rate_limit()
            try:
                resp = self.session.request(method, url, timeout=self.timeout_s, **kwargs)
                self._last_request_ts = time.time()

                if resp.status_code in (429, 500, 502, 503, 504):
                    backoff = min(20.0, 0.6 * (2 ** (attempt - 1)))
                    logger.warning(
                        "Transient %s on %s %s (attempt %d/%d); sleep %.1fs",
                        resp.status_code, method, url, attempt, self.max_retries, backoff
                    )
                    time.sleep(backoff)
                    continue

                resp.raise_for_status()
                return resp

            except (requests.Timeout, requests.ConnectionError) as e:
                last_exc = e
                backoff = min(20.0, 0.6 * (2 ** (attempt - 1)))
                logger.warning(
                    "Network error on %s %s (attempt %d/%d): %s; sleep %.1fs",
                    method, url, attempt, self.max_retries, e, backoff
                )
                time.sleep(backoff)

        if last_exc:
            raise MediaWikiError(f"Failed after {self.max_retries} retries: {last_exc}")
        raise MediaWikiError(f"Failed after {self.max_retries} retries (unknown error).")

    # -------------------- Public API methods -------------------- #

    def category_members(
        self,
        category_title: str,
        namespace: Optional[int] = 0,
        limit_per_call: int = 500,
        max_pages: Optional[int] = None,
    ) -> List[Dict]:
        """
        Enumerate pages in a category.

        Args:
            category_title: e.g. "Category:Books", "Category:World Quests"
            namespace: 0 = main/article space. None => all namespaces.
            limit_per_call: API pagination size (≤500).
            max_pages: optional hard cap for tests/dev.

        Returns:
            List[dict]: items like {"pageid": int, "ns": int, "title": "Page Title"}
        """
        params = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": category_title,
            "cmlimit": limit_per_call,
        }
        if namespace is not None:
            params["cmnamespace"] = namespace

        out: List[Dict] = []
        cmcontinue = None

        while True:
            p = dict(params)
            if cmcontinue:
                p["cmcontinue"] = cmcontinue

            resp = self._request("GET", self.api_url, params=p)
            data = resp.json()

            members = data.get("query", {}).get("categorymembers", [])
            out.extend(members)

            if max_pages and len(out) >= max_pages:
                return out[:max_pages]

            cmcontinue = data.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                break

        return out

    def page_html(self, title: str) -> Optional[str]:
        """
        Get rendered article HTML via REST (preferred for cleaning/sectioning).
        Returns None if the page does not exist (404).
        """
        url = f"{self.rest_url}/page/{quote(title, safe='')}/html"
        self._respect_rate_limit()
        resp = self.session.get(url, timeout=self.timeout_s)
        self._last_request_ts = time.time()
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.text

    def page_sections_via_api(self, title: str) -> Optional[Dict[str, str]]:
        """
        Get page sections via MediaWiki API (returns {section_name: index}).
        More reliable than parsing HTML. Uses action=parse&prop=sections.
        
        Returns:
            Dict mapping section names to their indices, or None if page not found.
        """
        params = {
            "action": "parse",
            "page": title,
            "prop": "sections",
            "format": "json",
            "formatversion": "2",
        }
        
        try:
            resp = self._request("GET", self.api_url, params=params)
            data = resp.json()
            
            sections: Dict[str, str] = {}
            parse_data = data.get("parse", {})
            if "missing" in parse_data or "error" in data:
                return None
                
            for sec in parse_data.get("sections", []):
                line = sec.get("line", "").strip()
                idx = sec.get("index", "")
                if line and idx:
                    sections[line] = idx
            return sections
        except (MediaWikiError, KeyError, ValueError):
            return None

    def page_section_text_via_api(self, title: str, section_index: str) -> Optional[str]:
        """
        Get a specific section's text via MediaWiki API.
        Uses action=parse&prop=text&section={index}, parses HTML and returns plain text.
        
        Args:
            title: Page title
            section_index: Section index (as returned by page_sections_via_api)
            
        Returns:
            Plain text content of the section, or None if not found.
        """
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "section": section_index,
            "format": "json",
            "formatversion": "2",
        }
        
        try:
            resp = self._request("GET", self.api_url, params=params)
            data = resp.json()
            
            parse_data = data.get("parse", {})
            if "missing" in parse_data or "error" in data:
                return None
                
            html = parse_data.get("text", "")
            if not html:
                return None
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text("\n", strip=True)
        except (MediaWikiError, KeyError, ValueError, ImportError):
            return None

    def page_wikitext(self, title: str) -> Optional[str]:
        """
        Get source wikitext via action=query&prop=revisions (optional).
        """
        params = {
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
        }
        resp = self._request("GET", self.api_url, params=params)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for _, page in pages.items():
            if "missing" in page:
                return None
            revs = page.get("revisions", [])
            if revs:
                slot = revs[0].get("slots", {}).get("main", {})
                return slot.get("*") or slot.get("content")
        return None

    def page_sections(self, title: str) -> List[Dict]:
        """
        Return a list of sections via action=parse.
        Section dict keys typically include: index, line, number, level, byteoffset.
        """
        params = {"action": "parse", "format": "json", "page": title, "prop": "sections"}
        resp = self._request("GET", self.api_url, params=params)
        data = resp.json()
        parsed = data.get("parse", {})
        return parsed.get("sections", []) or []

    def page_info(self, title: str) -> Dict:
        """
        Basic metadata: pageid, title, url, length, lastrevid, touched, categories.
        """
        params = {
            "action": "query",
            "format": "json",
            "prop": "info|categories",
            "inprop": "url|displaytitle",
            "titles": title,
            "cllimit": "max",
        }
        resp = self._request("GET", self.api_url, params=params)
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for _, page in pages.items():
            return page
        return {}

    # -------------------- Convenience utilities -------------------- #

    @staticmethod
    def normalize_title(title: str) -> str:
        """
        Normalize a wiki title to MediaWiki conventions:
        - Trim whitespace
        - Replace underscores with spaces
        - Capitalize first character
        """
        s = (title or "").strip().replace("_", " ")
        return s[:1].upper() + s[1:] if s else s

    @staticmethod
    def canonical_url(base_url: str, title: str) -> str:
        """Build canonical /wiki/<Title_With_Underscores> URL."""
        slug = title.replace(" ", "_")
        return f"{base_url}/wiki/{quote(slug)}"

    @staticmethod
    def estimate_tokens_from_chars(chars: int) -> int:
        """Rough 4 chars ≈ 1 token heuristic (budgeting embeds)."""
        return math.ceil(chars / 4)


# -------------------- Self-test (manual quick check) -------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mw = MediaWikiClient(user_agent="ajoshuauc-genshin-rag/1.0 (ajoshuauc@gmail.com)")

    # Sample: list a few World Quests
    worlds = mw.category_members("Category:World Quests", max_pages=5)
    print("[world quests sample]", [w["title"] for w in worlds])

    # Fetch HTML + sections for the first one
    if worlds:
        t = worlds[0]["title"]
        html = mw.page_html(t) or ""
        secs = mw.page_sections(t)
        info = mw.page_info(t)
        print(f"[{t}] html_bytes={len(html)} sections={len(secs)} url={info.get('fullurl','')}")
