"""
Advertisement / HTML-content analyzer.

Looks at raw HTML plus structured extension-provided elements (images,
buttons, forms) to score promotional/malicious-advertisement signals.
"""
from bs4 import BeautifulSoup
from app.utils.constants import (
    PROMOTIONAL_TERMS, PRIZE_TERMS, URGENCY_TERMS,
    CREDENTIAL_REQUEST_TERMS, PAYMENT_REQUEST_TERMS,
)


def _count_terms(text: str, terms: list[str]) -> int:
    text = (text or "").lower()
    return sum(text.count(t) for t in terms)


def analyze_advertisement(
    text: str = "",
    html_content: str = "",
    images: list[dict] | None = None,
    buttons: list[dict] | None = None,
    forms_present: bool = False,
) -> dict:
    images = images or []
    buttons = buttons or []

    soup = BeautifulSoup(html_content or "", "lxml") if html_content else None

    tracking_pixel_count = sum(
        1 for img in images
        if (img.get("width") in (0, 1) and img.get("height") in (0, 1)) or img.get("hidden")
    )
    external_image_count = sum(1 for img in images if img.get("src", "").startswith("http"))

    suspicious_button_count = 0
    for b in buttons:
        button_text = (b.get("text") or "").lower()
        if _count_terms(button_text, PRIZE_TERMS + CREDENTIAL_REQUEST_TERMS + URGENCY_TERMS) > 0:
            suspicious_button_count += 1

    embedded_form_count = 0
    password_input_count = 0
    iframe_count = 0
    script_count = 0
    hidden_element_count = 0

    if soup is not None:
        embedded_form_count = len(soup.find_all("form"))
        password_input_count = len(soup.find_all("input", {"type": "password"}))
        iframe_count = len(soup.find_all("iframe"))
        script_count = len(soup.find_all("script"))
        for tag in soup.find_all(style=True):
            style = tag.get("style", "").replace(" ", "").lower()
            if "display:none" in style or "visibility:hidden" in style:
                hidden_element_count += 1
    elif forms_present:
        embedded_form_count = 1

    combined_text = text or ""
    if soup is not None:
        combined_text += " " + soup.get_text(" ")

    features = {
        "promotional_term_count": _count_terms(combined_text, PROMOTIONAL_TERMS),
        "prize_term_count": _count_terms(combined_text, PRIZE_TERMS),
        "urgency_term_count": _count_terms(combined_text, URGENCY_TERMS),
        "credential_request_count": _count_terms(combined_text, CREDENTIAL_REQUEST_TERMS),
        "payment_request_count": _count_terms(combined_text, PAYMENT_REQUEST_TERMS),
        "external_image_count": external_image_count,
        "tracking_pixel_count": tracking_pixel_count,
        "suspicious_button_count": suspicious_button_count,
        "embedded_form_count": embedded_form_count,
        "password_input_count": password_input_count,
        "iframe_count": iframe_count,
        "script_count": script_count,
        "hidden_element_count": hidden_element_count,
        "advertisement_section_count": 1 if _count_terms(combined_text, PROMOTIONAL_TERMS + PRIZE_TERMS) > 0 else 0,
        "external_domain_count": len({img.get("src", "") for img in images if img.get("src", "").startswith("http")}),
    }
    return features


AD_FEATURE_NAMES = [
    "promotional_term_count", "prize_term_count", "urgency_term_count",
    "credential_request_count", "payment_request_count", "external_image_count",
    "tracking_pixel_count", "suspicious_button_count", "embedded_form_count",
    "password_input_count", "iframe_count", "script_count",
    "hidden_element_count", "advertisement_section_count", "external_domain_count",
]
