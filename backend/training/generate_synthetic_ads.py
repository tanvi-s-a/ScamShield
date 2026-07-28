"""
Generates the synthetic advertisement dataset (Section 7.5 of the plan).

Produces labeled HTML/text examples for categories that public email
datasets don't reliably label: tracking pixels, embedded forms, suspicious
buttons, fake prizes vs. legitimate promotions.

Only reserved demonstration domains (example.com/.org/.net) are used —
no real-world URLs appear anywhere in this generator, by design.

Output: backend/data/raw/synthetic_ads/synthetic_ads.csv
Columns: text, html_content, label (Ham/Phishing/Spam), category
"""
import csv
import random
from pathlib import Path

random.seed(42)

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "synthetic_ads" / "synthetic_ads.csv"

STORE_NAMES = ["Northwind Traders", "Bluepeak Outfitters", "Cedar & Co",
               "Harborline Goods", "Maple Street Market", "Fieldstone Supply"]
PRODUCTS = ["running shoes", "kitchenware", "office chairs", "backpacks",
            "winter coats", "desk lamps", "coffee gear", "garden tools"]


def legit_promo(n):
    rows = []
    for _ in range(n):
        store = random.choice(STORE_NAMES)
        product = random.choice(PRODUCTS)
        pct = random.choice([10, 15, 20, 25, 30])
        text = f"{store} newsletter: Save {pct}% on {product} this week. Visit our store to browse the full collection."
        html = f"""<h2>{store}</h2>
<p>Save {pct}% on {product}.</p>
<a href="https://shop.example.com/sale">View Sale</a>
<p><a href="https://shop.example.com/unsubscribe">Unsubscribe</a></p>"""
        rows.append((text, html, "Ham", "legitimate_promotion"))
    return rows


def legit_discount(n):
    rows = []
    for _ in range(n):
        store = random.choice(STORE_NAMES)
        text = f"Thanks for shopping with {store}. Here is a discount code for your next order: WELCOME10."
        html = f"""<h2>Thank you for shopping with {store}</h2>
<p>Use code WELCOME10 for 10% off your next order.</p>
<a href="https://shop.example.com/account">View your account</a>"""
        rows.append((text, html, "Ham", "legitimate_discount"))
    return rows


def ordinary_spam_ad(n):
    rows = []
    phrases = ["Best deals of the season", "Unbeatable prices today only",
               "Huge clearance sale", "Everything must go", "Buy one get one free",
               "Flash sale happening now", "Doorbuster prices this weekend"]
    stores = ["Deal Hub", "Bargain Bay", "Value Zone", "Clearance Corner", "Thrift Point"]
    for i in range(n):
        phrase = random.choice(phrases)
        store = random.choice(stores)
        pct = random.choice([20, 30, 40, 50, 60, 70])
        text = (f"{store}: {phrase}! Save up to {pct}% for a limited time. "
                f"Shop now before it's gone, order #{1000 + i}. Free shipping on all orders.")
        html = f"""<h2>{phrase}!</h2>
<p>{store} - Limited offer, up to {pct}% off. Free shipping on all orders.</p>
<a href="https://deals.example.net/shop{i % 50}">Shop Now</a>
<a href="https://deals.example.net/more{i % 50}">See More Deals</a>
<a href="https://deals.example.net/today{i % 50}">Today Only</a>"""
        rows.append((text, html, "Spam", "ordinary_spam"))
    return rows


def fake_prize_ad(n):
    rows = []
    prizes = ["free phone", "$500 gift card", "free vacation", "new laptop",
              "$1000 cash prize", "free smartwatch", "airline miles bundle"]
    names = ["Rewards Center", "Prize Notification", "Winner Services", "Bonus Team"]
    for i in range(n):
        prize = random.choice(prizes)
        sender_name = random.choice(names)
        ref = f"REF-{random.randint(100000, 999999)}"
        text = (f"{sender_name}: Congratulations! You have won a {prize}. "
                f"Reference {ref}. Verify your account immediately to claim your prize before it expires.")
        html = f"""<h2>You won a {prize}!</h2>
<p>Reference {ref}. Verify your account immediately.</p>
<a href="https://account-confirmation.example/verify?ref={i}">Claim Prize</a>
<img src="https://tracking.example/open?id={random.randint(1000,999999)}" width="1" height="1" />"""
        rows.append((text, html, "Phishing", "fake_prize"))
    return rows


def credential_phishing_ad(n):
    rows = []
    reasons = ["unusual sign-in activity", "a billing issue", "a security review",
               "an expired password", "suspicious device access"]
    for i in range(n):
        reason = random.choice(reasons)
        case_id = f"CASE-{random.randint(10000, 99999)}"
        text = (f"Account Security Notice ({case_id}): Your account has been limited due to {reason}. "
                f"Confirm your password and billing information immediately to avoid suspension.")
        html = f"""<h2>Account Limited - {case_id}</h2>
<p>Reason: {reason}. Confirm your password and billing information immediately.</p>
<form action="https://secure-login.example/confirm{i % 50}">
  <input type="text" name="username" />
  <input type="password" name="password" />
  <input type="text" name="card_number" />
  <button type="submit">Confirm Account</button>
</form>"""
        rows.append((text, html, "Phishing", "credential_phishing"))
    return rows


def tracking_pixel_examples(n):
    rows = []
    topics = ["product updates", "weekly digest", "community highlights",
              "industry news", "your account summary", "this week's stories"]
    for i in range(n):
        topic = random.choice(topics)
        text = f"Newsletter #{i}: {topic}. Here is what's new this week in our community."
        html = f"""<p>{topic} - issue #{i}.</p>
<img src="https://tracking.example/pixel?id={random.randint(1,999999)}" width="1" height="1" style="display:none" />"""
        rows.append((text, html, "Spam", "tracking_pixel"))
    return rows


def embedded_form_examples(n):
    rows = []
    services = ["streaming subscription", "cloud storage plan", "mobile phone plan",
                "insurance policy", "membership account"]
    for i in range(n):
        service = random.choice(services)
        text = (f"Payment Update Required: Please update your {service} payment information "
                f"to continue service without interruption. Ticket #{2000 + i}.")
        html = f"""<p>Update your {service} payment information. Ticket #{2000 + i}.</p>
<form action="https://billing-update.example/submit{i % 50}">
  <input type="text" name="card" />
  <input type="password" name="cvv" />
  <button type="submit">Update Now</button>
</form>"""
        rows.append((text, html, "Phishing", "embedded_form"))
    return rows


def disguised_link_examples(n):
    rows = []
    carriers = ["FastTrack Shipping", "GlobalPost", "QuickCourier", "ParcelWay"]
    for i in range(n):
        carrier = random.choice(carriers)
        tracking_num = f"{carrier[:2].upper()}{random.randint(100000,999999)}"
        text = (f"{carrier}: Your package {tracking_num} could not be delivered. "
                f"Reschedule delivery using the secure link below before it is returned to sender.")
        html = f"""<p>{carrier}: package {tracking_num} could not be delivered.</p>
<a href="https://delivery-reschedule.example/track{i % 50}">www.official-shipping.com</a>"""
        rows.append((text, html, "Phishing", "disguised_link"))
    return rows


def build_dataset():
    rows = []
    rows += legit_promo(500)
    rows += legit_discount(500)
    rows += ordinary_spam_ad(500)
    rows += fake_prize_ad(500)
    rows += credential_phishing_ad(500)
    rows += tracking_pixel_examples(250)
    rows += embedded_form_examples(150)
    rows += disguised_link_examples(250)
    random.shuffle(rows)
    return rows


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = build_dataset()
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "html_content", "label", "category"])
        writer.writerows(rows)
    print(f"Wrote {len(rows)} synthetic advertisement examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
