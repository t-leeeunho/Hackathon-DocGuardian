"""Web ingestion — crawl a URL and its same-site sub-pages into DocGuardian.

Given a starting URL (typically a documentation site), this fetches the page,
extracts the readable content as markdown, discovers same-site links *under the
start path*, and crawls a bounded set of sub-pages. Each page then goes through the
SAME drop-off pipeline as a pasted document — the **Librarian** rewrites it into an
AI-agent-friendly form, re-files it under a category, and embeds it — grouped under
a namespace derived from the site host (so a whole docs section imports as one tree).

Bounded by ``max_pages`` / ``max_depth`` and restricted to the start URL's host and
path prefix, so it imports "the URL and its sub-pages", not the entire internet.
"""

from __future__ import annotations

import re
from urllib.parse import urldefrag, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify

from app.agents.librarian import slugify
from app.ingestion.intake import ingest_content

USER_AGENT = "DocGuardian-WebIngest/0.1"
REQUEST_TIMEOUT = 15.0
MAX_CONTENT_CHARS = 24000

# Link targets we never follow (binary / asset extensions).
_SKIP_EXT = (
    ".pdf", ".zip", ".gz", ".tar", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".mp3",
    ".wasm", ".map", ".json", ".xml", ".rss", ".atom",
)


class WebIngestError(RuntimeError):
    """Crawling/extraction failed (e.g. unreachable URL, no readable pages)."""


def _normalize(url: str) -> str:
    clean, _ = urldefrag(url)
    if len(clean) > len("https://x"):  # don't strip the slash of a bare host root
        clean = clean.rstrip("/")
    return clean


def _host(url: str) -> str:
    return urlparse(url).netloc.lower()


def _looks_binary(url: str) -> bool:
    return urlparse(url).path.lower().endswith(_SKIP_EXT)


def _path_prefix(url: str) -> str:
    """The start URL's directory prefix, used to keep the crawl within its subtree."""
    p = urlparse(url)
    path = p.path or "/"
    if not path.endswith("/"):
        path = path.rsplit("/", 1)[0] + "/"
    return f"{p.scheme}://{p.netloc}{path}"


def _title_from_h1(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    return h1.get_text(strip=True) if h1 else ""


def extract(url: str, html: str) -> tuple[str, str, list[str]]:
    """Return (title, markdown_body, outbound_links) for one fetched page."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    title = (title or _title_from_h1(soup) or url).strip()[:140]

    # Collect links from the whole document (incl. nav) BEFORE trimming chrome.
    links = [urljoin(url, a["href"]) for a in soup.find_all("a", href=True)]

    # Trim site chrome, then convert the main content region to markdown.
    for tag in soup(["nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.body
        or soup
    )
    md = markdownify(str(main), heading_style="ATX", strip=["img"])
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return title, md, links


def crawl(
    start_url: str,
    *,
    max_pages: int = 8,
    max_depth: int = 2,
    restrict_to_path: bool = True,
    progress=None,
) -> list[dict]:
    """Breadth-first crawl of ``start_url`` within its host (and path prefix).

    Returns a list of ``{"url", "title", "markdown"}`` for each readable HTML page.
    Per-page failures are skipped silently so one bad link can't abort the import.
    """
    start = _normalize(start_url)
    host = _host(start)
    prefix = _path_prefix(start)

    seen: set[str] = {start}
    queue: list[tuple[str, int]] = [(start, 0)]
    pages: list[dict] = []

    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=headers) as client:
        while queue and len(pages) < max_pages:
            url, depth = queue.pop(0)
            try:
                resp = client.get(url)
            except Exception:  # noqa: BLE001 - unreachable page -> skip
                continue
            if resp.status_code != 200 or "html" not in resp.headers.get("content-type", "").lower():
                continue

            title, md, links = extract(url, resp.text)
            if md:
                pages.append({"url": url, "title": title, "markdown": md[:MAX_CONTENT_CHARS]})
                if progress:
                    try:
                        progress(len(pages), url, title)
                    except Exception:  # noqa: BLE001 - progress is best-effort
                        pass

            if depth < max_depth and len(pages) < max_pages:
                for link in links:
                    n = _normalize(link)
                    if n in seen or _host(n) != host or _looks_binary(n):
                        continue
                    if restrict_to_path and not n.startswith(prefix) and n != start:
                        continue
                    seen.add(n)
                    queue.append((n, depth + 1))
    return pages


def _name_for(url: str) -> str:
    """A drop-off filename derived from the URL path (the Librarian re-files it)."""
    p = urlparse(url)
    path = p.path.strip("/") or (p.netloc or "index")
    last = path.rsplit("/", 1)[-1]
    if "." not in last:
        path += ".md"
    return path


def ingest_url(
    start_url: str,
    *,
    max_pages: int = 8,
    max_depth: int = 2,
    namespace: str | None = None,
    progress=None,
) -> dict:
    """Crawl ``start_url`` (+ sub-pages) and import each page via the Librarian.

    Returns a summary: how many pages were found/imported, the namespace they were
    grouped under, the resulting doc ids, and any per-page errors.
    """
    if not start_url.lower().startswith(("http://", "https://")):
        raise WebIngestError("URL must start with http:// or https://")

    pages = crawl(start_url, max_pages=max_pages, max_depth=max_depth, progress=progress)
    if not pages:
        raise WebIngestError(f"No readable HTML pages found at {start_url}")

    ns = (namespace or "").strip() or slugify(_host(start_url)) or "web"
    imported: list[dict] = []
    errors: list[dict] = []
    for pg in pages:
        content = f"# {pg['title']}\n\n> Source: {pg['url']}\n\n{pg['markdown']}\n"
        try:
            res = ingest_content(_name_for(pg["url"]), content, namespace=ns)
            imported.append(
                {
                    "url": pg["url"],
                    "title": pg["title"],
                    "docId": res["doc_id"],
                    "chunks": res["chunks"],
                }
            )
        except Exception as exc:  # noqa: BLE001 - one bad page shouldn't fail the batch
            errors.append({"url": pg["url"], "error": str(exc)})

    return {
        "startUrl": start_url,
        "namespace": ns,
        "pagesFound": len(pages),
        "imported": len(imported),
        "docs": imported,
        "errors": errors,
    }
