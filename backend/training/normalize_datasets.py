"""Normalize MailShield datasets into one training table.

The repository ships with ``data/email_dataset (1).csv``.  This script
loads that file automatically, and also supports optional raw datasets placed
under ``data/raw``.  Labels are normalized to 0=Ham, 1=Phishing, 2=Spam.
"""
from __future__ import annotations

import email
import glob
import os
from email import policy
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from app.utils.constants import LABEL_MAP
from app.utils.domain_utils import extract_domain

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_PROCESSED = DATA_DIR / "processed"
LOCAL_DATASET = DATA_DIR / "email_dataset (1).csv"


def _clean(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _label(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)) and int(value) in (0, 1, 2):
        return int(value)
    text = str(value).strip().lower()
    mapping = {
        "ham": 0, "legitimate": 0, "legit": 0, "safe": 0, "normal": 0,
        "phishing": 1, "phish": 1, "malicious": 1,
        "spam": 2, "advertisement": 2, "advertising": 2,
    }
    return mapping.get(text)


def _base_record(**kwargs: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "source_dataset": "", "message_id": "", "subject": "", "body": "",
        "combined_text": "", "from_address": "", "from_domain": "",
        "reply_to_address": "", "reply_to_domain": "", "return_path_domain": "",
        "message_id_domain": "", "html_content": "", "label": None,
    }
    record.update(kwargs)
    for key in ("source_dataset", "message_id", "subject", "body", "from_address",
                "reply_to_address", "return_path_domain", "message_id_domain", "html_content"):
        record[key] = _clean(record.get(key))
    record["combined_text"] = f"{record['subject']} {record['body']}".strip()
    record["from_domain"] = extract_domain(record["from_address"])
    record["reply_to_domain"] = extract_domain(record["reply_to_address"])
    record["label"] = _label(record.get("label"))
    return record


def load_bundled_dataset() -> list[dict[str, Any]]:
    if not LOCAL_DATASET.exists():
        print(f"[bundled] {LOCAL_DATASET.name} not found — skipping")
        return []
    df = pd.read_csv(LOCAL_DATASET)
    required = {"subject", "body", "label"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Bundled dataset is missing columns: {sorted(missing)}")
    sender_col = "sender" if "sender" in df.columns else "from_address"
    rows = [
        _base_record(
            source_dataset="bundled_local",
            message_id=row.get("email_id", ""),
            subject=row.get("subject", ""),
            body=row.get("body", ""),
            from_address=row.get(sender_col, ""),
            label=row.get("label"),
        )
        for _, row in df.iterrows()
    ]
    rows = [r for r in rows if r["label"] is not None and r["combined_text"]]
    print(f"[bundled] Loaded {len(rows)} records")
    return rows


def _parse_eml_file(path: str | Path) -> tuple[str, str, str, str, str, str, str]:
    with open(path, "rb") as handle:
        msg = email.message_from_binary_file(handle, policy=policy.default)
    subject = _clean(msg.get("Subject", ""))
    from_address = _clean(msg.get("From", ""))
    reply_to = _clean(msg.get("Reply-To", ""))
    return_path = _clean(msg.get("Return-Path", ""))
    message_id = _clean(msg.get("Message-ID", ""))
    body_text, html_content = "", ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_maintype() == "multipart":
            continue
        try:
            content = part.get_content()
        except Exception:
            continue
        if part.get_content_type() == "text/plain" and not body_text:
            body_text = _clean(content)
        elif part.get_content_type() == "text/html" and not html_content:
            html_content = _clean(content)
    if not body_text and html_content:
        body_text = BeautifulSoup(html_content, "lxml").get_text(" ", strip=True)
    return subject, body_text, html_content, from_address, reply_to, return_path, message_id


def load_spamassassin(limit_per_folder: int = 3000) -> list[dict[str, Any]]:
    folder = DATA_RAW / "spamassassin"
    if not folder.exists():
        return []
    records: list[dict[str, Any]] = []
    for category in ("easy_ham", "easy_ham_2", "hard_ham", "spam", "spam_2"):
        cat_dir = folder / category
        if not cat_dir.exists():
            continue
        label = LABEL_MAP["Ham"] if "ham" in category else LABEL_MAP["Spam"]
        for path in sorted(p for p in cat_dir.iterdir() if p.is_file())[:limit_per_folder]:
            try:
                subject, body, html_content, frm, reply, ret, msgid = _parse_eml_file(path)
            except Exception:
                continue
            records.append(_base_record(
                source_dataset=f"spamassassin:{category}", message_id=msgid,
                subject=subject, body=body, html_content=html_content,
                from_address=frm, reply_to_address=reply,
                return_path_domain=extract_domain(ret), message_id_domain=extract_domain(msgid),
                label=label,
            ))
    if records:
        print(f"[spamassassin] Loaded {len(records)} records")
    return records


def load_generic_csvs() -> list[dict[str, Any]]:
    """Load optional CSVs from data/raw/kaggle and data/raw/phishing defensively."""
    records: list[dict[str, Any]] = []
    for folder_name in ("kaggle", "phishing"):
        for csv_path in (DATA_RAW / folder_name).glob("*.csv"):
            try:
                df = pd.read_csv(csv_path)
            except Exception as exc:
                print(f"[{folder_name}] Skipping {csv_path.name}: {exc}")
                continue
            lower = {c.lower(): c for c in df.columns}
            text_col = next((lower[k] for k in ("body", "text", "email_text", "message", "combined_text") if k in lower), None)
            subject_col = lower.get("subject")
            sender_col = next((lower[k] for k in ("sender", "from", "from_address") if k in lower), None)
            label_col = next((lower[k] for k in ("label", "class", "target", "category") if k in lower), None)
            if not text_col:
                print(f"[{folder_name}] Skipping {csv_path.name}: no text column")
                continue
            for _, row in df.iterrows():
                label = _label(row.get(label_col)) if label_col else (1 if folder_name == "phishing" else None)
                if label is None:
                    continue
                records.append(_base_record(
                    source_dataset=f"{folder_name}:{csv_path.stem}",
                    subject=row.get(subject_col, "") if subject_col else "",
                    body=row.get(text_col, ""),
                    from_address=row.get(sender_col, "") if sender_col else "",
                    label=label,
                ))
    if records:
        print(f"[optional csv] Loaded {len(records)} records")
    return records


def main() -> None:
    records: list[dict[str, Any]] = []
    records.extend(load_bundled_dataset())
    records.extend(load_spamassassin())
    records.extend(load_generic_csvs())
    if not records:
        raise SystemExit("No usable training records were found.")

    df = pd.DataFrame(records)
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)
    df["combined_text"] = df["combined_text"].fillna("").astype(str).str.strip()
    df = df[df["combined_text"].str.len() >= 4]
    df["dedupe_key"] = df["combined_text"].str.lower().str.replace(r"\s+", " ", regex=True)
    before = len(df)
    df = df.drop_duplicates(subset=["dedupe_key"]).drop(columns=["dedupe_key"])

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    output = DATA_PROCESSED / "combined_email_features.csv"
    df.to_csv(output, index=False)
    print(f"Wrote {len(df)} records to {output} ({before - len(df)} duplicates removed)")
    print(df["label"].value_counts().sort_index().rename(index={0: "Ham", 1: "Phishing", 2: "Spam"}))


if __name__ == "__main__":
    main()
