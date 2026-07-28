"""Shared keyword lists and label mappings."""

LABEL_MAP = {"Ham": 0, "Phishing": 1, "Spam": 2}
INVERSE_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}

URGENCY_TERMS = [
    "act now", "act immediately", "urgent", "immediately", "verify your account",
    "your account will be suspended", "final notice", "action required",
    "expires today", "limited time", "within 24 hours", "confirm your identity",
]

PRIZE_TERMS = [
    "you won", "you've won", "claim your prize", "free gift", "free phone",
    "winner", "congratulations you", "selected to receive", "lottery",
    "claim now", "reward center",
]

CREDENTIAL_REQUEST_TERMS = [
    "verify your password", "enter your password", "confirm your password",
    "update your billing", "login to confirm", "reset your password",
    "provide your ssn", "social security number", "verify your identity",
    "confirm your account",
]

PAYMENT_REQUEST_TERMS = [
    "processing fee", "shipping fee required", "pay to claim", "wire transfer",
    "gift card", "payment information", "credit card details", "billing information",
]

PROMOTIONAL_TERMS = [
    "% off", "discount", "sale", "unsubscribe", "shop now", "new arrivals",
    "limited offer", "free shipping", "coupon", "deal",
]

SUSPICIOUS_URL_KEYWORDS = [
    "login", "verify", "secure", "account", "confirm", "update", "billing",
    "signin", "webscr", "recover", "unlock",
]

URL_SHORTENERS = [
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly",
    "rebrand.ly", "cutt.ly",
]
