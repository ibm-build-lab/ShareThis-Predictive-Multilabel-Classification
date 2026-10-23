#!/usr/bin/env python3
"""
Web Scraper Module
==================

Two-pass scraper:
  Pass 1 — requests + BeautifulSoup  (fast, no browser)
  Pass 2 — Playwright headless Chromium (fallback on HTTP_403 / JAVASCRIPT_ONLY)

Playwright is imported lazily — the app starts normally even if it is not
installed. It is only invoked when pass 1 fails with a retryable error code.

Install Playwright once:
    pip install playwright
    playwright install chromium
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import urlparse
from datetime import datetime, timezone

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise ImportError(
        "Missing required libraries. Run: pip install requests beautifulsoup4 lxml"
    ) from exc

logger = logging.getLogger(__name__)


# ── Error taxonomy ─────────────────────────────────────────────────────── #

class ScrapeErrorCode(str, Enum):
    INVALID_URL          = "INVALID_URL"
    DNS_FAILURE          = "DNS_FAILURE"
    CONNECTION_REFUSED   = "CONNECTION_REFUSED"
    TIMEOUT              = "TIMEOUT"
    HTTP_403             = "HTTP_403"
    HTTP_404             = "HTTP_404"
    HTTP_429             = "HTTP_429"
    HTTP_5XX             = "HTTP_5XX"
    HTTP_OTHER           = "HTTP_OTHER"
    NON_HTML_CONTENT     = "NON_HTML_CONTENT"
    JAVASCRIPT_ONLY      = "JAVASCRIPT_ONLY"
    EMPTY_CONTENT        = "EMPTY_CONTENT"
    ENCODING_ERROR       = "ENCODING_ERROR"
    PARSE_ERROR          = "PARSE_ERROR"
    PLAYWRIGHT_UNAVAILABLE = "PLAYWRIGHT_UNAVAILABLE"
    UNKNOWN              = "UNKNOWN"


# Human-readable explanations shown in the API response
_ERROR_MESSAGES: Dict[ScrapeErrorCode, str] = {
    ScrapeErrorCode.INVALID_URL: (
        "The URL is not valid. Make sure it starts with http:// or https:// "
        "and contains a proper domain name (e.g. https://example.com/page)."
    ),
    ScrapeErrorCode.DNS_FAILURE: (
        "The domain could not be resolved. The website may be offline, "
        "the domain may not exist, or there may be a network connectivity issue."
    ),
    ScrapeErrorCode.CONNECTION_REFUSED: (
        "The server actively refused the connection. The website may be blocking "
        "automated requests or the service may be temporarily unavailable."
    ),
    ScrapeErrorCode.TIMEOUT: (
        "The request timed out. The server did not respond within the allowed time. "
        "The site may be slow or temporarily overloaded."
    ),
    ScrapeErrorCode.HTTP_403: (
        "Access to this URL is forbidden (HTTP 403). The website is blocking "
        "automated access. This is common on sites with bot-protection (e.g. Cloudflare). "
        "A headless browser fallback was attempted but also failed."
    ),
    ScrapeErrorCode.HTTP_404: (
        "The requested page was not found (HTTP 404). "
        "The URL may be incorrect or the page may have been removed."
    ),
    ScrapeErrorCode.HTTP_429: (
        "The server is rate-limiting requests (HTTP 429 — Too Many Requests). "
        "Please wait a moment before retrying."
    ),
    ScrapeErrorCode.HTTP_5XX: (
        "The website returned a server error. "
        "The site may be experiencing technical difficulties. Try again later."
    ),
    ScrapeErrorCode.HTTP_OTHER: (
        "The server returned an unexpected HTTP error. "
        "Check that the URL points to a publicly accessible web page."
    ),
    ScrapeErrorCode.NON_HTML_CONTENT: (
        "The URL does not point to an HTML page. "
        "Only standard web pages (text/html) are supported — "
        "PDFs, images, and other file types cannot be analysed."
    ),
    ScrapeErrorCode.JAVASCRIPT_ONLY: (
        "The page requires JavaScript to render its content and the headless "
        "browser fallback did not return usable text. "
        "The page may require authentication or use advanced anti-bot measures."
    ),
    ScrapeErrorCode.EMPTY_CONTENT: (
        "The page was fetched successfully but no readable text content was found. "
        "The page may be blank, consist only of images or media, "
        "or its main content may be behind a login wall."
    ),
    ScrapeErrorCode.ENCODING_ERROR: (
        "The page content could not be decoded. "
        "The server may have returned an unsupported character encoding."
    ),
    ScrapeErrorCode.PARSE_ERROR: (
        "The HTML could not be parsed. "
        "The page may contain severely malformed markup."
    ),
    ScrapeErrorCode.PLAYWRIGHT_UNAVAILABLE: (
        "The page requires JavaScript rendering but the headless browser (Playwright) "
        "is not installed. Run: pip install playwright && playwright install chromium"
    ),
    ScrapeErrorCode.UNKNOWN: (
        "An unexpected error occurred while fetching the page. "
        "Please verify the URL and try again."
    ),
}

# Error codes that trigger a Playwright fallback attempt
_PLAYWRIGHT_FALLBACK_CODES = {
    ScrapeErrorCode.HTTP_403,
    ScrapeErrorCode.JAVASCRIPT_ONLY,
}


@dataclass
class ScrapeResult:
    """Structured result returned by WebScraper.scrape()."""
    url: str
    status: str                         # "success" | "error"
    raw_text: str = ""
    cleaned_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None         # user-facing message
    error_code: Optional[str] = None    # ScrapeErrorCode value
    error_detail: Optional[str] = None  # low-level detail (logged, not in response)
    scrape_method: str = "requests"     # "requests" | "playwright"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url":           self.url,
            "status":        self.status,
            "raw_text":      self.raw_text,
            "cleaned_text":  self.cleaned_text,
            "metadata":      self.metadata,
            "error":         self.error,
            "error_code":    self.error_code,
            "scrape_method": self.scrape_method,
        }


# ── Scraper ────────────────────────────────────────────────────────────── #

class WebScraper:
    """
    Two-pass web scraper.

    Pass 1: requests + BeautifulSoup (fast, no browser overhead).
    Pass 2: Playwright headless Chromium (automatic fallback on HTTP_403
            or JAVASCRIPT_ONLY). Playwright is imported lazily.

    Every error path returns a ScrapeResult with:
    - error:        user-facing explanation (shown in API response)
    - error_code:   machine-readable ScrapeErrorCode
    - error_detail: low-level exception text (logged only)
    """

    _MIN_WORD_COUNT       = 20
    _JS_SHELL_SCRIPT_RATIO = 0.85

    # Playwright: how long to wait for the page to settle (ms)
    _PW_NAVIGATION_TIMEOUT = 30_000   # 30 s
    _PW_WAIT_AFTER_LOAD    = 2_000    # 2 s extra after networkidle

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            # Omit 'br' — requests only decompresses brotli when the 'brotli'
            # package is installed; advertising it without that package causes
            # the server to return bytes requests cannot decode.
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    # ------------------------------------------------------------------ #
    # Public entry-point                                                    #
    # ------------------------------------------------------------------ #

    def scrape(self, url: str) -> Dict[str, Any]:
        """
        Scrape a URL.  Tries requests first; falls back to Playwright on
        HTTP_403 or JAVASCRIPT_ONLY.

        Returns a dict with keys:
            url, status, raw_text, cleaned_text, metadata,
            error, error_code, scrape_method.
        status == 'success' only when meaningful text was extracted.
        """
        return self._scrape(url).to_dict()

    # ------------------------------------------------------------------ #
    # Orchestration                                                          #
    # ------------------------------------------------------------------ #

    def _scrape(self, url: str) -> ScrapeResult:
        result = ScrapeResult(url=url, status="error")

        # 1 — Validate URL
        if not self._validate_url(url):
            return self._fail(
                result, ScrapeErrorCode.INVALID_URL,
                f"URL failed format validation: {url}",
            )

        # 2 — Pass 1: requests
        result = self._scrape_with_requests(url)

        # 3 — Pass 2: Playwright fallback (only on specific error codes)
        if (
            result.status != "success"
            and ScrapeErrorCode(result.error_code) in _PLAYWRIGHT_FALLBACK_CODES
        ):
            logger.info(
                "Requests failed [%s] for %s — trying Playwright fallback",
                result.error_code, url,
            )
            pw_result = self._scrape_with_playwright(url)
            if pw_result.status == "success":
                return pw_result
            # Playwright also failed — return its error (more informative)
            logger.warning(
                "Playwright fallback also failed [%s] for %s",
                pw_result.error_code, url,
            )
            return pw_result

        return result

    # ------------------------------------------------------------------ #
    # Pass 1: requests + BeautifulSoup                                      #
    # ------------------------------------------------------------------ #

    def _scrape_with_requests(self, url: str) -> ScrapeResult:
        result = ScrapeResult(url=url, status="error", scrape_method="requests")

        response, fetch_error = self._fetch_html(url)
        if response is None:
            return fetch_error

        # Content-type guard
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and "text/html" not in content_type and "application/xhtml" not in content_type:
            return self._fail(
                result, ScrapeErrorCode.NON_HTML_CONTENT,
                f"Non-HTML content-type: {content_type}",
            )

        try:
            html_bytes = response.content
        except Exception as exc:
            return self._fail(result, ScrapeErrorCode.ENCODING_ERROR, str(exc))

        try:
            soup = BeautifulSoup(html_bytes, "lxml")
        except Exception as exc:
            return self._fail(result, ScrapeErrorCode.PARSE_ERROR, str(exc))

        return self._extract_from_soup(soup, url, result)

    # ------------------------------------------------------------------ #
    # Pass 2: Playwright headless Chromium                                  #
    # ------------------------------------------------------------------ #

    def _scrape_with_playwright(self, url: str) -> ScrapeResult:
        result = ScrapeResult(url=url, status="error", scrape_method="playwright")

        # Lazy import — don't fail at module load if Playwright isn't installed
        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
        except ImportError:
            return self._fail(
                result, ScrapeErrorCode.PLAYWRIGHT_UNAVAILABLE,
                "playwright package not installed",
            )

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                    ],
                )
                context = browser.new_context(
                    user_agent=self.headers["User-Agent"],
                    viewport={"width": 1280, "height": 800},
                    locale="en-US",
                    java_script_enabled=True,
                    # Mask common automation signals
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept": self.headers["Accept"],
                    },
                )
                page = context.new_page()

                # Hide navigator.webdriver to reduce bot detection
                page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )

                logger.info("Playwright fetching %s", url)
                try:
                    page.goto(
                        url,
                        timeout=self._PW_NAVIGATION_TIMEOUT,
                        wait_until="networkidle",
                    )
                except PWTimeout:
                    # networkidle timed out — try domcontentloaded as softer wait
                    logger.warning(
                        "Playwright networkidle timeout for %s — retrying with domcontentloaded",
                        url,
                    )
                    page.goto(
                        url,
                        timeout=self._PW_NAVIGATION_TIMEOUT,
                        wait_until="domcontentloaded",
                    )

                # Brief pause to let late JS mutations settle
                page.wait_for_timeout(self._PW_WAIT_AFTER_LOAD)

                html_content = page.content()
                browser.close()

            soup = BeautifulSoup(html_content, "lxml")
            return self._extract_from_soup(soup, url, result)

        except Exception as exc:
            exc_str = str(exc)
            logger.error("Playwright error for %s: %s", url, exc_str[:200])

            # Map common Playwright errors to typed codes
            if "net::ERR_NAME_NOT_RESOLVED" in exc_str or "getaddrinfo" in exc_str:
                code = ScrapeErrorCode.DNS_FAILURE
            elif "net::ERR_CONNECTION_REFUSED" in exc_str:
                code = ScrapeErrorCode.CONNECTION_REFUSED
            elif "Timeout" in exc_str or "timeout" in exc_str:
                code = ScrapeErrorCode.TIMEOUT
            elif "403" in exc_str:
                code = ScrapeErrorCode.HTTP_403
            else:
                code = ScrapeErrorCode.UNKNOWN

            return self._fail(result, code, f"Playwright: {exc_str[:300]}")

    # ------------------------------------------------------------------ #
    # Shared content extraction (used by both passes)                       #
    # ------------------------------------------------------------------ #

    def _extract_from_soup(
        self, soup: BeautifulSoup, url: str, result: ScrapeResult
    ) -> ScrapeResult:
        """Run metadata extraction, JS detection, cleaning, and content gates."""

        result.metadata = self._extract_metadata(soup, url)

        raw_text = self._extract_main_content(soup)
        result.raw_text = raw_text

        if self._is_js_only(soup, raw_text):
            # Only treat as a hard failure if requests tried; Playwright would
            # have already rendered JS, so flag as empty content instead.
            if result.scrape_method == "requests":
                return self._fail(
                    result, ScrapeErrorCode.JAVASCRIPT_ONLY,
                    "JS-only shell detected",
                )
            else:
                return self._fail(
                    result, ScrapeErrorCode.EMPTY_CONTENT,
                    "Playwright rendered the page but found no readable text",
                )

        soup_clean = self._remove_unwanted_elements(soup)
        main_text = self._extract_main_content(soup_clean)
        result.cleaned_text = self._clean_text(main_text)

        word_count = len(result.cleaned_text.split())
        result.metadata["word_count"] = word_count
        result.metadata["text_length"] = len(result.cleaned_text)

        if word_count < self._MIN_WORD_COUNT and len(raw_text.split()) < self._MIN_WORD_COUNT:
            return self._fail(
                result, ScrapeErrorCode.EMPTY_CONTENT,
                f"Only {word_count} words found (minimum {self._MIN_WORD_COUNT})",
            )

        result.status = "success"
        logger.info(
            "Scraped %s | method=%s words=%d",
            url, result.scrape_method, word_count,
        )
        return result

    # ------------------------------------------------------------------ #
    # requests fetch with retry                                             #
    # ------------------------------------------------------------------ #

    def _fetch_html(self, url: str):
        """
        Fetch with retry.
        Returns (response, None) on success.
        Returns (None, ScrapeResult) on final failure.
        """
        last_code: Optional[ScrapeErrorCode] = None
        last_detail: str = ""

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    "requests GET %s (attempt %d/%d)", url, attempt + 1, self.max_retries
                )
                response = requests.get(
                    url,
                    headers=self.headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                response.raise_for_status()
                return response, None

            except requests.exceptions.Timeout as exc:
                last_code = ScrapeErrorCode.TIMEOUT
                last_detail = str(exc)
                logger.warning("Timeout on attempt %d: %s", attempt + 1, url)

            except requests.exceptions.ConnectionError as exc:
                exc_str = str(exc).lower()
                if any(k in exc_str for k in ("name or service not known", "nodename nor servname", "getaddrinfo")):
                    last_code = ScrapeErrorCode.DNS_FAILURE
                else:
                    last_code = ScrapeErrorCode.CONNECTION_REFUSED
                last_detail = str(exc)
                logger.warning(
                    "Connection error on attempt %d (%s): %s",
                    attempt + 1, last_code.value, exc_str[:120],
                )

            except requests.exceptions.HTTPError as exc:
                status_code = exc.response.status_code if exc.response is not None else 0
                last_detail = f"HTTP {status_code}"
                if status_code == 403:
                    last_code = ScrapeErrorCode.HTTP_403
                elif status_code == 404:
                    last_code = ScrapeErrorCode.HTTP_404
                    break  # definitive — no retry
                elif status_code == 429:
                    last_code = ScrapeErrorCode.HTTP_429
                    wait = (2 ** attempt) * 2
                    logger.warning("Rate-limited (429), waiting %ds", wait)
                    time.sleep(wait)
                elif 500 <= status_code < 600:
                    last_code = ScrapeErrorCode.HTTP_5XX
                else:
                    last_code = ScrapeErrorCode.HTTP_OTHER
                    break  # other 4xx won't improve with retry
                logger.warning("HTTP %d on attempt %d: %s", status_code, attempt + 1, url)

            except requests.exceptions.RequestException as exc:
                last_code = ScrapeErrorCode.UNKNOWN
                last_detail = str(exc)
                logger.warning("Request error on attempt %d: %s", attempt + 1, exc)

            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)

        result = ScrapeResult(url=url, status="error", scrape_method="requests")
        return None, self._fail(result, last_code or ScrapeErrorCode.UNKNOWN, last_detail)

    # ------------------------------------------------------------------ #
    # Content extraction helpers                                            #
    # ------------------------------------------------------------------ #

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "url":        url,
            "domain":     urlparse(url).netloc,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

        title_tag = soup.find("title")
        metadata["title"] = title_tag.get_text().strip() if title_tag else None

        for tag in soup.find_all("meta"):
            name    = (tag.get("name")     or "").lower()
            prop    = (tag.get("property") or "").lower()
            content = tag.get("content", "").strip()

            if name in ("description", "keywords", "author", "robots", "language"):
                metadata[name] = content
            elif name in ("article:published_time", "publish_date"):
                metadata["published_date"] = content
            elif name in ("article:modified_time", "modified_date"):
                metadata["modified_date"] = content

            if prop.startswith("og:"):
                metadata[prop.replace("og:", "og_")] = content
            elif prop.startswith("article:"):
                metadata[prop.replace("article:", "article_")] = content

            if tag.get("charset"):
                metadata["charset"] = tag.get("charset")

        canonical = soup.find("link", {"rel": "canonical"})
        if canonical and canonical.get("href"):
            metadata["canonical_url"] = canonical["href"]

        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["html_lang"] = html_tag["lang"]

        return metadata

    def _remove_unwanted_elements(self, soup: BeautifulSoup) -> BeautifulSoup:
        for tag in [
            "script", "style", "noscript", "iframe", "embed",
            "nav", "header", "footer", "aside", "form",
            "button", "input", "select", "textarea",
        ]:
            for el in soup.find_all(tag):
                el.decompose()

        unwanted_classes = {
            "advertisement", "sidebar", "menu", "navigation",
            "footer", "header", "cookie", "popup", "modal",
            "social-share", "related-posts",
        }
        protected = {"article", "main", "section"}
        for el in [e for e in soup.find_all(class_=True) if e.name not in protected]:
            if el.parent is None:
                continue
            if {c.lower() for c in (el.get("class") or [])} & unwanted_classes:
                el.decompose()

        return soup

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        for tag, attrs in [
            ("article", {}),
            ("main",    {}),
            ("div",     {"role": "main"}),
            ("div",     {"class": re.compile(r"(content|article|post|entry)", re.I)}),
            ("body",    {}),
        ]:
            node = soup.find(tag, attrs)
            if node:
                return node.get_text(separator=" ", strip=True)
        return soup.get_text(separator=" ", strip=True)

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\s*\n", "\n\n", text)
        text = re.sub(r"https?://[^\s\)\]\}\"\'<>]+", "", text)
        text = re.sub(r"\S+@\S+\.\S+", "", text)
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        return text.strip()

    # ------------------------------------------------------------------ #
    # JS-only detection                                                     #
    # ------------------------------------------------------------------ #

    def _is_js_only(self, soup: BeautifulSoup, raw_text: str) -> bool:
        visible_words = len(raw_text.split())
        if visible_words >= 50:
            return False

        spa_markers = [
            soup.find("div", {"id": "root"}),
            soup.find("div", {"id": "app"}),
            soup.find("div", {"id": "__next"}),
            soup.find("div", {"id": "gatsby-focus-wrapper"}),
        ]
        if any(m is not None for m in spa_markers) and visible_words < 30:
            return True

        all_scripts    = soup.find_all("script")
        script_len     = sum(len(s.get_text()) for s in all_scripts)
        total_text_len = len(soup.get_text())
        if total_text_len > 0 and script_len / total_text_len > self._JS_SHELL_SCRIPT_RATIO:
            return True

        return False

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _validate_url(url: str) -> bool:
        try:
            p = urlparse(url)
            return bool(p.scheme in ("http", "https") and p.netloc)
        except Exception:
            return False

    @staticmethod
    def _fail(result: ScrapeResult, code: ScrapeErrorCode, detail: str) -> ScrapeResult:
        result.status      = "error"
        result.error_code  = code.value
        result.error       = _ERROR_MESSAGES.get(code, _ERROR_MESSAGES[ScrapeErrorCode.UNKNOWN])
        result.error_detail = detail
        logger.error("Scrape failed [%s] via %s: %s", code.value, result.scrape_method, detail[:200])
        return result
