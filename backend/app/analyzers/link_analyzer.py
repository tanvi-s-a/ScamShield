"""
Link analyzer.

Operates on URL strings only. Nothing in this module ever opens a
network connection or visits a URL — that is a hard project rule.
"""
from urllib.parse import urlparse
from app.utils.domain_utils import (
    extract_domain, is_ip_address, is_punycode, subdomain_count, lookalike_domain_score,
)
from app.utils.constants import SUSPICIOUS_URL_KEYWORDS, URL_SHORTENERS


def _analyze_single_url(url: str) -> dict:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = parsed.netloc.lower()
    return {
        "is_https": parsed.scheme == "https",
        "is_ip": is_ip_address(host.split(":")[0]),
        "is_shortened": any(s in host for s in URL_SHORTENERS),
        "is_punycode": is_punycode(host),
        "has_suspicious_keyword": any(k in url.lower() for k in SUSPICIOUS_URL_KEYWORDS),
        "length": len(url),
        "subdomains": subdomain_count(host),
        "lookalike_score": lookalike_domain_score(extract_domain(host)),
        "looks_like_redirect": "redirect" in url.lower() or "url=" in url.lower() or "goto=" in url.lower(),
    }


def analyze_links(links: list[dict]) -> dict:
    """
    links: list of {"visible_text": str, "href": str} extracted from the
    Gmail DOM (or an .eml file). visible_text lets us detect mismatches
    between what the user sees and where the link actually points.
    """
    links = links or []
    per_url = [_analyze_single_url(l.get("href", "")) for l in links]

    mismatch_count = 0
    for link in links:
        visible = (link.get("visible_text") or "").strip().lower()
        href = (link.get("href") or "").strip().lower()
        # If the visible text itself looks like a URL/domain, compare domains.
        last_token = visible.split()[-1] if visible.split() else ""
        looks_like_url = visible.startswith("http") or "." in last_token
        if looks_like_url:
            visible_domain = extract_domain(visible)
            href_domain = extract_domain(href)
            if visible_domain and href_domain and visible_domain != href_domain:
                mismatch_count += 1

    features = {
        "url_count": len(links),
        "https_url_count": sum(1 for u in per_url if u["is_https"]),
        "http_url_count": sum(1 for u in per_url if not u["is_https"]),
        "ip_address_url_count": sum(1 for u in per_url if u["is_ip"]),
        "shortened_url_count": sum(1 for u in per_url if u["is_shortened"]),
        "punycode_url_count": sum(1 for u in per_url if u["is_punycode"]),
        "suspicious_keyword_count": sum(1 for u in per_url if u["has_suspicious_keyword"]),
        "visible_destination_mismatch_count": mismatch_count,
        "maximum_url_length": max([u["length"] for u in per_url], default=0),
        "maximum_subdomain_count": max([u["subdomains"] for u in per_url], default=0),
        "lookalike_url_domain_count": sum(1 for u in per_url if u["lookalike_score"] >= 0.75),
        "redirect_like_url_count": sum(1 for u in per_url if u["looks_like_redirect"]),
    }
    return features


LINK_FEATURE_NAMES = [
    "url_count", "https_url_count", "http_url_count", "ip_address_url_count",
    "shortened_url_count", "punycode_url_count", "suspicious_keyword_count",
    "visible_destination_mismatch_count", "maximum_url_length",
    "maximum_subdomain_count", "lookalike_url_domain_count", "redirect_like_url_count",
]
