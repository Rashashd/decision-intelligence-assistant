import logging
import time
from functools import lru_cache

import joblib
import numpy as np
from fastapi import HTTPException
from scipy.sparse import csr_matrix, hstack

from app.config import get_settings
from app.schemas import PriorityPrediction
from app.utils.feature_extractor import ENGINEERED_COLS, extract_features

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_artifact() -> dict:
    path = get_settings().model_path
    logger.info("Loading ML artifact from %s", path)
    try:
        artifact = joblib.load(path)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail=f"ML model not found at '{path}'. Run the notebook to generate it.")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Failed to load ML model artifact") from exc
    logger.info(
        "Artifact loaded: %s on %s features (val F1=%.3f)",
        artifact["model_family"],
        artifact["feature_config"],
        artifact["val_f1"],
    )
    return artifact


def predict_priority(text: str) -> PriorityPrediction:
    # Run the full inference pipeline and return label, confidence, latency, and cost.

    # Returns a dict matching the PriorityPrediction schema
    # Cost is always 0.0 because it is a local model
    
    t0 = time.perf_counter()

    artifact = _load_artifact()

    # 1. Numeric features → impute → scale
    num_arr = extract_features(text)
    num_arr = artifact["imputer"].transform(num_arr)
    num_arr = artifact["scaler"].transform(num_arr)

    # 2. Brand one-hot encoding → toarray() for stacking with sparse tf-idf
    brand_arr = artifact["brand_encoder"].transform([["unknown"]])

    # 3. TF-IDF on raw text
    tfidf_arr = artifact["vectorizer"].transform([text])

    # 4. Stack: engineered (dense) + tfidf (sparse) → toarray() for HistGBM
    engineered_sparse = csr_matrix(np.hstack([num_arr, brand_arr]))
    combined = hstack([engineered_sparse, tfidf_arr]).toarray()

    # 5. Predict
    pred = artifact["model"].predict(combined)[0]
    proba = artifact["model"].predict_proba(combined)[0]

    latency_ms = (time.perf_counter() - t0) * 1000

    return PriorityPrediction(
        label="urgent" if pred == 1 else "normal",
        confidence=round(float(max(proba)), 4),
        latency_ms=round(latency_ms, 2),
        cost_usd=0.0,
    )