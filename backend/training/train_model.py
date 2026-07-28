"""
Trains the final Random Forest pipeline (Section 12-13 of the plan):

    combined_text -> TF-IDF
    sender/link/advertisement numeric features -> passthrough (imputed)
    ColumnTransformer -> RandomForestClassifier

Saves the complete pipeline (including the fitted TF-IDF vectorizer) to
backend/models/mailshield_random_forest.joblib so inference at request
time uses the exact same fitted preprocessing as training.
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.analyzers.sender_analyzer import SENDER_FEATURE_NAMES
from app.analyzers.link_analyzer import LINK_FEATURE_NAMES
from app.analyzers.advertisement_analyzer import AD_FEATURE_NAMES

DATA_PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"

NUMERIC_FEATURES = SENDER_FEATURE_NAMES + LINK_FEATURE_NAMES + AD_FEATURE_NAMES


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(
                lowercase=True, stop_words="english", max_features=5000,
                ngram_range=(1, 2), min_df=2, max_df=0.98, sublinear_tf=True,
            ), "combined_text"),
            ("numeric", SimpleImputer(strategy="median"), NUMERIC_FEATURES),
        ],
    )

    model = RandomForestClassifier(
        n_estimators=250, max_depth=40, min_samples_split=5,
        min_samples_leaf=2, class_weight="balanced", n_jobs=-1, random_state=42,
    )

    return Pipeline([("preprocess", preprocessor), ("classifier", model)])


def main():
    in_path = DATA_PROCESSED / "features_table.csv"
    if not in_path.exists():
        raise SystemExit(f"{in_path} not found. Run extract_features.py first.")

    df = pd.read_csv(in_path)
    df["combined_text"] = df["combined_text"].fillna("")
    df = df.dropna(subset=["label"])
    df["label"] = df["label"].astype(int)

    X = df[["combined_text"] + NUMERIC_FEATURES]
    y = df["label"]

    # Guard against classes too small to stratify (common with tiny synthetic-only runs)
    class_counts = y.value_counts()
    stratify = y if class_counts.min() >= 2 else None

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=stratify
    )
    strat_temp = y_temp if (stratify is not None and y_temp.value_counts().min() >= 2) else None
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=strat_temp
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "mailshield_random_forest.joblib"
    joblib.dump(pipeline, model_path)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    info = {
        "model_version": "0.1.0",
        "n_train": len(X_train), "n_val": len(X_val), "n_test": len(X_test),
        "feature_count_numeric": len(NUMERIC_FEATURES),
        "class_labels": {"0": "Ham", "1": "Phishing", "2": "Spam"},
    }
    with open(REPORTS_DIR / "model_metrics.json", "w") as f:
        json.dump(info, f, indent=2)

    # Persist the split so evaluate_model.py scores on the exact same test set.
    X_test_out = X_test.copy()
    X_test_out["label"] = y_test.values
    X_test_out.to_csv(DATA_PROCESSED / "test_split.csv", index=False)

    print(f"Saved trained pipeline to {model_path}")
    print(f"Train/val/test sizes: {len(X_train)}/{len(X_val)}/{len(X_test)}")


if __name__ == "__main__":
    main()
