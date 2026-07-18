"""
Model Registry.

Saves, version-controls, and loads trained machine learning models.
"""

from __future__ import annotations

import os
import logging
import joblib
from typing import Optional

from app.services.ml.ensemble import ModelEnsemble

logger = logging.getLogger(__name__)

MODELS_DIR = "backend/models"


class ModelRegistry:
    """Manages serialization of model ensembled checkpoints."""

    def __init__(self, directory: str = MODELS_DIR) -> None:
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

    def save_model(self, model: ModelEnsemble, version: str) -> str:
        """
        Serialize and save model ensemble to disk.
        """
        path = os.path.join(self.directory, f"ensemble_v{version}.pkl")
        joblib.dump(model, path)
        logger.info(f"Model saved to {path}")
        return path

    def load_model(self, version: str) -> Optional[ModelEnsemble]:
        """
        Deserialize and load model ensemble from disk.
        """
        path = os.path.join(self.directory, f"ensemble_v{version}.pkl")
        if not os.path.exists(path):
            logger.warning(f"No model found at {path}")
            return None

        try:
            model = joblib.load(path)
            logger.info(f"Model loaded from {path}")
            return model
        except Exception as e:
            logger.error(f"Error loading model from {path}: {e}")
            return None
