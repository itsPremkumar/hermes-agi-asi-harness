"""Data profiling — automated statistics generation."""
from __future__ import annotations

import pandas as pd

from qualitywatch.models import QualityProfile


def profile(df: pd.DataFrame, name: str = "dataset") -> QualityProfile:
    """Generate a full statistical profile for a DataFrame."""
    profile = QualityProfile(dataset_name=name, row_count=len(df), column_count=len(df.columns))

    for col in df.columns:
        profile.null_counts[col] = int(df[col].isna().sum())
        n_unique = df[col].nunique()
        profile.uniqueness[col] = round(n_unique / len(df), 4) if len(df) else 0.0

        if pd.api.types.is_numeric_dtype(df[col]):
            stats = df[col].describe()
            profile.stats[col] = {
                "mean": round(float(stats.get("mean", 0)), 4),
                "std": round(float(stats.get("std", 0)), 4),
                "min": round(float(stats.get("min", 0)), 4),
                "max": round(float(stats.get("max", 0)), 4),
                "median": round(float(df[col].median()), 4),
                "missing_pct": round(profile.null_counts[col] / len(df) * 100, 2),
            }
        else:
            profile.stats[col] = {
                "dtype": str(df[col].dtype),
                "top": str(df[col].mode().iloc[0]) if not df[col].mode().empty else None,
                "freq": int(df[col].value_counts().iloc[0]) if not df[col].value_counts().empty else 0,
                "missing_pct": round(profile.null_counts[col] / len(df) * 100, 2),
            }

    return profile