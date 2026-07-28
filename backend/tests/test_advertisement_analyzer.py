from app.analyzers.advertisement_analyzer import analyze_advertisement


def test_tracking_pixel_detected():
    images = [{"src": "https://tracking.example/x", "width": 1, "height": 1, "hidden": False}]
    features = analyze_advertisement(text="hello", images=images)
    assert features["tracking_pixel_count"] == 1


def test_embedded_form_and_password_input_detected():
    html = """<form><input type="password" name="pw" /></form>"""
    features = analyze_advertisement(text="update info", html_content=html)
    assert features["embedded_form_count"] == 1
    assert features["password_input_count"] == 1


def test_prize_terms_counted():
    features = analyze_advertisement(text="Congratulations! You won a free phone, claim now.")
    assert features["prize_term_count"] >= 1


def test_legitimate_promotion_has_no_prize_terms():
    features = analyze_advertisement(text="Save 20% on your next order. Shop now.")
    assert features["prize_term_count"] == 0
    assert features["promotional_term_count"] >= 1
