"""
OI Heatmap data generation and matrix formatting.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

import pandas as pd

from app.db.models.option_chain import OptionChainSnapshot

logger = logging.getLogger(__name__)


def generate_oi_heatmap_matrix(
    snapshots: Sequence[OptionChainSnapshot],
    value_field: str = "oi"
) -> Dict[str, Any]:
    """
    Format historical option chain snapshots into a strike-vs-time matrix for heatmaps.
    """
    if not snapshots:
        return {"timestamps": [], "strikes": [], "matrix": []}

    # Convert to DataFrame
    data = []
    for s in snapshots:
        data.append({
            "time": s.time.isoformat(),
            "strike": s.strike,
            "option_type": s.option_type,
            "value": getattr(s, value_field, 0.0) or 0.0
        })

    df = pd.DataFrame(data)

    # Pivot table: Index = strike, Columns = time, Values = sum of value_field
    pivot = df.pivot_table(
        index="strike",
        columns="time",
        values="value",
        aggfunc="sum"
    ).fillna(0.0)

    return {
        "timestamps": list(pivot.columns),
        "strikes": [float(x) for x in pivot.index],
        "matrix": pivot.values.tolist()
    }
