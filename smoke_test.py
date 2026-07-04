"""
smoke_test.py
-------------
Verifies the full pipeline WITHOUT hitting real websites — mocks page
fetches so you can confirm extraction, validation, and CSV output are all
correct. Run this any time after changing code, or right after cloning
the repo, to confirm everything works before pointing it at a real site.

Usage: python smoke_test.py
"""

import os
import csv
import yaml
from unittest.mock import patch

from audit_tool.extractor import extract_jsonld_blocks, fetch_sitemap_urls
from audit_tool.validator import validate_node
from audit_tool.auditor import run

FAKE_PAGES = {
    # A fully valid, complete Article — should come back completely clean.
    "https://example.com/good-article": """
    <html><head><script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Article","headline":"Test",
     "datePublished":"2026-01-01","dateModified":"2026-01-02",
     "author":{"@type":"Person","name":"Rohit"},
     "image":"https://example.com/img.jpg",
     "publisher":{"@type":"Organization","name":"IndexCraft"},
     "mainEntityOfPage":"https://example.com/good-article"}
    </script></head></html>
    """,

    # Article missing every required field.
    "https://example.com/incomplete-article": """
    <script type="application/ld+json">{"@context":"https://schema.org","@type":"Article"}</script>
    """,

    # A page using @graph with three nodes, one of which (BreadcrumbList)
    # has a structural problem (an item missing its position).
    "https://example.com/graph-page": """
    <script type="application/ld+json">
    {"@context":"https://schema.org","@graph":[
      {"@type":"Article","headline":"T","datePublished":"2026-01-01","author":{"name":"R"}},
      {"@type":"BreadcrumbList","itemListElement":[{"position":1,"name":"Home"},{"name":"Missing position"}]},
      {"@type":"WebPage","name":"Test Page"}
    ]}</script>
    """,

    # No JSON-LD anywhere on the page.
    "https://example.com/no-schema": "<html><body>Just plain content, no schema at all.</body></html>",

    # Malformed / broken JSON-LD block.
    "https://example.com/broken-json": """
    <script type="application/ld+json">{"@context": "https://schema.org", broken</script>
    """,
}


def mock_fetch(url, timeout=20):
    if url not in FAKE_PAGES:
        raise ValueError(f"Test fixture missing for {url}")
    return FAKE_PAGES[url]


def main():
    checks = 0

    # --- Unit-level checks on extraction + validation ---
    blocks = extract_jsonld_blocks(FAKE_PAGES["https://example.com/good-article"])
    assert len(blocks) == 1, "Expected 1 block from good-article"
    issues = validate_node(blocks[0])
    assert issues == [], f"Expected zero issues on a fully valid Article, got {issues}"
    print("[PASS] fully valid Article produces zero issues")
    checks += 1

    blocks = extract_jsonld_blocks(FAKE_PAGES["https://example.com/incomplete-article"])
    issues = validate_node(blocks[0])
    error_fields = {i["field"] for i in issues if i["severity"] == "error"}
    assert error_fields == {"headline", "datePublished", "author"}, f"Unexpected error fields: {error_fields}"
    print("[PASS] incomplete Article correctly flags all 3 required fields as errors")
    checks += 1

    blocks = extract_jsonld_blocks(FAKE_PAGES["https://example.com/graph-page"])
    assert len(blocks) == 3, f"Expected 3 nodes from @graph, got {len(blocks)}"
    types_found = {b["_raw_type"] for b in blocks}
    assert types_found == {"Article", "BreadcrumbList", "WebPage"}, f"Unexpected types: {types_found}"
    breadcrumb_block = next(b for b in blocks if b["_raw_type"] == "BreadcrumbList")
    breadcrumb_issues = validate_node(breadcrumb_block)
    assert any("position" in i["field"] for i in breadcrumb_issues), "Expected a missing-position error"
    print("[PASS] @graph correctly flattened into 3 nodes, structural breadcrumb error detected")
    checks += 1

    blocks = extract_jsonld_blocks(FAKE_PAGES["https://example.com/broken-json"])
    assert blocks[0]["_raw_type"] == "INVALID_JSON", "Expected malformed JSON to be tagged INVALID_JSON"
    issues = validate_node(blocks[0])
    assert issues[0]["severity"] == "error", "Malformed JSON should be an error"
    print("[PASS] malformed JSON-LD caught gracefully, not crashed")
    checks += 1

    # --- Sitemap index resolution (nested sitemaps) ---
    fake_index = '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><sitemap><loc>https://example.com/sub-sitemap.xml</loc></sitemap></sitemapindex>'
    fake_sub = '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.com/page-a</loc></url></urlset>'

    def mock_sitemap_fetch(url, timeout=20):
        return fake_index if "sub-sitemap" not in url else fake_sub

    with patch("audit_tool.extractor.fetch_html", side_effect=mock_sitemap_fetch):
        urls = fetch_sitemap_urls("https://example.com/sitemap.xml")
    assert urls == ["https://example.com/page-a"], f"Sitemap index resolution failed: {urls}"
    print("[PASS] nested sitemap index correctly resolved to final page URLs")
    checks += 1

    # --- Full pipeline run (auditor.run) against all fixture pages ---
    config = {
        "sitemap_url": "",
        "urls": list(FAKE_PAGES.keys()),
        "max_urls": 50,
        "request_delay_seconds": 0,
        "checks": {},
    }
    os.makedirs("/tmp", exist_ok=True)
    config_path = "/tmp/smoke_test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)

    with patch("audit_tool.auditor.fetch_html", side_effect=mock_fetch):
        issues_path, summary_path = run(config_path=config_path, output_dir="/tmp/smoke_test_reports")

    with open(summary_path) as f:
        summary_rows = {r["url"]: r for r in csv.DictReader(f)}

    assert summary_rows["https://example.com/good-article"]["status"] == "clean"
    assert summary_rows["https://example.com/incomplete-article"]["status"] == "errors_found"
    assert summary_rows["https://example.com/no-schema"]["status"] == "errors_found"
    assert summary_rows["https://example.com/broken-json"]["status"] == "errors_found"
    print("[PASS] full pipeline run correctly classifies all 5 fixture pages")
    checks += 1

    print(f"\n=== ALL {checks} CHECKS PASSED ===")
    print("Pipeline verified end-to-end: JSON-LD extraction, @graph flattening,")
    print("field validation, structural checks, sitemap parsing, and CSV output")
    print("are all working correctly.")


if __name__ == "__main__":
    main()
