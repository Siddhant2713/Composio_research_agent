"""HTTP fetch + HTML-to-text layer.

Nothing becomes evidence unless it was fetched here and came back with real content.
That property is what keeps fabricated URLs out of the final records.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Link hints worth a second hop, split deliberately: the first group answers "how do I
# call the API once authenticated", the second answers "how does a newcomer get
# credentials at all". Good docs for the first say nothing about the second.
CALL_KEYWORDS = (
    "auth", "authentication", "authorize", "oauth", "api-key", "apikey", "token",
    "quickstart", "quick-start", "getting-started", "api-reference", "reference",
    "webhook", "graphql", "sdk", "rest",
)
ACCESS_KEYWORDS = (
    "signup", "sign-up", "register", "registration", "get-started", "apply",
    "request-access", "partner", "developer-program", "contact", "sales",
    "pricing", "plans", "onboarding", "approval", "license",
)
LINK_KEYWORDS = CALL_KEYWORDS + ACCESS_KEYWORDS

SKIP_EXTENSIONS = (
    ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".mp4", ".webm",
    ".css", ".js", ".ico", ".woff", ".woff2",
)


@dataclass
class Page:
    """One successfully fetched page."""

    url: str           # final URL after redirects
    requested_url: str
    status: int
    title: str
    text: str
    html: str = ""
    accessed_at: str = field(default_factory=lambda: date.today().isoformat())

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc


@dataclass
class FetchFailure:
    requested_url: str
    reason: str


def make_client(timeout: float = 25.0) -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        timeout=timeout,
        headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*"},
    )


# Sidebar/nav chrome reads as a list of capability names ("Model Context Protocol",
# "Webhooks", "GraphQL") and was being mistaken for evidence that the product has those
# features. Strip it before the text ever reaches the model.
CHROME_TAGS = ("script", "style", "noscript", "svg", "nav", "aside", "footer", "header", "form")
CHROME_PATTERN = re.compile(
    r"(^|[-_\s])(nav|navbar|navigation|sidebar|side-bar|menu|breadcrumb|toc|"
    r"table-of-contents|footer|header|masthead|cookie|banner|drawer)([-_\s]|$)",
    re.I,
)


def _strip_chrome(root, total_chars: int) -> None:
    """Remove nav-ish elements, but never one large enough to be a content wrapper.

    Real sites hang nav class names on outer wrappers (Stripe's page body carries
    `Sidebar--expanded`), so decomposing every class match deletes the whole document.
    Only small elements are treated as chrome.
    """
    for element in root.find_all(attrs={"role": ["navigation", "banner", "contentinfo", "search"]}):
        element.decompose()

    for attr in ("class", "id"):
        for element in root.find_all(attrs={attr: CHROME_PATTERN}):
            if not element.parent:  # already removed with an ancestor
                continue
            size = len(element.get_text(strip=True))
            if size < 2000 and size < 0.3 * max(total_chars, 1):
                element.decompose()


def _html_to_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""

    for tag in soup(list(CHROME_TAGS)):
        tag.decompose()

    main = soup.find("main") or soup.find(attrs={"role": "main"})
    if main is None or len(main.get_text(strip=True)) < 200:
        main = soup

    _strip_chrome(main, len(main.get_text(strip=True)))
    text = re.sub(r"\n{3,}", "\n\n", main.get_text("\n", strip=True))
    return title, text


def fetch(client: httpx.Client, url: str, max_chars: int = 6000) -> Page | FetchFailure:
    """Fetch one URL. Returns a Page only for a real 2xx response with real text."""
    try:
        resp = client.get(url)
    except Exception as exc:
        return FetchFailure(url, f"{type(exc).__name__}: {exc}"[:200])

    if resp.status_code >= 400:
        return FetchFailure(url, f"HTTP {resp.status_code}")

    ctype = resp.headers.get("content-type", "")
    if not any(t in ctype for t in ("html", "text", "json", "xml")):
        return FetchFailure(url, f"non-text content-type: {ctype!r}")

    title, text = _html_to_text(resp.text)
    # A thin page is often a JS-rendered docs landing page: little text, but its links
    # still lead to the pages that matter, so keep it rather than dropping it.
    if len(text.strip()) < 120:
        return FetchFailure(url, f"page too thin ({len(text.strip())} chars)")

    return Page(
        url=str(resp.url),
        requested_url=url,
        status=resp.status_code,
        title=title,
        text=redact_secrets(text[:max_chars]),
        html=resp.text,
    )


# Docs pages routinely print sample credentials, and a scraped page could carry a real
# leaked one. Redact credential-shaped strings before any fetched text is written to disk.
SECRET_PATTERNS = (
    re.compile(r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{8,}", re.I),      # Stripe secret/restricted
    re.compile(r"\bwhsec_[A-Za-z0-9]{8,}"),                          # Stripe webhook signing
    re.compile(r"\bgh[posu]_[A-Za-z0-9]{20,}"),                      # GitHub tokens
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),                   # Slack tokens
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                             # AWS access key id
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),                        # Google API key
    re.compile(r"\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
)


def redact_secrets(text: str) -> str:
    """Replace credential-shaped substrings with a marker, preserving the prefix as a hint."""
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(0)[:8]}[REDACTED]", text)
    return text


def strip_shared_boilerplate(pages: list[Page], min_pages: int = 3) -> int:
    """Drop short lines that repeat across most of a site's pages.

    A short line appearing on nearly every page of a docs site is chrome, not a claim.
    This is the backstop for nav markup that the tag/class filters do not catch.
    Mutates `pages` in place; returns the number of distinct lines removed.
    """
    if len(pages) < min_pages:
        return 0

    counts: dict[str, int] = {}
    for page in pages:
        for line in {ln.strip() for ln in page.text.splitlines() if ln.strip()}:
            counts[line] = counts.get(line, 0) + 1

    threshold = max(min_pages, int(0.6 * len(pages)))
    boilerplate = {
        line for line, count in counts.items() if count >= threshold and len(line) < 80
    }
    if not boilerplate:
        return 0

    for page in pages:
        kept = [ln for ln in page.text.splitlines() if ln.strip() not in boilerplate]
        page.text = re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
    return len(boilerplate)


def harvest_links(page: Page, limit: int = 10, prefer_prefix: str | None = None) -> list[str]:
    """Same-domain links whose URL or anchor text suggests auth or access docs.

    `prefer_prefix` (the hint URL's first path segment, e.g. "/bots") is boosted, which
    keeps discovery anchored to the documented integration surface instead of drifting
    into unrelated sections of a large docs site.
    """
    soup = BeautifulSoup(page.html, "lxml")
    base_host = urlparse(page.url).netloc.lower()
    base_root = ".".join(base_host.split(".")[-2:]) if base_host else ""

    scored: list[tuple[int, str]] = []
    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].split("#")[0].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(page.url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if absolute.lower().endswith(SKIP_EXTENSIONS):
            continue
        if base_root and not parsed.netloc.lower().endswith(base_root):
            continue
        if absolute in seen or absolute.rstrip("/") == page.url.rstrip("/"):
            continue
        seen.add(absolute)

        haystack = f"{absolute.lower()} {anchor.get_text(' ', strip=True).lower()}"
        hits = sum(1 for kw in LINK_KEYWORDS if kw in haystack)
        if hits and prefer_prefix and parsed.path.startswith(prefer_prefix):
            hits += 3
        if hits:
            scored.append((hits, absolute))

    scored.sort(key=lambda pair: (-pair[0], len(pair[1])))
    return [url for _, url in scored[:limit]]
