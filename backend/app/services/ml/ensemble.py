"""
ML Model Ensemble.

Wraps, trains, and stacks multiple classifier types:
Logistic Regression, Random Forest, XGBoost, LightGBM, and CatBoost.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List

import numpy as np
import pandas as pd

# Scikit-learn & Gradient Boosting packages
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier

logger = logging.getLogger(__name__)


class ModelEnsemble:
    """Ensemble stacking Logistic Regression, Random Forest, and Gradient Boosted trees."""

    def __init__(self) -> None:
        # Initialize estimators
        self._models = {
            "logistic": LogisticRegression(max_iter=1000, C=0.1),
            "random_forest": RandomForestClassifier(n_estimators=100, max_depth=10, n_jobs=-1),
            "xgboost": XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, eval_metric="logloss"),
            "lightgbm": LGBMClassifier(n_estimators=100, max_depth=5, learning_rate=0.05, verbose=-1),
            "catboost": CatBoostClassifier(iterations=100, depth=5, learning_rate=0.05, verbose=0)
        }
        self._is_trained = False

    def train(self, X: pd.DataFrame, y: pd.Series) -> None:
        """
        Train all models on the provided training set.
        """
        logger.info(f"Training ModelEnsemble with {len(X)} samples and {len(X.columns)} features.")

        # Clean features to numeric only (drop non-numeric columns if any)
        X_clean = X.select_dtypes(include=[np.number])

        for name, clf in self._models.items():
            try:
                logger.info(f"Fitting model: {name}")
                clf.fit(X_clean, y)
            except Exception as e:
                logger.error(f"Failed to fit model {name}: {e}")

        self._is_trained = True

    def predict_probability(self, X: pd.DataFrame) -> Dict[str, float]:
        """
        Return the average/ensemble probability score of positive targets.
        """
        if not self._is_trained:
            return {"prob": 0.5}

        X_clean = X.select_dtypes(include=[np.number])
        probs = []

        for name, clf in self._models.items():
            try:
                # Predict probability of class 1 (gain event)
                p = clf.predict_proba(X_clean)[0][1]
                probs.append(p)
            except Exception as e:
                logger.error(f"Failed prediction for {name}: {e}")

        if not probs:
            return {"prob": 0.5}

        # Ensemble average
        mean_prob = float(np.mean(probs))

        return {
            "prob": mean_prob,
            "individual_predictions": {
                name: float(p)
                for name, p in zip(self._models.keys(), probs)
            }
        }
