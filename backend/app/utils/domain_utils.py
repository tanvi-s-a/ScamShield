"""
Domain parsing and lookalike-domain scoring utilities.

No network calls are made here — everything operates on strings only,
per the project rule that URLs are analyzed but never visited.
"""
import re
import difflib

try:
    import tldextract
    _HAS_TLDEXTRACT = True
except ImportError:
    _HAS_TLDEXTRACT = False

# A short list of commonly-impersonated brand domains for lookalike scoring.
# Extend this list as needed for the demo dataset.
KNOWN_BRAND_DOMAINS = [
    "paypal.com", "google.com", "microsoft.com", "apple.com", "amazon.com",
    "bankofamerica.com", "chase.com", "wellsfargo.com", "netflix.com",
    "facebook.com", "instagram.com", "linkedin.com", "dropbox.com",
    "docusign.com", "irs.gov", "usps.com", "fedex.com", "ups.com",
]


def extract_domain(address_or_url: str) -> str:
    """Extract the registrable domain (e.g. 'paypa1-login.example') from an
    email address or URL string."""
    if not address_or_url:
        return ""
    address_or_url = address_or_url.strip().lower()

    # Email address case: take everything after '@'
    if "@" in address_or_url and "://" not in address_or_url:
        address_or_url = address_or_url.split("@")[-1]

    if _HAS_TLDEXTRACT:
        ext = tldextract.extract(address_or_url)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
        return ext.domain or address_or_url

    # Fallback without tldextract: strip scheme/path, take last two labels
    address_or_url = re.sub(r"^[a-z]+://", "", address_or_url)
    address_or_url = address_or_url.split("/")[0]
    parts = address_or_url.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else address_or_url


def domain_has_digits(domain: str) -> bool:
    return any(c.isdigit() for c in domain)


def domain_has_hyphen(domain: str) -> bool:
    return "-" in domain


def subdomain_count(host: str) -> int:
    if not host:
        return 0
    if _HAS_TLDEXTRACT:
        ext = tldextract.extract(host)
        if not ext.subdomain:
            return 0
        return len(ext.subdomain.split("."))
    return max(0, host.count(".") - 1)


def is_punycode(host: str) -> bool:
    return "xn--" in (host or "").lower()


def is_ip_address(host: str) -> bool:
    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host or ""))


def lookalike_domain_score(domain: str, brand_list=None) -> float:
    """
    Returns a 0-1 similarity score against the closest known brand domain.
    High score + not an exact match == likely lookalike (e.g. paypa1-login.example).

    Rather than comparing whole domain strings (which get diluted by extra
    segments like "-login" or ".example"), this compares each hyphen/dot
    separated label in the candidate domain against each brand's core name,
    since typosquats usually preserve the brand name as one label and add
    junk elsewhere (paypa1-login.example, paypal-secure.net, etc).
    """
    if not domain:
        return 0.0
    brand_list = brand_list or KNOWN_BRAND_DOMAINS
    if domain in brand_list:
        return 0.0  # exact legitimate match, not a lookalike

    core_domain = domain.split(".")[0]
    labels = [seg for seg in re.split(r"[.-]", domain) if seg]

    best = 0.0
    for brand in brand_list:
        brand_core = brand.split(".")[0]
        if brand_core == core_domain:
            continue  # exact core match against a brand means it likely *is* legit

        # Compare the whole leading label first (cheap, catches most cases)
        candidates = [core_domain] + labels
        for label in candidates:
            ratio = difflib.SequenceMatcher(None, label, brand_core).ratio()
            if ratio > best:
                best = ratio
    return round(best, 3)


def domains_match(a: str, b: str) -> bool:
    return bool(a) and bool(b) and extract_domain(a) == extract_domain(b)
