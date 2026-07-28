from app.analyzers.link_analyzer import analyze_links


def test_visible_destination_mismatch_detected():
    links = [{"visible_text": "https://paypal.com", "href": "https://paypa1-login.example/verify"}]
    features = analyze_links(links)
    assert features["visible_destination_mismatch_count"] == 1


def test_no_mismatch_for_matching_domains():
    links = [{"visible_text": "https://example.com/page", "href": "https://example.com/other"}]
    features = analyze_links(links)
    assert features["visible_destination_mismatch_count"] == 0


def test_suspicious_keyword_detected():
    links = [{"visible_text": "", "href": "https://secure-login-verify.example/account"}]
    features = analyze_links(links)
    assert features["suspicious_keyword_count"] >= 1


def test_ip_address_url_detected():
    links = [{"visible_text": "", "href": "http://192.168.1.5/login"}]
    features = analyze_links(links)
    assert features["ip_address_url_count"] == 1


def test_empty_links_returns_zero_counts():
    features = analyze_links([])
    assert features["url_count"] == 0
    assert features["https_url_count"] == 0
