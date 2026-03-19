"""Tests for the content extraction pipeline."""

from webharvest.core.content import extract_content, extract_metadata, extract_links


def test_extract_content_strips_scripts(sample_html):
    _, markdown = extract_content(sample_html, "https://example.com")
    assert "console.log" not in markdown
    assert "Hello" in markdown or "main content" in markdown


def test_extract_metadata(sample_html):
    meta = extract_metadata(sample_html, "https://example.com")
    assert meta.title is not None
    assert meta.description == "A test page for WebHarvest"
    assert meta.language == "en"
    assert meta.og_image == "https://example.com/image.jpg"


def test_extract_links(sample_html):
    links = extract_links(sample_html, "https://example.com")
    assert "https://example.com/page1" in links
    assert "https://example.com/page2" in links


def test_full_page_mode(sample_html):
    _, markdown = extract_content(sample_html, "https://example.com", only_main_content=False)
    assert isinstance(markdown, str)
    assert len(markdown) > 0
