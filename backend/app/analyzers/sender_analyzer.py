"""
Sender / header analyzer.

Computes numeric features from From / Reply-To / Return-Path / Message-ID
and (optionally) SPF/DKIM/DMARC authentication results, when available.

IMPORTANT: missing authentication data is NOT treated as a failure.
We track *_missing flags separately from *_pass / *_fail so the model
never learns "no data == malicious."
"""
from app.utils.domain_utils import (
    extract_domain, domain_has_digits, domain_has_hyphen,
    subdomain_count, lookalike_domain_score, domains_match,
)


def analyze_sender(
    from_address: str = "",
    reply_to_address: str = "",
    return_path: str = "",
    message_id: str = "",
    auth_results: dict | None = None,
) -> dict:
    """
    auth_results, if provided, may contain any subset of:
        {"spf": "pass"/"fail"/None, "dkim": ..., "dmarc": ...}
    """
    auth_results = auth_results or {}
    from_domain = extract_domain(from_address)
    reply_domain = extract_domain(reply_to_address) if reply_to_address else ""
    return_domain = extract_domain(return_path) if return_path else ""
    msgid_domain = extract_domain(message_id) if message_id else ""

    features = {
        "sender_domain_length": len(from_domain),
        "sender_domain_has_digits": int(domain_has_digits(from_domain)),
        "sender_domain_has_hyphen": int(domain_has_hyphen(from_domain)),
        "sender_subdomain_count": subdomain_count(from_address.split("@")[-1] if "@" in from_address else from_domain),
        "from_reply_mismatch": int(bool(reply_domain) and from_domain != reply_domain),
        "from_return_mismatch": int(bool(return_domain) and from_domain != return_domain),
        "from_message_id_mismatch": int(bool(msgid_domain) and from_domain != msgid_domain),
        "lookalike_domain_score": lookalike_domain_score(from_domain),
    }

    for proto in ("spf", "dkim", "dmarc"):
        value = auth_results.get(proto)
        features[f"{proto}_pass"] = int(value == "pass")
        features[f"{proto}_fail"] = int(value == "fail")
        features[f"{proto}_missing"] = int(value not in ("pass", "fail"))

    return features


SENDER_FEATURE_NAMES = [
    "sender_domain_length", "sender_domain_has_digits", "sender_domain_has_hyphen",
    "sender_subdomain_count", "from_reply_mismatch", "from_return_mismatch",
    "from_message_id_mismatch", "lookalike_domain_score",
    "spf_pass", "spf_fail", "spf_missing",
    "dkim_pass", "dkim_fail", "dkim_missing",
    "dmarc_pass", "dmarc_fail", "dmarc_missing",
]
