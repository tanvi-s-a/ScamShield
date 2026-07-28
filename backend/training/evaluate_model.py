"""
Evaluates the trained pipeline on the held-out test split (Section 14).

Reports accuracy, precision/recall/F1 (per-class, macro, weighted),
confusion matrix, phishing recall / false-negative rate, and saves a
confusion-matrix image.
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
)

DATA_PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

LABEL_NAMES = ["Ham", "Phishing", "Spam"]


def main():
    model_path = MODELS_DIR / "mailshield_random_forest.joblib"
    test_path = DATA_PROCESSED / "test_split.csv"
    if not model_path.exists() or not test_path.exists():
        raise SystemExit("Run train_model.py first.")

    pipeline = joblib.load(model_path)
    df = pd.read_csv(test_path)
    df["combined_text"] = df["combined_text"].fillna("")

    numeric_cols = [c for c in df.columns if c not in ("combined_text", "label")]
    X_test = df[["combined_text"] + numeric_cols]
    y_test = df["label"].astype(int)

    y_pred = pipeline.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(
        y_test, y_pred, labels=[0, 1, 2], target_names=LABEL_NAMES,
        output_dict=True, zero_division=0,
    )
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2])

    # Phishing (label 1) recall and false-negative rate
    phishing_row = cm[1]
    phishing_total = phishing_row.sum()
    phishing_recall = phishing_row[1] / phishing_total if phishing_total else None
    phishing_fnr = (1 - phishing_recall) if phishing_recall is not None else None

    metrics = {
        "accuracy": accuracy,
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
        "per_class": {name: report[name] for name in LABEL_NAMES},
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": LABEL_NAMES,
        "phishing_recall": phishing_recall,
        "phishing_false_negative_rate": phishing_fnr,
        "test_size": len(df),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / "evaluation_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        fig, ax = plt.subplots(figsize=(5, 4))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(3)); ax.set_xticklabels(LABEL_NAMES)
        ax.set_yticks(range(3)); ax.set_yticklabels(LABEL_NAMES)
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        ax.set_title("MailShield AI - Confusion Matrix")
        for i in range(3):
            for j in range(3):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        fig.colorbar(im)
        fig.tight_layout()
        fig.savefig(REPORTS_DIR / "confusion_matrix.png", dpi=150)
        print(f"Saved confusion matrix image to {REPORTS_DIR / 'confusion_matrix.png'}")
    except ImportError:
        print("matplotlib not available, skipping confusion matrix image.")

    print(json.dumps({
        "accuracy": round(accuracy, 4),
        "macro_f1": round(metrics["macro_f1"], 4),
        "phishing_recall": round(phishing_recall, 4) if phishing_recall is not None else None,
    }, indent=2))
    print(f"Full metrics saved to {REPORTS_DIR / 'evaluation_metrics.json'}")


if __name__ == "__main__":
    main()
