"""
auditor.py
----------
Orchestrates a full run:
  1. Build the URL list (explicit config list + optional sitemap discovery)
  2. Fetch each page, extract JSON-LD, validate each schema node found
  3. Track "pages with zero structured data" as their own finding — a
     silent SEO gap that's easy to miss otherwise
  4. Write both CSV reports
"""

import os
import time
from datetime import datetime

import yaml

from audit_tool.extractor import fetch_html, fetch_sitemap_urls, extract_jsonld_blocks
from audit_tool.validator import validate_node
from audit_tool.report import write_issues_csv, write_page_summary_csv


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def build_url_list(config: dict) -> list:
    urls = list(dict.fromkeys(config.get("urls", [])))  # de-dupe, keep order

    sitemap_url = config.get("sitemap_url", "")
    if sitemap_url:
        print(f"[sitemap] discovering URLs from {sitemap_url}")
        try:
            sitemap_urls = fetch_sitemap_urls(sitemap_url)
            for u in sitemap_urls:
                if u not in urls:
                    urls.append(u)
            print(f"[sitemap] found {len(sitemap_urls)} URLs")
        except Exception as e:
            print(f"[sitemap] failed to read sitemap: {e}")

    max_urls = config.get("max_urls", 50)
    if len(urls) > max_urls:
        print(f"[cap] {len(urls)} URLs found, capping to max_urls={max_urls}")
        urls = urls[:max_urls]

    return urls


def audit_url(url: str, enabled_checks: dict) -> list:
    """Returns a list of result dicts for one URL: [{url, schema_type, issues}]"""
    try:
        html = fetch_html(url)
    except Exception as e:
        return [{"url": url, "schema_type": "PAGE_FETCH_ERROR", "issues": [
            {"severity": "error", "field": "-", "message": f"Could not fetch page: {e}"}
        ]}]

    blocks = extract_jsonld_blocks(html, source_url=url)

    if not blocks:
        return [{"url": url, "schema_type": "NONE", "issues": [
            {"severity": "error", "field": "-", "message": "No JSON-LD structured data found on this page at all"}
        ]}]

    results = []
    for block in blocks:
        issues = validate_node(block, enabled_checks)
        results.append({
            "url": url,
            "schema_type": block.get("_raw_type", "UNKNOWN"),
            "issues": issues,
        })
    return results


def run(config_path: str = "config.yaml", output_dir: str = "reports") -> tuple:
    config = load_config(config_path)
    enabled_checks = config.get("checks", {})
    delay = config.get("request_delay_seconds", 1.0)

    urls = build_url_list(config)
    print(f"[start] auditing {len(urls)} URL(s)")

    all_results = []
    for url in urls:
        print(f"[audit] {url}")
        all_results.extend(audit_url(url, enabled_checks))
        time.sleep(delay)

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    issues_path = os.path.join(output_dir, f"issues_{timestamp}.csv")
    summary_path = os.path.join(output_dir, f"page_summary_{timestamp}.csv")

    write_issues_csv(issues_path, all_results)
    write_page_summary_csv(summary_path, all_results)

    total_errors = sum(1 for r in all_results for i in r["issues"] if i["severity"] == "error")
    total_warnings = sum(1 for r in all_results for i in r["issues"] if i["severity"] == "warning")

    print("\n=== DONE ===")
    print(f"URLs audited:  {len(urls)}")
    print(f"Total errors:   {total_errors}")
    print(f"Total warnings: {total_warnings}")
    print(f"Issue detail:   {issues_path}")
    print(f"Page summary:   {summary_path}")

    return issues_path, summary_path
