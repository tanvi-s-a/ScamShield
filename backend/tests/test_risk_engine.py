from app.security.risk_engine import compute_risk, recommend_blocking_actions


def test_high_phishing_probability_yields_high_risk():
    probs = {"ham": 0.02, "phishing": 0.93, "spam": 0.05}
    sender = {"lookalike_domain_score": 0.9, "from_reply_mismatch": 1}
    link = {"suspicious_keyword_count": 1, "visible_destination_mismatch_count": 1}
    ad = {"suspicious_button_count": 1, "embedded_form_count": 1, "password_input_count": 1,
          "tracking_pixel_count": 1, "external_image_count": 1}
    result = compute_risk(probs, sender, link, ad)
    assert result["risk_level"] == "High Risk"
    assert result["risk_score"] >= 70


def test_low_risk_for_clean_email():
    probs = {"ham": 0.95, "phishing": 0.02, "spam": 0.03}
    sender, link, ad = {}, {}, {}
    result = compute_risk(probs, sender, link, ad)
    assert result["risk_level"] == "Low Risk"


def test_blocking_actions_scale_with_risk():
    low_actions = recommend_blocking_actions("Low Risk", {})
    high_actions = recommend_blocking_actions("High Risk", {"embedded_form_count": 1})
    assert not low_actions["disable_links"]
    assert high_actions["disable_links"]
    assert high_actions["remove_forms"]
