"""
Runs the sender / link / advertisement analyzers over every row of
combined_email_features.csv to produce the final numeric feature table
used for training (Section 10 of the plan).

Note: the public datasets (Kaggle, curated phishing, most of Enron) do not
contain structured link/image/button lists the way live Gmail extraction
will. We approximate by extracting <a>/<img>/<form> tags from html_content
when present, and by regex-extracting raw URLs from body text otherwise.
This keeps train-time features consistent with what the live extension
sends at inference time (same feature names/order).
"""
import re
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

from app.analyzers.sender_analyzer import analyze_sender, SENDER_FEATURE_NAMES
from app.analyzers.link_analyzer import analyze_links, LINK_FEATURE_NAMES
from app.analyzers.advertisement_analyzer import analyze_advertisement, AD_FEATURE_NAMES

DATA_PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
URL_REGEX = re.compile(r"https?://[^\s\"'<>]+")


def _links_from_row(row) -> list[dict]:
    html_content = row.get("html_content") or ""
    if isinstance(html_content, str) and html_content.strip():
        soup = BeautifulSoup(html_content, "lxml")
        links = [{"visible_text": a.get_text(" ").strip(), "href": a.get("href", "")}
                 for a in soup.find_all("a") if a.get("href")]
        if links:
            return links
    # Fallback: raw URLs found in the body text, visible text unknown.
    body = row.get("body") or ""
    return [{"visible_text": "", "href": u} for u in URL_REGEX.findall(str(body))]


def _images_from_row(row) -> list[dict]:
    html_content = row.get("html_content") or ""
    if not isinstance(html_content, str) or not html_content.strip():
        return []
    soup = BeautifulSoup(html_content, "lxml")
    images = []
    for img in soup.find_all("img"):
        width = img.get("width")
        height = img.get("height")
        images.append({
            "src": img.get("src", ""),
            "width": int(width) if str(width).isdigit() else None,
            "height": int(height) if str(height).isdigit() else None,
            "hidden": "display:none" in (img.get("style", "").replace(" ", "")),
        })
    return images


def _buttons_from_row(row) -> list[dict]:
    html_content = row.get("html_content") or ""
    if not isinstance(html_content, str) or not html_content.strip():
        return []
    soup = BeautifulSoup(html_content, "lxml")
    buttons = []
    for btn in soup.find_all(["button"]):
        buttons.append({"text": btn.get_text(" ").strip(), "target": ""})
    # Treat prominent single links as buttons too (common in HTML emails)
    for a in soup.find_all("a"):
        if a.get_text(" ").strip().lower() in ("claim prize", "claim now", "click here", "verify now", "confirm account"):
            buttons.append({"text": a.get_text(" ").strip(), "target": a.get("href", "")})
    return buttons


def build_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    sender_rows, link_rows, ad_rows = [], [], []

    for _, row in df.iterrows():
        sender_rows.append(analyze_sender(
            from_address=str(row.get("from_address") or ""),
            reply_to_address=str(row.get("reply_to_address") or ""),
        ))
        links = _links_from_row(row)
        link_rows.append(analyze_links(links))
        images = _images_from_row(row)
        buttons = _buttons_from_row(row)
        ad_rows.append(analyze_advertisement(
            text=str(row.get("combined_text") or ""),
            html_content=str(row.get("html_content") or ""),
            images=images,
            buttons=buttons,
        ))

    sender_df = pd.DataFrame(sender_rows, columns=SENDER_FEATURE_NAMES)
    link_df = pd.DataFrame(link_rows, columns=LINK_FEATURE_NAMES)
    ad_df = pd.DataFrame(ad_rows, columns=AD_FEATURE_NAMES)

    features = pd.concat(
        [df[["source_dataset", "combined_text", "label"]].reset_index(drop=True),
         sender_df, link_df, ad_df],
        axis=1,
    )
    return features


def main():
    in_path = DATA_PROCESSED / "combined_email_features.csv"
    if not in_path.exists():
        raise SystemExit(f"{in_path} not found. Run normalize_datasets.py first.")

    df = pd.read_csv(in_path)
    df["combined_text"] = df["combined_text"].fillna("")
    features = build_feature_table(df)

    out_path = DATA_PROCESSED / "features_table.csv"
    features.to_csv(out_path, index=False)
    print(f"Wrote {len(features)} feature rows to {out_path}")
    print(f"Numeric feature columns: {len(SENDER_FEATURE_NAMES) + len(LINK_FEATURE_NAMES) + len(AD_FEATURE_NAMES)}")


if __name__ == "__main__":
    main()
