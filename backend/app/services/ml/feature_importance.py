"""
Feature Importance calculations.

Computes SHAP-based or model-based feature importances to explain which factors
contribute most to model predictions.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np

from app.services.ml.ensemble import ModelEnsemble

logger = logging.getLogger(__name__)


def compute_feature_importances(
    ensemble: ModelEnsemble,
    feature_names: List[str]
) -> List[Tuple[str, float]]:
    """
    Extract model-based feature importances from trained tree estimators.
    Returns a sorted list of (feature_name, importance_score).
    """
    if not ensemble._is_trained:
        return []

    importances = np.zeros(len(feature_names))
    count = 0

    # Average feature importances across tree-based models in ensemble
    for name, clf in ensemble._models.items():
        if hasattr(clf, "feature_importances_"):
            importances += clf.feature_importances_
            count += 1

    if count == 0:
        return []

    importances /= count

    # Combine with names and sort
    feat_imp = [
        (name, float(score))
        for name, score in zip(feature_names, importances)
    ]

    return sorted(feat_imp, key=lambda x: x[1], reverse=True)
