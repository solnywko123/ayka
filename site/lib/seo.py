"""JSON-LD builders + sitemap.xml / robots.txt generation."""
from __future__ import annotations

import re
from xml.sax.saxutils import escape

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _parse_hours(work_hours_ru: str) -> tuple[str, str]:
    times = re.findall(r"(\d{2}:\d{2})", work_hours_ru)
    if len(times) >= 2:
        return times[0], times[1]
    return "08:00", "20:00"


def local_business_jsonld(config: dict, lang: str, page_url: str, reviews: list[dict] | None = None) -> dict:
    opens, closes = _parse_hours(config["work_hours"]["ru"])
    data = {
        "@context": "https://schema.org",
        "@type": "HomeAndConstructionBusiness",
        "name": config["company_name"],
        "image": f"https://{config['domain']}/img/og-default.png",
        "url": page_url,
        "telephone": config["phone"],
        "priceRange": "$$",
        "areaServed": config["service_area"],
        "openingHoursSpecification": {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": WEEKDAYS,
            "opens": opens,
            "closes": closes,
        },
    }
    if config.get("legal_name"):
        data["legalName"] = config["legal_name"]
    if config.get("address"):
        data["address"] = {
            "@type": "PostalAddress",
            "streetAddress": config["address"],
            "addressLocality": config["city"].get(lang, config["city"]["ru"]),
            "addressCountry": "KG",
        }
    geo = config.get("geo")
    if geo:
        data["geo"] = {"@type": "GeoCoordinates", "latitude": geo["lat"], "longitude": geo["lng"]}
    same_as = [v for v in (config.get("telegram"), config.get("instagram")) if v]
    if same_as:
        data["sameAs"] = same_as

    if reviews:
        rating = aggregate_rating_jsonld(reviews)
        if rating:
            data["aggregateRating"] = rating
    return data


def aggregate_rating_jsonld(reviews: list[dict]) -> dict | None:
    """Only ever built from non-placeholder reviews — see BRIEF.md section 5.1 / 17."""
    real = [r for r in reviews if not r.get("placeholder")]
    if not real:
        return None
    avg = sum(r["rating"] for r in real) / len(real)
    return {
        "@type": "AggregateRating",
        "ratingValue": round(avg, 1),
        "reviewCount": len(real),
        "bestRating": 5,
    }


def service_jsonld(config: dict, service: dict, page_url: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "serviceType": service["title"],
        "description": service.get("meta_description", service.get("short_description", "")),
        "provider": {"@type": "HomeAndConstructionBusiness", "name": config["company_name"]},
        "areaServed": config["service_area"],
        "url": page_url,
        "offers": {
            "@type": "Offer",
            "priceCurrency": config["currency"],
            "price": str(service["price_from"]),
            "url": page_url,
            "availability": "https://schema.org/InStock",
        },
    }


def faq_jsonld(items: list[dict]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": it["question"],
                "acceptedAnswer": {"@type": "Answer", "text": it["answer"]},
            }
            for it in items
        ],
    }


def breadcrumb_jsonld(items: list[tuple[str, str]]) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


def article_jsonld(config: dict, post: dict, page_url: str, image_url: str) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["title"],
        "description": post.get("description", ""),
        "image": image_url,
        "datePublished": post["date"],
        "dateModified": post.get("date_modified", post["date"]),
        "author": {"@type": "Organization", "name": config["company_name"]},
        "publisher": {"@type": "Organization", "name": config["company_name"]},
        "mainEntityOfPage": {"@type": "WebPage", "@id": page_url},
    }


def generate_sitemap(pages: list[dict]) -> str:
    """pages: [{"url": str, "lastmod": "YYYY-MM-DD", "alternates": {lang: url}}]"""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for page in pages:
        lines.append("  <url>")
        lines.append(f"    <loc>{escape(page['url'])}</loc>")
        lines.append(f"    <lastmod>{page['lastmod']}</lastmod>")
        for hreflang, alt_url in page.get("alternates", {}).items():
            lines.append(
                f'    <xhtml:link rel="alternate" hreflang="{hreflang}" href="{escape(alt_url)}" />'
            )
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def generate_robots(domain: str) -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        f"Sitemap: https://{domain}/sitemap.xml\n"
    )
