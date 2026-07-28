"""
Normalizes every raw dataset into one standard record format.

Output columns (Section 9 of the plan):
    source_dataset, message_id, subject, body, combined_text,
    from_address, from_domain, reply_to_address, reply_to_domain,
    return_path_domain, message_id_domain, html_content, label

Label mapping: 0 = Ham, 1 = Phishing, 2 = Spam

HOW TO USE WITH REAL DATA
--------------------------
This script does NOT download anything (no internet access is assumed).
Place the raw files yourself before running:

  backend/data/raw/kaggle/<kaggle_csv_file>.csv
      -> Kaggle "Biggest Spam Ham Phish Email Dataset" (Akshat Sharma)
         https://www.kaggle.com/datasets/  (search the exact slug)

  backend/data/raw/spamassassin/{easy_ham,easy_ham_2,hard_ham,spam,spam_2}/
      -> extracted Apache SpamAssassin Public Corpus folders, one raw
         .eml-style file per message (no extension)
         https://spamassassin.apache.org/old/publiccorpus/

  backend/data/raw/phishing/<curated_csv_or_files>
      -> Zenodo curated phishing collection

  backend/data/raw/enron/maildir/<user>/<folder>/<message files>
      -> CMU Enron email dataset (maildir layout)

Each loader below checks whether its expected files exist and safely skips
with a warning if they don't, so the pipeline still runs end-to-end using
only the synthetic advertisement dataset while you're getting the other
sources downloaded.

Run `python training/generate_synthetic_ads.py` first to create the
synthetic dataset, then run this script.
"""
import email
import glob
import os
from email import policy
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from app.utils.domain_utils import extract_domain
from app.utils.constants import LABEL_MAP

DATA_RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
DATA_PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"


def _base_record(**kwargs):
    record = {
        "source_dataset": "", "message_id": "", "subject": "", "body": "",
        "combined_text": "", "from_address": "", "from_domain": "",
        "reply_to_address": "", "reply_to_domain": "", "return_path_domain": "",
        "message_id_domain": "", "html_content": "", "label": None,
    }
    record.update(kwargs)
    record["combined_text"] = f"{record['subject']} {record['body']}".strip()
    record["from_domain"] = extract_domain(record["from_address"])
    record["reply_to_domain"] = extract_domain(record["reply_to_address"])
    return record


# ---------------------------------------------------------------------------
# Dataset A: Kaggle Biggest Spam Ham Phish Email Dataset
# ---------------------------------------------------------------------------
def load_kaggle(sample_per_class=5000):
    folder = DATA_RAW / "kaggle"
    csv_files = list(folder.glob("*.csv"))
    if not csv_files:
        print(f"[kaggle] No CSV found in {folder} — skipping. "
              f"Download the dataset and place the CSV there.")
        return []

    df = pd.read_csv(csv_files[0])
    # The exact column names must be confirmed after downloading (Section 7.1).
    # Common possibilities are handled here defensively.
    text_col = next((c for c in df.columns if c.lower() in ("text", "email_text", "body", "combined_text")), None)
    label_col = next((c for c in df.columns if c.lower() in ("label", "class", "target")), None)
    if not text_col or not label_col:
        print(f"[kaggle] Could not confidently identify text/label columns in {csv_files[0].name}: "
              f"{list(df.columns)}. Please inspect and adjust load_kaggle().")
        return []

    # Published mapping: 0=Ham, 1=Phish, 2=Spam (already matches our LABEL_MAP)
    records = []
    for label_value in sorted(df[label_col].unique()):
        subset = df[df[label_col] == label_value].head(sample_per_class)
        for _, row in subset.iterrows():
            records.append(_base_record(
                source_dataset="kaggle",
                body=str(row[text_col]),
                label=int(label_value),
            ))
    print(f"[kaggle] Loaded {len(records)} records")
    return records


# ---------------------------------------------------------------------------
# Dataset B: Apache SpamAssassin Public Corpus
# ---------------------------------------------------------------------------
def _parse_eml_file(path):
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    subject = msg.get("Subject", "") or ""
    from_address = msg.get("From", "") or ""
    reply_to = msg.get("Reply-To", "") or ""
    return_path = msg.get("Return-Path", "") or ""
    message_id = msg.get("Message-ID", "") or ""

    body_text, html_content = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            try:
                content = part.get_content()
            except Exception:
                continue
            if ctype == "text/plain" and not body_text:
                body_text = content
            elif ctype == "text/html" and not html_content:
                html_content = content
    else:
        try:
            content = msg.get_content()
        except Exception:
            content = ""
        if msg.get_content_type() == "text/html":
            html_content = content
        else:
            body_text = content

    if not body_text and html_content:
        body_text = BeautifulSoup(html_content, "lxml").get_text(" ")

    return subject, body_text, html_content, from_address, reply_to, return_path, message_id


def load_spamassassin(sample_sizes=None):
    sample_sizes = sample_sizes or {"easy_ham": 2000, "hard_ham": 250, "spam": 1500, "spam_2": 1500}
    folder = DATA_RAW / "spamassassin"
    if not folder.exists() or not any(folder.iterdir()):
        print(f"[spamassassin] No data found in {folder} — skipping. "
              f"Download and extract the public corpus folders there.")
        return []

    records = []
    for category, limit in sample_sizes.items():
        cat_dir = folder / category
        if not cat_dir.exists():
            continue
        label = 0 if "ham" in category else 2  # Ham=0, Spam=2 (SpamAssassin has no phishing label)
        files = sorted(glob.glob(str(cat_dir / "*")))[:limit]
        for fp in files:
            try:
                subject, body, html_content, frm, reply_to, ret_path, msgid = _parse_eml_file(fp)
            except Exception:
                continue
            records.append(_base_record(
                source_dataset="spamassassin",
                message_id=msgid, subject=subject, body=body,
                from_address=frm, reply_to_address=reply_to,
                return_path_domain=extract_domain(ret_path),
                message_id_domain=extract_domain(msgid),
                html_content=html_content, label=label,
            ))
    print(f"[spamassassin] Loaded {len(records)} records")
    return records


# ---------------------------------------------------------------------------
# Dataset C: Curated phishing collection (Zenodo)
# ---------------------------------------------------------------------------
def load_curated_phishing(limit=5000):
    folder = DATA_RAW / "phishing"
    csv_files = list(folder.glob("*.csv"))
    if not csv_files:
        print(f"[phishing] No CSV found in {folder} — skipping. Download the curated collection there.")
        return []

    records = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        text_col = next((c for c in df.columns if c.lower() in ("body", "text", "email_text")), None)
        subject_col = next((c for c in df.columns if c.lower() == "subject"), None)
        from_col = next((c for c in df.columns if c.lower() in ("from", "sender", "from_address")), None)
        if not text_col:
            print(f"[phishing] Skipping {csv_file.name}: no recognizable text column ({list(df.columns)})")
            continue
        for _, row in df.head(limit).iterrows():
            records.append(_base_record(
                source_dataset=f"phishing:{csv_file.stem}",
                subject=str(row[subject_col]) if subject_col else "",
                body=str(row[text_col]),
                from_address=str(row[from_col]) if from_col else "",
                label=LABEL_MAP["Phishing"],
            ))
    print(f"[phishing] Loaded {len(records)} records")
    return records


# ---------------------------------------------------------------------------
# Dataset D: Enron (legitimate workplace email)
# ---------------------------------------------------------------------------
def load_enron(limit=5000):
    folder = DATA_RAW / "enron" / "maildir"
    if not folder.exists():
        print(f"[enron] No data found in {folder} — skipping. Download the Enron maildir there.")
        return []

    records = []
    files = glob.glob(str(folder / "**" / "*"), recursive=True)
    files = [f for f in files if os.path.isfile(f)]
    for fp in files[:limit]:
        try:
            subject, body, html_content, frm, reply_to, ret_path, msgid = _parse_eml_file(fp)
        except Exception:
            continue
        records.append(_base_record(
            source_dataset="enron",
            message_id=msgid, subject=subject, body=body,
            from_address=frm, reply_to_address=reply_to,
            return_path_domain=extract_domain(ret_path),
            message_id_domain=extract_domain(msgid),
            html_content=html_content, label=LABEL_MAP["Ham"],
        ))
    print(f"[enron] Loaded {len(records)} records")
    return records


# ---------------------------------------------------------------------------
# Dataset E: synthetic advertisements
# ---------------------------------------------------------------------------
def load_synthetic_ads():
    fp = DATA_RAW / "synthetic_ads" / "synthetic_ads.csv"
    if not fp.exists():
        print(f"[synthetic] {fp} not found — run generate_synthetic_ads.py first. Skipping.")
        return []
    df = pd.read_csv(fp)
    records = []
    for _, row in df.iterrows():
        records.append(_base_record(
            source_dataset="synthetic_ads",
            body=str(row["text"]),
            html_content=str(row["html_content"]),
            label=LABEL_MAP[row["label"]],
        ))
    print(f"[synthetic] Loaded {len(records)} records")
    return records


def main():
    all_records = []
    all_records += load_kaggle()
    all_records += load_spamassassin()
    all_records += load_curated_phishing()
    all_records += load_enron()
    all_records += load_synthetic_ads()

    if not all_records:
        raise SystemExit(
            "No records loaded from any source. At minimum, run "
            "generate_synthetic_ads.py first so the pipeline has data to work with."
        )

    df = pd.DataFrame(all_records)
    df = df.dropna(subset=["label"])
    df = df.drop_duplicates(subset=["combined_text"])

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out_path = DATA_PROCESSED / "combined_email_features.csv"
    df.to_csv(out_path, index=False)

    print(f"\nWrote {len(df)} normalized records to {out_path}")
    print("Records per source:")
    print(df["source_dataset"].value_counts())
    print("\nRecords per label (0=Ham, 1=Phishing, 2=Spam):")
    print(df["label"].value_counts())


if __name__ == "__main__":
    main()
