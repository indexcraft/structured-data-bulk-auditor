# Structured Data Bulk Auditor

Crawls a set of pages (or a whole sitemap) and audits every JSON-LD structured data block against schema.org requirements — flagging missing required fields, weak/missing recommended fields, and structural mistakes (broken FAQ entries, breadcrumb items with no position, products with incomplete pricing, etc).

Built for technical SEO / GEO work where you need to check structured data compliance across dozens or hundreds of pages at once, instead of pasting one URL at a time into Google's Rich Results Test.

**Supports:** Article, BlogPosting, NewsArticle, FAQPage, BreadcrumbList, Product, HowTo, WebPage, WebSite, Organization, LocalBusiness, VideoObject, Review, SoftwareApplication — plus generic checks for date formats and URL fields, and correct handling of `@graph` structures (multiple schema nodes sharing one `<script>` block).

Output: two CSVs —
- **page_summary.csv** — one row per URL: how many schema blocks found, error/warning counts, overall status
- **issues.csv** — every individual issue found, with the exact field and message, so you can go straight to the fix

---

## 1. What you need

- **Python 3.10+**
- No API keys needed — this tool only fetches public pages and inspects their HTML, it doesn't call any paid service.

Check your Python version:
```bash
python3 --version
```

---

## 2. Setup (one-time)

```bash
cd structured-data-bulk-auditor

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## 3. Configure what to audit

Open **`config.yaml`**:

- **`sitemap_url`** — point this at any `sitemap.xml` (including a sitemap index — it resolves nested sitemaps automatically) to auto-discover every page
- **`urls`** — or just list specific pages directly, no sitemap needed
- **`max_urls`** — safety cap so a huge sitemap doesn't trigger hundreds of requests by accident
- **`checks`** — turn off any schema type you don't want checked

You can use both `sitemap_url` and `urls` together — they get merged and de-duplicated.

---

## 4. Run it

```bash
python run_audit.py
```

You'll see live progress as each page is fetched. Results land in the `reports/` folder as two timestamped CSVs.

---

## 5. Verifying it works (before pointing it at a real site)

```bash
python smoke_test.py
```

This mocks page fetches (no real network calls, no risk of hammering a live site) and checks that extraction, `@graph` flattening, field validation, structural rules, and sitemap parsing all produce correct results. You should see 6 `[PASS]` lines ending in `=== ALL 6 CHECKS PASSED ===`.

---

## 6. Reading the output

See `sample_output/page_summary_example.csv` and `sample_output/issues_example.csv` for the exact format.

**page_summary.csv columns:**
| column | meaning |
|---|---|
| schema_types_found | which @type blocks were found on this page |
| total_blocks | how many separate schema nodes were on the page |
| errors | count of missing-required-field / broken issues |
| warnings | count of missing-recommended-field issues |
| status | `clean`, `warnings_only`, `errors_found`, or `no_schema_found` |

**issues.csv** gives you the row-level detail — exact field name and message for every problem, so you (or whoever owns the CMS template) can go fix it directly.

---

## 7. What counts as an error vs a warning

- **Error** — a required field for that schema type is missing, the JSON itself is malformed, or a structural rule is broken (e.g. a FAQ question with no answer text, a breadcrumb item with no position). These are the things most likely to cost you rich-result eligibility.
- **Warning** — a recommended-but-not-required field is missing, or a date/URL field doesn't look correctly formatted. Still valid schema, just a weaker signal.

Edit `audit_tool/schema_rules.py` any time to add a new schema type or adjust which fields are required vs recommended for your site.

---

## 8. Extending it

- **New schema type** — add an entry to `SCHEMA_RULES` in `audit_tool/schema_rules.py`. No other code changes needed unless it needs structural checks beyond "is this field present" (see `_validate_faq_entities` in `validator.py` for an example of a deeper check).
- **Scheduling** — add a cron job to re-run this weekly and diff the CSVs to catch regressions after a template change or CMS migration.
- **CI integration** — run `python run_audit.py` in a pre-deploy check and fail the build if `errors > 0` in the summary CSV.

---

## Project structure

```
structured-data-bulk-auditor/
├── config.yaml                  # what to audit (edit this per site)
├── run_audit.py                  # run this to execute an audit
├── smoke_test.py                 # verifies the tool works, no real network calls
├── requirements.txt
├── audit_tool/
│   ├── schema_rules.py            # required/recommended fields per @type
│   ├── extractor.py                # fetches pages, extracts JSON-LD, parses sitemaps
│   ├── validator.py                # runs the actual validation logic
│   ├── report.py                   # writes the CSV output
│   └── auditor.py                  # orchestrates a full run
├── reports/                       # your run outputs land here
└── sample_output/                 # example CSVs so you can see the format
```

---

## For your resume / portfolio

Suggested bullet:
> Built an open-source Python tool that bulk-audits JSON-LD structured data across a sitemap, validating schema.org compliance (required/recommended fields, `@graph` structure, FAQ/Breadcrumb/Product-specific rules) and flagging issues that affect rich-result eligibility.

Push this to a public GitHub repo and link it directly from your resume/LinkedIn alongside the AI Citation Tracker — together they demonstrate both the "classic technical SEO" and "GEO/AI search" sides of the role.
