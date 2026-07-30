"""Run normalization, feature extraction, model comparison, and evaluation."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
TRAINING_DIR = Path(__file__).resolve().parent
for path in (str(BACKEND_DIR), str(TRAINING_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from normalize_datasets import main as normalize
from extract_features import main as extract
from train_model import main as train
from evaluate_model import main as evaluate


def main() -> None:
    print("\n[1/4] Normalizing datasets")
    normalize()
    print("\n[2/4] Extracting sender, URL, and content features")
    extract()
    print("\n[3/4] Comparing and training models")
    train()
    print("\n[4/4] Evaluating selected model")
    evaluate()
    print("\nMailShield model training completed successfully.")


if __name__ == "__main__":
    main()
