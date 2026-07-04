"""
report.py
---------
Writes two CSVs from the audit results:
  - issues_TIMESTAMP.csv    : one row per individual issue found (detail view)
  - page_summary_TIMESTAMP.csv : one row per URL (pass/fail overview)
"""

import csv


def write_issues_csv(path: str, all_results: list):
    """all_results: list of dicts, each {url, schema_type, issues: [...]}"""
    fieldnames = ["url", "schema_type", "severity", "field", "message"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in all_results:
            if not result["issues"]:
                writer.writerow({
                    "url": result["url"], "schema_type": result["schema_type"],
                    "severity": "ok", "field": "-", "message": "No issues found",
                })
            for issue in result["issues"]:
                writer.writerow({
                    "url": result["url"],
                    "schema_type": result["schema_type"],
                    "severity": issue["severity"],
                    "field": issue["field"],
                    "message": issue["message"],
                })


def write_page_summary_csv(path: str, all_results: list):
    """Aggregates per-URL: how many schema blocks found, error count, warning count."""
    fieldnames = ["url", "schema_types_found", "total_blocks", "errors", "warnings", "status"]
    per_url = {}

    for result in all_results:
        url = result["url"]
        if url not in per_url:
            per_url[url] = {"types": set(), "blocks": 0, "errors": 0, "warnings": 0}
        per_url[url]["types"].add(result["schema_type"])
        per_url[url]["blocks"] += 1
        for issue in result["issues"]:
            if issue["severity"] == "error":
                per_url[url]["errors"] += 1
            elif issue["severity"] == "warning":
                per_url[url]["warnings"] += 1

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for url, data in per_url.items():
            if data["blocks"] == 0:
                status = "no_schema_found"
            elif data["errors"] > 0:
                status = "errors_found"
            elif data["warnings"] > 0:
                status = "warnings_only"
            else:
                status = "clean"
            writer.writerow({
                "url": url,
                "schema_types_found": ", ".join(sorted(data["types"])) if data["types"] else "none",
                "total_blocks": data["blocks"],
                "errors": data["errors"],
                "warnings": data["warnings"],
                "status": status,
            })
