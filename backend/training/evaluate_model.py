"""Evaluate the selected MailShield model on the saved held-out test split."""
from __future__ import annotations
import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, recall_score

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_PROCESSED = BACKEND_DIR / "data" / "processed"
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"
LABEL_NAMES = {0: "Ham", 1: "Phishing", 2: "Spam"}


def main() -> None:
    model_path = MODELS_DIR / "mailshield_model.joblib"
    test_path = DATA_PROCESSED / "test_split.csv"
    if not model_path.exists() or not test_path.exists():
        raise SystemExit("Run training/run_phase_1_to_3.py first.")
    model = joblib.load(model_path)
    df = pd.read_csv(test_path)
    df["combined_text"] = df["combined_text"].fillna("")
    y = df.pop("label").astype(int)
    prediction = model.predict(df)
    labels = sorted(set(y.tolist()) | set(prediction.tolist()))
    report = classification_report(y, prediction, labels=labels,
        target_names=[LABEL_NAMES[i] for i in labels], output_dict=True, zero_division=0)
    metrics = {
        "accuracy": float(accuracy_score(y, prediction)),
        "macro_f1": float(f1_score(y, prediction, labels=labels, average="macro", zero_division=0)),
        "phishing_recall": float(recall_score(y, prediction, labels=[1], average="macro", zero_division=0)) if 1 in labels else None,
        "confusion_matrix": confusion_matrix(y, prediction, labels=labels).tolist(),
        "confusion_matrix_labels": [LABEL_NAMES[i] for i in labels],
        "classification_report": report,
        "test_size": int(len(df)),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "evaluation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("accuracy", "macro_f1", "phishing_recall", "test_size")}, indent=2))


if __name__ == "__main__":
    main()
