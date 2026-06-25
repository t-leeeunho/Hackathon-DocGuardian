"""Offline tests for web ingestion (HTML extraction + URL helpers).

These don't hit the network or the DB — they exercise the pure extraction and
URL-normalization logic that decides what gets crawled and imported.
"""

from __future__ import annotations

import pytest

from app.ingestion.web_ingest import (
    WebIngestError,
    _looks_binary,
    _name_for,
    _normalize,
    _path_prefix,
    extract,
    ingest_url,
)

SAMPLE = """<html><head><title>Build Guide</title></head>
<body>
  <nav><a href="/docs/intro">Intro</a><a href="https://other.com/x">External</a></nav>
  <main>
    <h1>Build Guide</h1>
    <p>Run <code>dotnet build</code> to compile.</p>
    <a href="setup">Setup</a>
  </main>
  <footer>site footer junk</footer>
  <script>var x = 1;</script>
</body></html>"""


def test_extract_pulls_title_markdown_and_links():
    title, md, links = extract("https://site.test/docs/build", SAMPLE)
    assert title == "Build Guide"
    assert "Build Guide" in md
    assert "dotnet build" in md
    assert "site footer junk" not in md  # chrome (footer/script) stripped from content
    # Links are resolved to absolute URLs (nav links included for crawling).
    assert "https://site.test/docs/intro" in links
    assert "https://site.test/docs/setup" in links
    assert "https://other.com/x" in links


def test_title_falls_back_to_h1_then_url():
    title, _, _ = extract("https://s/p", "<html><body><h1>Only H1</h1><p>hi</p></body></html>")
    assert title == "Only H1"


def test_path_prefix_keeps_crawl_in_subtree():
    assert _path_prefix("https://s/docs/build") == "https://s/docs/"
    assert _path_prefix("https://s/docs/") == "https://s/docs/"
    assert _path_prefix("https://s") == "https://s/"


def test_name_for_derives_filename_from_path():
    assert _name_for("https://s/docs/getting-started/build") == "docs/getting-started/build.md"
    assert _name_for("https://s/docs/x.html") == "docs/x.html"
    assert _name_for("https://s/").endswith(".md")


def test_normalize_strips_fragment_and_trailing_slash():
    assert _normalize("https://s/a/#section") == "https://s/a"
    assert _normalize("https://s/a") == "https://s/a"


def test_looks_binary():
    assert _looks_binary("https://s/file.pdf") is True
    assert _looks_binary("https://s/style.css") is True
    assert _looks_binary("https://s/docs/page") is False


def test_ingest_url_rejects_non_http():
    with pytest.raises(WebIngestError):
        ingest_url("ftp://example.com/x")
