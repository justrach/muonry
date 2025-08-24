"""
Naive DeepWiki fetcher for the repo pages.
- Uses stdlib only (urllib + html.parser) to avoid extra deps.
- Provides utilities to list pages for a repo and fetch page content.

NOTE: This is a naive HTML scraper, not an MCP client. It's intended as a
minimal, dependency-free integration that can be swapped for MCP later.
"""
from __future__ import annotations

import urllib.request
import urllib.error
import urllib.parse
from html.parser import HTMLParser
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import time

BASE = "https://deepwiki.com"


@dataclass
class Link:
    href: str
    text: str


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: List[Link] = []
        self._in_a = False
        self._current_href: Optional[str] = None
        self._current_text: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._in_a = True
            self._current_href = None
            self._current_text = []
            for k, v in attrs:
                if k.lower() == "href":
                    self._current_href = v

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._in_a:
            href = self._current_href or ""
            text = "".join(self._current_text).strip()
            if href:
                self.links.append(Link(href=href, text=text))
            self._in_a = False
            self._current_href = None
            self._current_text = []

    def handle_data(self, data):
        if self._in_a:
            self._current_text.append(data)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.chunks: List[str] = []

    def handle_data(self, data):
        if data and data.strip():
            self.chunks.append(data)

    def text(self) -> str:
        return " ".join(part.strip() for part in self.chunks if part.strip())


def _fetch(url: str, timeout: int = 15, retries: int = 2, backoff: float = 0.5) -> Tuple[int, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "muonry-deepwiki-naive/0.1 (+https://muonry.com)"
    })
    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200) or 200
                charset = resp.headers.get_content_charset() or "utf-8"
                body = resp.read().decode(charset, errors="ignore")
                # Detect common protection interstitials and retry
                if status in (429, 503) or ("Just a moment" in body and attempt < retries):
                    raise urllib.error.HTTPError(url, status, "transient", hdrs=None, fp=None)
                return status, body
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="ignore") if getattr(e, 'fp', None) else str(e)
            except Exception:
                body = str(e)
            if attempt < retries and (e.code in (0, 408, 429, 500, 502, 503, 504) or "Just a moment" in body):
                attempt += 1
                time.sleep(backoff * attempt)
                continue
            return e.code, body
        except Exception as e:
            if attempt < retries:
                attempt += 1
                time.sleep(backoff * attempt)
                continue
            return 0, str(e)


def _normalize_repo(repo: str) -> str:
    repo = (repo or "").strip().strip("/")
    if not repo or "/" not in repo:
        return "jennyzzt/dgm"
    return repo


def list_pages(repo: str = "jennyzzt/dgm", limit: int = 50) -> Dict:
    repo = _normalize_repo(repo)
    url = f"{BASE}/{urllib.parse.quote(repo)}"
    status, html = _fetch(url)
    if status != 200:
        return {"status": "error", "code": status, "error": "failed to fetch index", "url": url}

    parser = _LinkParser()
    parser.feed(html)

    # Heuristic: keep links within the repo namespace and drop query/hash
    seen = set()
    pages: List[str] = []
    base_prefix = f"/{repo.strip('/')}"
    for ln in parser.links:
        href = urllib.parse.urlsplit(ln.href)
        path = href.path
        if not path:
            continue
        # Resolve relative paths (e.g., "docs/overview") as within the repo
        if not path.startswith("/"):
            path = f"{base_prefix}/" + path.lstrip("/")
        # Only keep links within the repo namespace
        if not path.startswith(base_prefix):
            continue
        if path == base_prefix:
            # repo root
            continue
        if path == base_prefix + "/":
            # repo root with trailing slash
            continue
        # Normalize path to path relative to repo root
        rel = path[len(base_prefix):].lstrip("/")
        if not rel:
            continue
        if rel in seen:
            continue
        seen.add(rel)
        pages.append(rel)
        if len(pages) >= max(1, int(limit)):
            break

    if not pages:
        # Fallback: if the root page has content, expose it as a single page ""
        extractor = _TextExtractor()
        extractor.feed(html)
        txt = extractor.text().strip()
        if txt:
            return {"status": "ok", "repo": repo, "count": 1, "pages": [""], "source": url, "note": "fallback: root only"}

    return {"status": "ok", "repo": repo, "count": len(pages), "pages": pages, "source": url}


def get_page(repo: str = "jennyzzt/dgm", path: str | None = None) -> Dict:
    repo = _normalize_repo(repo)
    rel = (path or "").strip().strip("/")
    if rel:
        url = f"{BASE}/{urllib.parse.quote(repo)}/{urllib.parse.quote(rel)}"
    else:
        url = f"{BASE}/{urllib.parse.quote(repo)}"
    status, html = _fetch(url)
    if status != 200:
        return {"status": "error", "code": status, "error": "failed to fetch page", "url": url}
    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.text()
    return {
        "status": "ok",
        "repo": repo,
        "path": rel or "",
        "url": url,
        "text": text[:20000],  # cap for safety
        "len_text": len(text),
    }
