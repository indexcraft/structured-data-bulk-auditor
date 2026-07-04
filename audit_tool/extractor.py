"""
extractor.py
------------
Two jobs:
  1. Fetch a page's HTML (or parse a sitemap.xml for URLs)
  2. Pull every JSON-LD block out of the HTML and flatten @graph structures
     into a simple list of individual schema nodes, each tagged with the
     source URL so errors can be traced back to the right page.
"""

import json
import requests
from bs4 import BeautifulSoup


def fetch_html(url: str, timeout: int = 20) -> str:
    """Fetch raw HTML for a URL. Raises on network/HTTP errors — caller
    is expected to catch and log these per-URL rather than crash the run."""
    headers = {"User-Agent": "StructuredDataBulkAuditor/1.0 (+https://indexcraft.in)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def fetch_sitemap_urls(sitemap_url: str, timeout: int = 20) -> list:
    """Parse a standard sitemap.xml and return the list of <loc> URLs.
    Handles sitemap index files (a sitemap of sitemaps) one level deep."""
    xml_text = fetch_html(sitemap_url, timeout=timeout)
    soup = BeautifulSoup(xml_text, "xml")

    # Sitemap index case: <sitemapindex><sitemap><loc>...
    sub_sitemaps = [loc.text.strip() for loc in soup.select("sitemap > loc")]
    if sub_sitemaps:
        urls = []
        for sub in sub_sitemaps:
            urls.extend(fetch_sitemap_urls(sub, timeout=timeout))
        return urls

    # Regular sitemap case: <urlset><url><loc>...
    return [loc.text.strip() for loc in soup.select("url > loc")]


def extract_jsonld_blocks(html: str, source_url: str = "") -> list:
    """
    Returns a list of dicts, one per individual schema node found on the
    page. Each dict has:
        _source_url : where this came from (for reporting)
        _raw_type   : the @type value (string or first item if it's a list)
        ...plus all the original schema.org properties.

    Handles:
      - multiple <script type="application/ld+json"> tags on one page
      - a single block containing {"@graph": [...]} with several nodes
      - malformed JSON (returns an error marker instead of raising)
    """
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})

    blocks = []
    for i, script in enumerate(scripts):
        raw_text = script.string or script.get_text()
        if not raw_text or not raw_text.strip():
            continue
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            blocks.append({
                "_source_url": source_url,
                "_raw_type": "INVALID_JSON",
                "_parse_error": f"Block #{i+1}: {str(e)}",
            })
            continue

        # A page can have a single object, or a list of objects, or an
        # object containing @graph (a list of objects sharing one @context).
        if isinstance(data, dict) and "@graph" in data:
            nodes = data["@graph"]
        elif isinstance(data, list):
            nodes = data
        else:
            nodes = [data]

        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = node.get("@type", "UNKNOWN")
            if isinstance(node_type, list):
                node_type = node_type[0] if node_type else "UNKNOWN"
            node_copy = dict(node)
            node_copy["_source_url"] = source_url
            node_copy["_raw_type"] = node_type
            blocks.append(node_copy)

    return blocks
