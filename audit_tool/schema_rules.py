"""
schema_rules.py
----------------
Defines what "valid" means for each schema.org @type. Two tiers:
  - required: missing = ERROR (Google/AI engines may reject rich result eligibility)
  - recommended: missing = WARNING (still valid schema, but weaker signal)

This is deliberately a plain data structure (not a class hierarchy) so you
can add a new type or tweak fields in 30 seconds without touching any logic.
"""

SCHEMA_RULES = {
    "Article": {
        "required": ["headline", "datePublished", "author"],
        "recommended": ["image", "dateModified", "publisher", "mainEntityOfPage"],
    },
    "BlogPosting": {
        "required": ["headline", "datePublished", "author"],
        "recommended": ["image", "dateModified", "publisher", "mainEntityOfPage"],
    },
    "NewsArticle": {
        "required": ["headline", "datePublished", "author"],
        "recommended": ["image", "dateModified", "publisher"],
    },
    "FAQPage": {
        "required": ["mainEntity"],
        "recommended": [],
    },
    "Question": {
        "required": ["name", "acceptedAnswer"],
        "recommended": [],
    },
    "BreadcrumbList": {
        "required": ["itemListElement"],
        "recommended": [],
    },
    "Product": {
        "required": ["name"],
        "recommended": ["image", "description", "offers", "aggregateRating", "brand"],
    },
    "Offer": {
        "required": ["price", "priceCurrency"],
        "recommended": ["availability"],
    },
    "HowTo": {
        "required": ["name", "step"],
        "recommended": ["totalTime", "estimatedCost", "image"],
    },
    "WebPage": {
        "required": ["name"],
        "recommended": ["description", "url"],
    },
    "WebSite": {
        "required": ["name", "url"],
        "recommended": ["potentialAction"],
    },
    "Organization": {
        "required": ["name"],
        "recommended": ["url", "logo", "sameAs"],
    },
    "LocalBusiness": {
        "required": ["name", "address"],
        "recommended": ["telephone", "openingHoursSpecification", "geo"],
    },
    "VideoObject": {
        "required": ["name", "description", "thumbnailUrl", "uploadDate"],
        "recommended": ["duration", "contentUrl"],
    },
    "Review": {
        "required": ["reviewRating", "author"],
        "recommended": ["itemReviewed", "datePublished"],
    },
    "AggregateRating": {
        "required": ["ratingValue", "reviewCount"],
        "recommended": ["bestRating"],
    },
    "SoftwareApplication": {
        "required": ["name"],
        "recommended": ["applicationCategory", "operatingSystem", "offers"],
    },
}

# Fields that should contain an ISO 8601 date (YYYY-MM-DD, optionally with time).
DATE_FIELDS = {"datePublished", "dateModified", "uploadDate"}

# Fields that should contain a URL.
URL_FIELDS = {"url", "logo", "thumbnailUrl", "contentUrl", "image"}
