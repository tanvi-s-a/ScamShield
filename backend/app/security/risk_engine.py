"""
Risk-scoring engine.

Combines Random Forest class probabilities with rule-based evidence from
the sender/link/advertisement analyzers into a single 0-100 risk score,
a risk level, and a list of human-readable findings.

These are project-defined scores for demonstration purposes, not an
industry-certified risk model.
"""

MAX_POINTS = {
    "phishing_probability": 40,
    "spam_probability": 10,
    "lookalike_sender_domain": 15,
    "from_reply_mismatch": 8,
    "auth_failure": 8,
    "suspicious_url_keyword": 20,
    "link_destination_mismatch": 15,
    "suspicious_button": 8,
    "embedded_form": 15,
    "tracking_pixel": 3,
    "external_image": 4,
}


def _clamp(value, low=0, high=100):
    return max(low, min(high, value))


def compute_risk(probabilities: dict, sender_features: dict, link_features: dict, ad_features: dict) -> dict:
    score = 0
    findings = []

    phishing_p = probabilities.get("phishing", 0.0)
    spam_p = probabilities.get("spam", 0.0)

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

    return {
        "risk_score": score,
        "risk_level": level,
        "findings": findings,
    }


def recommend_blocking_actions(risk_level: str, ad_features: dict) -> dict:
    """
    Deterministic rules, not ML output, control blocking recommendations
    (Section 17 of the project plan). The current MVP extension only
    *displays* these recommendations; actual DOM blocking is a stretch goal.
    """
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
