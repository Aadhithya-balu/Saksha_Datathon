"""
SAKSHA – District Risk & Forecast Feature Engineering

Produces two feature sets from raw crime records:
  1. RiskFeatures  – district-level aggregated features for risk scoring
  2. ForecastFeatures – monthly time-series features per district for forecasting
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required input columns (subset of CaseMaster / crime_cases join)
# ---------------------------------------------------------------------------

REQUIRED_INPUT_COLUMNS: List[str] = [
    "occurred_at",
    "district",
    "category",
]

# ---------------------------------------------------------------------------
# Feature column lists (single source of truth)
# ---------------------------------------------------------------------------

RISK_FEATURE_COLUMNS: List[str] = [
    "crime_count",
    "night_crime_ratio",
    "weekend_crime_ratio",
    "unique_categories",
    "month_sin",
    "month_cos",
    "lag_1",
    "lag_3",
    "rolling_mean_3",
    "rolling_std_3",
    "yoy_growth",
]

FORECAST_FEATURE_COLUMNS: List[str] = [
    "crime_count",
    "month_sin",
    "month_cos",
    "quarter",
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_6",
    "rolling_mean_3",
    "rolling_mean_6",
    "rolling_std_3",
    "ema_3",
    "growth_rate",
    "momentum",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("Input dataframe is empty.")
    missing = [c for c in REQUIRED_INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = df.copy()
    df["occurred_at"] = pd.to_datetime(df["occurred_at"], errors="coerce")
    df = df.dropna(subset=["occurred_at", "district"])
    if df.empty:
        raise ValueError("No valid rows after cleaning.")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Monthly aggregation per district
# ---------------------------------------------------------------------------

def _aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year"] = df["occurred_at"].dt.year
    df["month"] = df["occurred_at"].dt.month
    df["year_month"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    df["is_night"] = df["occurred_at"].dt.hour.between(20, 23) | df["occurred_at"].dt.hour.between(0, 5)
    df["is_weekend"] = df["occurred_at"].dt.weekday.isin([5, 6])

    monthly = (
        df.groupby(["district", "year_month"])
        .agg(
            crime_count=("occurred_at", "count"),
            night_crimes=("is_night", "sum"),
            weekend_crimes=("is_weekend", "sum"),
            unique_categories=("category", "nunique"),
            year=("year", "first"),
            month=("month", "first"),
        )
        .reset_index()
        .sort_values(["district", "year_month"])
        .reset_index(drop=True)
    )

    monthly["night_crime_ratio"] = monthly["night_crimes"] / monthly["crime_count"].clip(lower=1)
    monthly["weekend_crime_ratio"] = monthly["weekend_crimes"] / monthly["crime_count"].clip(lower=1)
    monthly["month_sin"] = np.sin(2 * np.pi * monthly["month"] / 12)
    monthly["month_cos"] = np.cos(2 * np.pi * monthly["month"] / 12)
    monthly["quarter"] = ((monthly["month"] - 1) // 3) + 1

    return monthly


# ---------------------------------------------------------------------------
# Lag / rolling features (shared)
# ---------------------------------------------------------------------------

def _add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().sort_values(["district", "year", "month"]).reset_index(drop=True)
    grp = df.groupby("district")["crime_count"]

    for lag in [1, 2, 3, 6]:
        df[f"lag_{lag}"] = grp.shift(lag)

    df["rolling_mean_3"] = grp.transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    df["rolling_mean_6"] = grp.transform(lambda x: x.shift(1).rolling(6, min_periods=1).mean())
    df["rolling_std_3"] = grp.transform(lambda x: x.shift(1).rolling(3, min_periods=2).std())
    df["ema_3"] = grp.transform(lambda x: x.shift(1).ewm(span=3).mean())
    df["growth_rate"] = df["lag_1"] - df["lag_2"]
    df["momentum"] = df["rolling_mean_3"] - df["lag_1"]

    # Year-over-year growth (lag 12 months)
    df["lag_12"] = grp.shift(12)
    df["yoy_growth"] = (df["crime_count"] - df["lag_12"]) / (df["lag_12"].clip(lower=1))

    df.fillna(0, inplace=True)
    return df


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_risk_features(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """Build district-level risk features.

    Returns DataFrame with columns: district, year_month + RISK_FEATURE_COLUMNS
    + optionally TargetRiskScore (next-month crime count, used as regression target).
    """
    df = _validate(df)
    monthly = _aggregate_monthly(df)
    monthly = _add_lag_features(monthly)

    monthly["TargetRiskScore"] = monthly.groupby("district")["crime_count"].shift(-1)
    if include_target:
        monthly = monthly.dropna(subset=["TargetRiskScore"]).reset_index(drop=True)
    else:
        monthly["TargetRiskScore"] = monthly["TargetRiskScore"].fillna(0)

    monthly.fillna(0, inplace=True)

    out_cols = ["district", "year_month"] + RISK_FEATURE_COLUMNS
    if include_target:
        out_cols = ["district", "year_month", "TargetRiskScore"] + RISK_FEATURE_COLUMNS

    missing = [c for c in RISK_FEATURE_COLUMNS if c not in monthly.columns]
    if missing:
        raise RuntimeError(f"Risk feature engineering missing columns: {missing}")

    logger.info("build_risk_features: %d rows, %d districts.", len(monthly), monthly["district"].nunique())
    return monthly[out_cols]


def build_forecast_features(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """Build monthly time-series features for crime count forecasting.

    Returns DataFrame with columns: district, year_month + FORECAST_FEATURE_COLUMNS
    + optionally TargetCrimeCount.
    """
    df = _validate(df)
    monthly = _aggregate_monthly(df)
    monthly = _add_lag_features(monthly)

    monthly["TargetCrimeCount"] = monthly.groupby("district")["crime_count"].shift(-1)
    if include_target:
        monthly = monthly.dropna(subset=["TargetCrimeCount"]).reset_index(drop=True)
    else:
        monthly["TargetCrimeCount"] = monthly["TargetCrimeCount"].fillna(0)

    monthly.fillna(0, inplace=True)

    out_cols = ["district", "year_month"] + FORECAST_FEATURE_COLUMNS
    if include_target:
        out_cols = ["district", "year_month", "TargetCrimeCount"] + FORECAST_FEATURE_COLUMNS

    missing = [c for c in FORECAST_FEATURE_COLUMNS if c not in monthly.columns]
    if missing:
        raise RuntimeError(f"Forecast feature engineering missing columns: {missing}")

    logger.info("build_forecast_features: %d rows, %d districts.", len(monthly), monthly["district"].nunique())
    return monthly[out_cols]
