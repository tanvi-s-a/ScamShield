"""Train and select MailShield's Phase 1–3 phishing model.

Models compared:
* Logistic Regression
* Calibrated Linear SVM
* Random Forest

Selection prioritizes phishing recall, then macro F1.  The saved joblib file
contains both feature preprocessing and the selected classifier.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import MaxAbsScaler
from sklearn.svm import LinearSVC

from app.analyzers.advertisement_analyzer import AD_FEATURE_NAMES
from app.analyzers.link_analyzer import LINK_FEATURE_NAMES
from app.analyzers.sender_analyzer import SENDER_FEATURE_NAMES

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_PROCESSED = BACKEND_DIR / "data" / "processed"
MODELS_DIR = BACKEND_DIR / "models"
REPORTS_DIR = BACKEND_DIR / "reports"
MODEL_PATH = MODELS_DIR / "mailshield_model.joblib"
LEGACY_MODEL_PATH = MODELS_DIR / "mailshield_random_forest.joblib"
NUMERIC_FEATURES = SENDER_FEATURE_NAMES + LINK_FEATURE_NAMES + AD_FEATURE_NAMES
LABEL_NAMES = {0: "Ham", 1: "Phishing", 2: "Spam"}


def build_preprocessor() -> ColumnTransformer:
    text_features = FeatureUnion([
        ("word", TfidfVectorizer(
            lowercase=True, strip_accents="unicode", sublinear_tf=True,
            ngram_range=(1, 2), min_df=1, max_df=0.995, max_features=18000,
        )),
        ("char", TfidfVectorizer(
            analyzer="char_wb", lowercase=True, sublinear_tf=True,
            ngram_range=(3, 5), min_df=2, max_features=12000,
        )),
    ])
    numeric = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", MaxAbsScaler()),
    ])
    return ColumnTransformer([
        ("text", text_features, "combined_text"),
        ("numeric", numeric, NUMERIC_FEATURES),
    ], sparse_threshold=0.3)


def candidates() -> dict[str, object]:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=2500, class_weight="balanced", C=3.0, solver="liblinear", random_state=42,
        ),
        "linear_svm": CalibratedClassifierCV(
            estimator=LinearSVC(class_weight="balanced", C=1.0, random_state=42),
            method="sigmoid", cv=3,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=350, max_depth=None, min_samples_leaf=1,
            class_weight="balanced_subsample", n_jobs=-1, random_state=42,
        ),
    }


def _metrics(y_true, y_pred, labels: list[int]) -> dict:
    report = classification_report(
        y_true, y_pred, labels=labels,
        target_names=[LABEL_NAMES[i] for i in labels], output_dict=True, zero_division=0,
    )
    phishing_recall = recall_score(y_true, y_pred, labels=[1], average="macro", zero_division=0) if 1 in labels else 0.0
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "phishing_recall": float(phishing_recall),
        "classification_report": report,
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }


def main() -> None:
    source = DATA_PROCESSED / "features_table.csv"
    if not source.exists():
        raise SystemExit(f"{source} not found. Run the full training pipeline first.")
    df = pd.read_csv(source)
    df["combined_text"] = df["combined_text"].fillna("")
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)
    labels = sorted(df["label"].unique().tolist())
    if len(labels) < 2:
        raise SystemExit("Training requires at least two classes.")

    X = df[["combined_text"] + NUMERIC_FEATURES]
    y = df["label"]
    counts = y.value_counts()
    stratify = y if counts.min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify,
    )

    results: dict[str, dict] = {}
    fitted: dict[str, Pipeline] = {}
    for name, classifier in candidates().items():
        print(f"Training {name}...")
        pipeline = Pipeline([
            ("preprocess", build_preprocessor()),
            ("classifier", classifier),
        ])
        pipeline.fit(X_train, y_train)
        prediction = pipeline.predict(X_test)
        results[name] = _metrics(y_test, prediction, labels)
        fitted[name] = pipeline
        print(
            f"  phishing recall={results[name]['phishing_recall']:.3f}, "
            f"macro F1={results[name]['macro_f1']:.3f}, "
            f"accuracy={results[name]['accuracy']:.3f}"
        )

    winner = max(results, key=lambda n: (
        results[n]["phishing_recall"], results[n]["macro_f1"], results[n]["accuracy"]
    ))
    selected = fitted[winner]

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected, MODEL_PATH)
    # Keep the old filename too so older backend code remains compatible.
    joblib.dump(selected, LEGACY_MODEL_PATH)

    test_output = X_test.copy()
    test_output["label"] = y_test.values
    test_output.to_csv(DATA_PROCESSED / "test_split.csv", index=False)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "model_version": "1.0.0",
        "selected_model": winner,
        "selection_rule": "highest phishing recall, then macro F1, then accuracy",
        "class_labels": {str(i): LABEL_NAMES[i] for i in labels},
        "feature_count_numeric": len(NUMERIC_FEATURES),
        "n_total": int(len(df)), "n_train": int(len(X_train)), "n_test": int(len(X_test)),
        "results": results,
    }
    (REPORTS_DIR / "model_metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Selected: {winner}")
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
