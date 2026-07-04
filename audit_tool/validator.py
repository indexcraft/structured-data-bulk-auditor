"""
validator.py
------------
Takes one extracted schema node (from extractor.py) and returns a list of
issues. Each issue is a dict: {severity, field, message}.

severity is either "error" (missing required field, broken JSON, etc. —
things that can cost rich-result eligibility) or "warning" (missing
recommended field, weak signal, but not disqualifying).
"""

import re
from datetime import datetime

from audit_tool.schema_rules import SCHEMA_RULES, DATE_FIELDS, URL_FIELDS

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _is_valid_date(value) -> bool:
    if not isinstance(value, str) or not ISO_DATE_RE.match(value):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00")[:19] if "T" in value else value)
        return True
    except ValueError:
        return False


def _is_valid_url(value) -> bool:
    if isinstance(value, dict):
        # e.g. ImageObject {"@type": "ImageObject", "url": "..."} instead of a plain string
        value = value.get("url", "")
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def validate_node(node: dict, enabled_checks: dict = None) -> list:
    """Validate a single extracted schema node. Returns a list of issue dicts."""
    issues = []
    node_type = node.get("_raw_type", "UNKNOWN")

    if node_type == "INVALID_JSON":
        return [{"severity": "error", "field": "-", "message": f"Malformed JSON-LD: {node.get('_parse_error', 'unknown parse error')}"}]

    if enabled_checks is not None and node_type in enabled_checks and not enabled_checks[node_type]:
        return []  # this type's checks are turned off in config

    rules = SCHEMA_RULES.get(node_type)
    if rules is None:
        # Not a type we have rules for — not an error, just nothing to check.
        return []

    for field in rules["required"]:
        if field not in node or node[field] in (None, "", [], {}):
            issues.append({"severity": "error", "field": field, "message": f"Missing required field '{field}' for @type {node_type}"})

    for field in rules["recommended"]:
        if field not in node or node[field] in (None, "", [], {}):
            issues.append({"severity": "warning", "field": field, "message": f"Missing recommended field '{field}' for @type {node_type}"})

    # Field-level sanity checks (only run if the field is actually present)
    for field in DATE_FIELDS:
        if field in node and node[field] and not _is_valid_date(node[field]):
            issues.append({"severity": "warning", "field": field, "message": f"'{field}' value doesn't look like a valid ISO 8601 date: {node[field]!r}"})

    for field in URL_FIELDS:
        if field in node and node[field] and not _is_valid_url(node[field]):
            issues.append({"severity": "warning", "field": field, "message": f"'{field}' doesn't look like a valid absolute URL: {str(node[field])[:80]!r}"})

    # Type-specific structural checks that go beyond "is the field present"
    if node_type == "FAQPage":
        issues.extend(_validate_faq_entities(node))
    elif node_type == "BreadcrumbList":
        issues.extend(_validate_breadcrumb_items(node))
    elif node_type == "HowTo":
        issues.extend(_validate_howto_steps(node))
    elif node_type == "Product" and "offers" in node:
        issues.extend(_validate_offer(node["offers"]))

    return issues


def _validate_faq_entities(node: dict) -> list:
    issues = []
    main_entity = node.get("mainEntity", [])
    if not isinstance(main_entity, list):
        main_entity = [main_entity]
    if len(main_entity) == 0:
        issues.append({"severity": "error", "field": "mainEntity", "message": "FAQPage has no Question entries"})
    for i, q in enumerate(main_entity):
        if not isinstance(q, dict):
            continue
        if q.get("@type") != "Question":
            issues.append({"severity": "warning", "field": f"mainEntity[{i}]", "message": "FAQ entry is missing @type: Question"})
        if not q.get("name"):
            issues.append({"severity": "error", "field": f"mainEntity[{i}].name", "message": "FAQ question is missing its text (name)"})
        answer = q.get("acceptedAnswer", {})
        if not isinstance(answer, dict) or not answer.get("text"):
            issues.append({"severity": "error", "field": f"mainEntity[{i}].acceptedAnswer", "message": "FAQ answer is missing acceptedAnswer.text"})
    return issues


def _validate_breadcrumb_items(node: dict) -> list:
    issues = []
    items = node.get("itemListElement", [])
    if not isinstance(items, list) or len(items) == 0:
        issues.append({"severity": "error", "field": "itemListElement", "message": "BreadcrumbList has no items"})
        return issues
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if "position" not in item:
            issues.append({"severity": "error", "field": f"itemListElement[{i}].position", "message": "Breadcrumb item missing position"})
        if not item.get("name") and not (isinstance(item.get("item"), dict) and item["item"].get("name")):
            issues.append({"severity": "error", "field": f"itemListElement[{i}].name", "message": "Breadcrumb item missing a name"})
    return issues


def _validate_howto_steps(node: dict) -> list:
    issues = []
    steps = node.get("step", [])
    if not isinstance(steps, list) or len(steps) == 0:
        issues.append({"severity": "error", "field": "step", "message": "HowTo has no steps"})
        return issues
    for i, step in enumerate(steps):
        if isinstance(step, dict) and not step.get("text") and not step.get("name"):
            issues.append({"severity": "error", "field": f"step[{i}]", "message": "HowTo step has no text or name"})
    return issues


def _validate_offer(offer) -> list:
    issues = []
    offers = offer if isinstance(offer, list) else [offer]
    for i, o in enumerate(offers):
        if not isinstance(o, dict):
            continue
        if not o.get("price"):
            issues.append({"severity": "error", "field": f"offers[{i}].price", "message": "Offer is missing a price"})
        if not o.get("priceCurrency"):
            issues.append({"severity": "error", "field": f"offers[{i}].priceCurrency", "message": "Offer is missing priceCurrency"})
    return issues
