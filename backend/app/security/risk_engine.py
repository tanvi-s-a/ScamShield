"""Hybrid MailShield risk engine.

Combines machine-learning probabilities with deterministic phishing signals.
The heuristic layer is intentionally independent of the model so obvious
lookalike domains, credential/payment requests, urgency, shortened URLs, and
prize lures can raise the final risk even when the small demo model is unsure.

Scores are project-defined for demonstration purposes, not an
industry-certified risk model.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from app.utils.constants import (
    CREDENTIAL_REQUEST_TERMS,
    PAYMENT_REQUEST_TERMS,
    PRIZE_TERMS,
    URGENCY_TERMS,
    URL_SHORTENERS,
)
from app.utils.domain_utils import extract_domain, lookalike_domain_score

MAX_POINTS = {
    "phishing_probability": 40,
    "spam_probability": 8,
    "lookalike_sender_domain": 24,
    "from_reply_mismatch": 8,
    "auth_failure": 8,
    "suspicious_url_keyword": 12,
    "link_destination_mismatch": 15,
    "shortened_url": 14,
    "lookalike_url_domain": 22,
    "ip_or_punycode_url": 15,
    "insecure_http_url": 5,
    "urgency_language": 14,
    "credential_request": 18,
    "payment_request": 16,
    "prize_lure": 10,
    "claimed_sender_lookalike": 22,
    "suspicious_button": 6,
    "embedded_form": 15,
    "tracking_pixel": 2,
    "external_image": 2,
}

URL_RE = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def _clamp(value: float, low: int = 0, high: int = 100) -> int:
    return int(max(low, min(high, value)))


def _contains_any(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term in lowered]


def _text_heuristics(subject: str, body: str, from_address: str = "") -> dict:
    """Extract high-value security signals directly from subject/body text.

    This also catches demo emails where a forged ``From:`` line is pasted into
    the body instead of being represented by the real Gmail message headers.
    URLs are only parsed as strings; they are never opened.
    """
    text = f"{subject}\n{body}".strip()
    urls = [u.rstrip(".,);]") for u in URL_RE.findall(text)]
    email_addresses = EMAIL_RE.findall(text)

    urgency_hits = _contains_any(text, URGENCY_TERMS)
    credential_hits = _contains_any(text, CREDENTIAL_REQUEST_TERMS)
    payment_hits = _contains_any(text, PAYMENT_REQUEST_TERMS)
    prize_hits = _contains_any(text, PRIZE_TERMS)

    # Broader phrases that commonly appear in phishing messages but may not be
    # present verbatim in the shared constants.
    lowered = text.lower()
    if not credential_hits and any(
        phrase in lowered
        for phrase in (
            "verify account", "verify your account", "update your account",
            "sign in to", "log in to", "confirm your login", "account verification",
        )
    ):
        credential_hits = ["account verification request"]
    if not payment_hits and any(
        phrase in lowered
        for phrase in (
            "update your payment", "payment method", "card information",
            "bank information", "update payment", "confirm payment",
        )
    ):
        payment_hits = ["payment information request"]
    if not urgency_hits and any(
        phrase in lowered
        for phrase in (
            "do not ignore", "service interruption", "account closure",
            "account locked", "account suspended", "respond immediately",
        )
    ):
        urgency_hits = ["urgent consequence language"]

    shortened_count = 0
    insecure_http_count = 0
    lookalike_url_count = 0
    ip_or_punycode_count = 0
    for url in urls:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if any(host == short or host.endswith(f".{short}") for short in URL_SHORTENERS):
            shortened_count += 1
        if parsed.scheme.lower() == "http":
            insecure_http_count += 1
        if lookalike_domain_score(extract_domain(host)) >= 0.75:
            lookalike_url_count += 1
        if host.startswith("xn--") or re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
            ip_or_punycode_count += 1

    # Inspect domains shown in pasted headers/body. Ignore the real sender
    # address here because sender_analyzer handles it separately.
    claimed_lookalike_count = 0
    real_sender_domain = extract_domain(from_address)
    for address in email_addresses:
        domain = extract_domain(address)
        if domain and domain != real_sender_domain and lookalike_domain_score(domain) >= 0.75:
            claimed_lookalike_count += 1

    return {
        "urgency_hits": urgency_hits,
        "credential_hits": credential_hits,
        "payment_hits": payment_hits,
        "prize_hits": prize_hits,
        "shortened_url_count": shortened_count,
        "insecure_http_count": insecure_http_count,
        "lookalike_url_count": lookalike_url_count,
        "ip_or_punycode_count": ip_or_punycode_count,
        "claimed_sender_lookalike_count": claimed_lookalike_count,
    }


def compute_risk(
    probabilities: dict,
    sender_features: dict,
    link_features: dict,
    ad_features: dict,
    *,
    subject: str = "",
    body: str = "",
    from_address: str = "",
) -> dict:
    score = 0.0
    findings: list[str] = []

    phishing_p = float(probabilities.get("phishing", 0.0) or 0.0)
    spam_p = float(probabilities.get("spam", 0.0) or 0.0)
    score += phishing_p * MAX_POINTS["phishing_probability"]
    score += spam_p * MAX_POINTS["spam_probability"]

    if phishing_p >= 0.5:
        findings.append("The message content strongly resembles known phishing language")
    elif spam_p >= 0.5:
        findings.append("The message content resembles typical spam wording")

    if sender_features.get("lookalike_domain_score", 0) >= 0.75:
        score += MAX_POINTS["lookalike_sender_domain"]
        findings.append("The sender domain closely resembles a well-known brand domain")

    if sender_features.get("from_reply_mismatch"):
        score += MAX_POINTS["from_reply_mismatch"]
        findings.append("The Reply-To address does not match the From address")

    auth_failed = any(sender_features.get(f"{p}_fail") for p in ("spf", "dkim", "dmarc"))
    if auth_failed:
        score += MAX_POINTS["auth_failure"]
        findings.append("Email authentication (SPF/DKIM/DMARC) failed")

    if link_features.get("suspicious_keyword_count", 0) > 0:
        score += MAX_POINTS["suspicious_url_keyword"]
        findings.append("A link contains suspicious keywords such as 'verify' or 'login'")

    if link_features.get("visible_destination_mismatch_count", 0) > 0:
        score += MAX_POINTS["link_destination_mismatch"]
        findings.append("A link's visible text does not match its actual destination")

    # Link analyzer signals from actual Gmail anchors.
    if link_features.get("shortened_url_count", 0) > 0:
        score += MAX_POINTS["shortened_url"]
        findings.append("A shortened link hides the final destination")
    if link_features.get("lookalike_url_domain_count", 0) > 0:
        score += MAX_POINTS["lookalike_url_domain"]
        findings.append("A link uses a domain resembling a trusted brand")
    if link_features.get("ip_address_url_count", 0) > 0 or link_features.get("punycode_url_count", 0) > 0:
        score += MAX_POINTS["ip_or_punycode_url"]
        findings.append("A link uses an IP address or encoded international domain")
    if link_features.get("http_url_count", 0) > 0:
        score += MAX_POINTS["insecure_http_url"]
        findings.append("A link uses unencrypted HTTP")

    text_signals = _text_heuristics(subject, body, from_address)
    if text_signals["claimed_sender_lookalike_count"]:
        score += MAX_POINTS["claimed_sender_lookalike"]
        findings.append("The message claims to use a lookalike brand email domain")
    if text_signals["urgency_hits"]:
        score += MAX_POINTS["urgency_language"]
        findings.append("The message uses urgency or threatens a negative consequence")
    if text_signals["credential_hits"]:
        score += MAX_POINTS["credential_request"]
        findings.append("The message asks for account verification or login information")
    if text_signals["payment_hits"]:
        score += MAX_POINTS["payment_request"]
        findings.append("The message asks the recipient to update or provide payment information")
    if text_signals["prize_hits"]:
        score += MAX_POINTS["prize_lure"]
        findings.append("The message uses a prize or cash-bonus lure")

    # Avoid scoring the same body URL twice if Gmail also exposed it as an anchor.
    if text_signals["shortened_url_count"] and not link_features.get("shortened_url_count", 0):
        score += MAX_POINTS["shortened_url"]
        findings.append("A shortened link hides the final destination")
    if text_signals["lookalike_url_count"] and not link_features.get("lookalike_url_domain_count", 0):
        score += MAX_POINTS["lookalike_url_domain"]
        findings.append("A link uses a domain resembling a trusted brand")
    if text_signals["ip_or_punycode_count"] and not (
        link_features.get("ip_address_url_count", 0) or link_features.get("punycode_url_count", 0)
    ):
        score += MAX_POINTS["ip_or_punycode_url"]
        findings.append("A link uses an IP address or encoded international domain")
    if text_signals["insecure_http_count"] and not link_features.get("http_url_count", 0):
        score += MAX_POINTS["insecure_http_url"]
        findings.append("A link uses unencrypted HTTP")

    if ad_features.get("suspicious_button_count", 0) > 0:
        score += MAX_POINTS["suspicious_button"]
        findings.append("A suspicious promotional button was detected")

    if ad_features.get("embedded_form_count", 0) > 0:
        score += MAX_POINTS["embedded_form"]
        findings.append("An embedded form was detected in the message")
        if ad_features.get("password_input_count", 0) > 0:
            findings.append("The embedded form requests a password")

    if ad_features.get("tracking_pixel_count", 0) > 0:
        score += MAX_POINTS["tracking_pixel"]
        findings.append("A tracking pixel was detected")

    if ad_features.get("external_image_count", 0) > 0:
        score += MAX_POINTS["external_image"]
        findings.append("The message loads external remote images")

    score = _clamp(round(score))
    if score >= 70:
        level = "High Risk"
    elif score >= 35:
        level = "Suspicious"
    else:
        level = "Low Risk"

    if not findings:
        findings.append("No significant risk indicators were detected")

    # Remove duplicate human-readable findings while preserving order.
    findings = list(dict.fromkeys(findings))
    return {
        "risk_score": score,
        "risk_level": level,
        "findings": findings,
        "heuristic_signals": text_signals,
    }


def hybrid_classification(model_classification: str, model_confidence: float, risk: dict) -> tuple[str, float]:
    """Return a user-facing label/confidence consistent with the hybrid score."""
    score = int(risk["risk_score"])
    level = risk["risk_level"]
    if level == "High Risk":
        return "Phishing", max(float(model_confidence) if model_classification == "Phishing" else 0.0, score / 100)
    if level == "Suspicious" and model_classification == "Ham":
        return "Suspicious", max(0.50, score / 100)
    return model_classification, float(model_confidence)


def recommend_blocking_actions(risk_level: str, ad_features: dict) -> dict:
    actions = {
        "disable_links": False,
        "hide_suspicious_promotions": False,
        "block_external_images": False,
        "remove_tracking_pixels": ad_features.get("tracking_pixel_count", 0) > 0,
        "remove_forms": False,
        "offer_safe_preview": False,
    }

    if risk_level == "Suspicious":
        actions["offer_safe_preview"] = True
    elif risk_level == "High Risk":
        actions.update({
            "disable_links": True,
            "hide_suspicious_promotions": True,
            "block_external_images": True,
            "remove_forms": ad_features.get("embedded_form_count", 0) > 0,
            "offer_safe_preview": True,
        })
    return actions
