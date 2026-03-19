"""
Content extraction pipeline — the HEART of WebHarvest.

Three-stage pipeline that converts raw HTML into agent-friendly content:

  Stage 1 — Readability:  Extract main article content, strip boilerplate
  Stage 2 — Cleanup:      Remove ads, nav, footer, scripts, cookie banners
  Stage 3 — Markdown:     Convert clean HTML to well-formatted markdown

Also handles metadata extraction (title, description, OG tags, links, language).
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment
from markdownify import markdownify as md
from readability import Document

from webharvest.models.responses import PageMetadata


# ── Elements and class/id patterns to strip ──────────────────
STRIP_TAGS = {"script", "style", "noscript", "iframe", "svg"}
BOILERPLATE_TAGS = {"nav", "footer", "header", "aside"}
AD_PATTERNS = re.compile(
    r"(ad[-_]?(banner|slot|unit|container|wrapper))|"
    r"(cookie[-_]?(banner|consent|notice|popup))|"
    r"(sidebar|popup|modal|overlay|newsletter|signup)",
    re.IGNORECASE,
)


def extract_content(
    raw_html: str,
    url: str,
    *,
    only_main_content: bool = True,
    include_tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
) -> tuple[str, str]:
    """
    Extract clean content from raw HTML.

    Returns:
        (clean_html, markdown) — both forms of the cleaned content.
    """
    # ── Stage 1: Readability ─────────────────────────────────
    if only_main_content:
        doc = Document(raw_html, url=url)
        html = doc.summary()
    else:
        html = raw_html

    # ── Stage 2: Cleanup with BeautifulSoup ──────────────────
    soup = BeautifulSoup(html, "lxml")

    # Remove comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    # Remove unwanted tags
    tags_to_remove = STRIP_TAGS.copy()
    if not only_main_content:
        tags_to_remove.update(BOILERPLATE_TAGS)
    if exclude_tags:
        tags_to_remove.update(exclude_tags)

    for tag_name in tags_to_remove:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove ad-like elements by class/id
    for el in soup.find_all(True):
        classes = " ".join(el.get("class", []))
        el_id = el.get("id", "")
        if AD_PATTERNS.search(classes) or AD_PATTERNS.search(el_id):
            el.decompose()

    # Keep only specific tags if requested
    if include_tags:
        allowed = set(include_tags) | {"html", "body"}
        for el in soup.find_all(True):
            if el.name not in allowed:
                el.unwrap()

    clean_html = str(soup)

    # ── Stage 3: Markdown conversion ─────────────────────────
    markdown = md(
        clean_html,
        heading_style="ATX",
        bullets="-",
        strip=["img"],
    )

    # Post-process: collapse blank lines, trim whitespace
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = markdown.strip()

    return clean_html, markdown


def extract_metadata(raw_html: str, url: str) -> PageMetadata:
    """
    Extract page metadata: title, description, OG tags, language, canonical URL.
    """
    soup = BeautifulSoup(raw_html, "lxml")

    def meta_content(name: str | None = None, property: str | None = None) -> str | None:
        if name:
            tag = soup.find("meta", attrs={"name": name})
        elif property:
            tag = soup.find("meta", attrs={"property": property})
        else:
            return None
        return tag.get("content") if tag else None

    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    title = meta_content(property="og:title") or title

    return PageMetadata(
        title=title,
        description=meta_content(name="description") or meta_content(property="og:description"),
        language=soup.html.get("lang") if soup.html else None,
        og_image=meta_content(property="og:image"),
        og_type=meta_content(property="og:type"),
        og_site_name=meta_content(property="og:site_name"),
        canonical_url=_canonical(soup, url),
    )


def extract_links(raw_html: str, base_url: str) -> list[str]:
    """Extract all unique absolute URLs from anchor tags."""
    soup = BeautifulSoup(raw_html, "lxml")
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        parsed = urlparse(href)
        if parsed.scheme in ("http", "https") and href not in seen:
            seen.add(href)
            links.append(href)
    return links


def _canonical(soup: BeautifulSoup, url: str) -> str | None:
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        return urljoin(url, link["href"])
    return meta_content_from_soup(soup, property="og:url")


def meta_content_from_soup(soup: BeautifulSoup, **kwargs) -> str | None:
    tag = soup.find("meta", attrs=kwargs)
    return tag.get("content") if tag else None
