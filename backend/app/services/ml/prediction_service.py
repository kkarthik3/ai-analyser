"""
Prediction Service.

Coordinates real-time model inferences using the active ensemble version.
"""

from __future__ import annotations

import logging
from typing import Dict, Any

import pandas as pd

from app.services.ml.model_registry import ModelRegistry
from app.services.ml.ensemble import ModelEnsemble

logger = logging.getLogger(__name__)


class PredictionService:
    """Manages real-time predictive inferences on market features."""

    def __init__(self, registry: ModelRegistry = None) -> None:
        self._registry = registry or ModelRegistry()
        self._model: Optional[ModelEnsemble] = None
        self._load_active_model()

    def _load_active_model(self) -> None:
        """Load the production-active ensemble model version."""
        # For simplicity, we load version '1.0'
        self._model = self._registry.load_model("1.0")
        if not self._model:
            logger.warning("Active model v1.0 not found in registry. Inference disabled.")

    def predict_probability(self, features: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict probability of option gains based on current feature vector.
        """
        if not self._model:
            # Fallback to neutral 50% probability
            return {
                "prob_10pct": 0.5,
                "prob_20pct": 0.5,
                "prob_30pct": 0.5,
                "model_version": "None"
            }

        # Convert dictionary to single-row DataFrame
        df = pd.DataFrame([features])

        pred_10 = self._model.predict_probability(df)

        return {
            "prob_10pct": pred_10["prob"],
            "prob_20pct": pred_10["prob"] * 0.8,  # Approximate scaling
            "prob_30pct": pred_10["prob"] * 0.6,
            "model_version": "1.0",
            "individual_predictions": pred_10.get("individual_predictions", {})
        }
