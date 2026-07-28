import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException

from app.schemas.request_models import AnalyzeRequest, AnalyzeResponse
from app.analyzers.sender_analyzer import analyze_sender, SENDER_FEATURE_NAMES
from app.analyzers.link_analyzer import analyze_links, LINK_FEATURE_NAMES
from app.analyzers.advertisement_analyzer import analyze_advertisement, AD_FEATURE_NAMES
from app.security.risk_engine import compute_risk, recommend_blocking_actions
from app.utils.constants import INVERSE_LABEL_MAP

router = APIRouter()

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
MODEL_PATH = MODELS_DIR / "mailshield_random_forest.joblib"

NUMERIC_FEATURES = SENDER_FEATURE_NAMES + LINK_FEATURE_NAMES + AD_FEATURE_NAMES

_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None and MODEL_PATH.exists():
        _pipeline = joblib.load(MODEL_PATH)
    return _pipeline


@router.get("/health")
def health():
    return {"status": "healthy", "model_loaded": get_pipeline() is not None}


@router.get("/model-info")
def model_info():
    info_path = REPORTS_DIR / "model_metrics.json"
    eval_path = REPORTS_DIR / "evaluation_metrics.json"
    info = json.loads(info_path.read_text()) if info_path.exists() else {}
    eval_summary = json.loads(eval_path.read_text()) if eval_path.exists() else None
    return {
        "model_version": info.get("model_version", "unknown"),
        "class_labels": info.get("class_labels", {"0": "Ham", "1": "Phishing", "2": "Spam"}),
        "feature_count_numeric": info.get("feature_count_numeric", len(NUMERIC_FEATURES)),
        "evaluation_summary": eval_summary,
        "model_loaded": get_pipeline() is not None,
    }


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    pipeline = get_pipeline()
    if pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Run the training pipeline first "
                   "(generate_synthetic_ads.py -> normalize_datasets.py -> "
                   "extract_features.py -> train_model.py).",
        )

    sender_features = analyze_sender(
        from_address=request.from_address,
        reply_to_address=request.reply_to_address,
        return_path=request.return_path,
        message_id=request.message_id,
        auth_results=request.auth_results.model_dump() if request.auth_results else {},
    )
    link_features = analyze_links([l.model_dump() for l in request.links])
    ad_features = analyze_advertisement(
        text=f"{request.subject} {request.body}",
        html_content=request.html_content,
        images=[i.model_dump() for i in request.images],
        buttons=[b.model_dump() for b in request.buttons],
        forms_present=request.forms_present,
    )

    combined_text = f"{request.subject} {request.body}"
    row = {"combined_text": combined_text, **sender_features, **link_features, **ad_features}
    X = pd.DataFrame([row])[["combined_text"] + NUMERIC_FEATURES]

    proba = pipeline.predict_proba(X)[0]
    class_order = pipeline.classes_  # e.g. array([0, 1, 2])
    proba_by_label = {INVERSE_LABEL_MAP[int(c)].lower(): float(p) for c, p in zip(class_order, proba)}

    predicted_class = int(class_order[proba.argmax()])
    classification = INVERSE_LABEL_MAP[predicted_class]
    confidence = float(proba.max())

    risk = compute_risk(proba_by_label, sender_features, link_features, ad_features)
    blocking_actions = recommend_blocking_actions(risk["risk_level"], ad_features)

    return AnalyzeResponse(
        classification=classification,
        confidence=confidence,
        probabilities=proba_by_label,
        risk_score=risk["risk_score"],
        risk_level=risk["risk_level"],
        findings=risk["findings"],
        blocking_actions=blocking_actions,
    )
