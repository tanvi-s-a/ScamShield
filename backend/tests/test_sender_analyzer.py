from app.analyzers.sender_analyzer import analyze_sender


def test_lookalike_domain_flagged():
    features = analyze_sender(from_address="support@paypa1-login.example")
    assert features["lookalike_domain_score"] >= 0.75


def test_legitimate_domain_not_flagged_as_lookalike():
    features = analyze_sender(from_address="billing@paypal.com")
    assert features["lookalike_domain_score"] == 0.0


def test_from_reply_mismatch_detected():
    features = analyze_sender(
        from_address="security@bank-alerts.example",
        reply_to_address="reply@totally-different.example",
    )
    assert features["from_reply_mismatch"] == 1


def test_missing_auth_is_not_treated_as_failure():
    features = analyze_sender(from_address="a@example.com", auth_results={})
    assert features["spf_missing"] == 1
    assert features["spf_fail"] == 0
    assert features["dkim_missing"] == 1
    assert features["dmarc_missing"] == 1


def test_auth_failure_detected():
    features = analyze_sender(
        from_address="a@example.com",
        auth_results={"spf": "fail", "dkim": "pass", "dmarc": None},
    )
    assert features["spf_fail"] == 1
    assert features["spf_missing"] == 0
    assert features["dkim_pass"] == 1
    assert features["dmarc_missing"] == 1
