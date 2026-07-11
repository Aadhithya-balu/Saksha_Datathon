"""
SAKSHA – Crime Hotspot Prediction
Production Feature Engineering Module

Reproduces EXACTLY the transformations from the Colab training notebook so that
inference features are identical to training features.

Output feature order matches feature_columns.json (31 features):
    CrimeCount, NightCrime, WeekendCrime, AvgHour, UniqueStations,
    MajorCrimeTypes, GravityMean, Year, Month, Quarter, MonthSin, MonthCos,
    Lag_1, Lag_2, Lag_3, Lag_6, RollingMean3, RollingMean6, RollingStd3,
    RollingStd6, RollingMax6, RollingMin6, EMA3, EMA6,
    GrowthRate, Momentum, Acceleration,
    NeighborCrimeCount, NeighborDensity, LocalDensityRatio,
    StationCrimeIntensity
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np
import pandas as pd

try:
    import h3
except ImportError as exc:  # pragma: no cover
    raise ImportError("h3 is required: pip install h3") from exc

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (must match training notebook)
# ---------------------------------------------------------------------------

H3_RESOLUTION: int = 7

REQUIRED_INPUT_COLUMNS: List[str] = [
    "CaseMasterID",
    "IncidentFromDate",
    "latitude",
    "longitude",
    "PoliceStationID",
    "GravityOffenceID",
    "CrimeMajorHeadID",
]

FEATURE_COLUMNS: List[str] = [
    "CrimeCount", "NightCrime", "WeekendCrime", "AvgHour",
    "UniqueStations", "MajorCrimeTypes", "GravityMean",
    "Year", "Month", "Quarter", "MonthSin", "MonthCos",
    "Lag_1", "Lag_2", "Lag_3", "Lag_6",
    "RollingMean3", "RollingMean6", "RollingStd3", "RollingStd6",
    "RollingMax6", "RollingMin6", "EMA3", "EMA6",
    "GrowthRate", "Momentum", "Acceleration",
    "NeighborCrimeCount", "NeighborDensity", "LocalDensityRatio",
    "StationCrimeIntensity",
]


# ---------------------------------------------------------------------------
# 1. Validation
# ---------------------------------------------------------------------------

def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Validate input dataframe and return a clean working copy.

    Raises
    ------
    ValueError
        If required columns are missing or the dataframe is empty.
    """
    if df is None or df.empty:
        raise ValueError("Input dataframe is empty.")

    missing = [c for c in REQUIRED_INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df["IncidentFromDate"] = pd.to_datetime(df["IncidentFromDate"], errors="coerce")

    invalid_dates = df["IncidentFromDate"].isna().sum()
    if invalid_dates:
        logger.warning("Dropping %d rows with unparseable IncidentFromDate.", invalid_dates)
        df = df.dropna(subset=["IncidentFromDate"])

    invalid_coords = df["latitude"].isna() | df["longitude"].isna()
    if invalid_coords.any():
        logger.warning("Dropping %d rows with missing coordinates.", invalid_coords.sum())
        df = df[~invalid_coords]

    if df.empty:
        raise ValueError("No valid rows remain after cleaning.")

    logger.info("validate_dataframe: %d valid rows.", len(df))
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. H3 Cells
# ---------------------------------------------------------------------------

def create_h3_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Assign H3 cell index (resolution 7) to every crime record."""
    df = df.copy()
    df["H3Cell"] = [
        h3.latlng_to_cell(lat, lon, H3_RESOLUTION)
        for lat, lon in zip(df["latitude"], df["longitude"])
    ]
    logger.info("create_h3_cells: %d unique H3 cells.", df["H3Cell"].nunique())
    return df


# ---------------------------------------------------------------------------
# 3. Monthly Aggregation
# ---------------------------------------------------------------------------

def _add_time_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add IsNight and IsWeekend flags needed for aggregation."""
    df = df.copy()
    hour = df["IncidentFromDate"].dt.hour
    weekday = df["IncidentFromDate"].dt.weekday
    df["IsNight"] = ((hour >= 20) | (hour <= 5)).astype(int)
    df["IsWeekend"] = weekday.isin([5, 6]).astype(int)
    df["Hour"] = hour
    return df


def aggregate_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate crime records to monthly H3-cell level.

    Returns a dataframe with one row per (H3Cell, YearMonth) and the
    aggregated columns used as model features.
    """
    df = df.copy()
    df["Year"] = df["IncidentFromDate"].dt.year
    df["Month"] = df["IncidentFromDate"].dt.month
    df["YearMonth"] = (
        df["Year"].astype(str) + "-" + df["Month"].astype(str).str.zfill(2)
    )
    df = _add_time_flags(df)

    monthly = (
        df.groupby(["H3Cell", "YearMonth"])
        .agg(
            CrimeCount=("CaseMasterID", "count"),
            NightCrime=("IsNight", "sum"),
            WeekendCrime=("IsWeekend", "sum"),
            AvgHour=("Hour", "mean"),
            UniqueStations=("PoliceStationID", "nunique"),
            MajorCrimeTypes=("CrimeMajorHeadID", "nunique"),
            GravityMean=("GravityOffenceID", "mean"),
        )
        .reset_index()
        .sort_values(["H3Cell", "YearMonth"])
        .reset_index(drop=True)
    )

    logger.info(
        "aggregate_monthly: %d rows, %d unique cells.",
        len(monthly), monthly["H3Cell"].nunique(),
    )
    return monthly


# ---------------------------------------------------------------------------
# 4. Temporal Features
# ---------------------------------------------------------------------------

def create_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add Year, Month, Quarter, MonthSin, MonthCos from YearMonth column."""
    df = df.copy()
    dt = pd.to_datetime(df["YearMonth"])
    df["Year"] = dt.dt.year
    df["Month"] = dt.dt.month
    df["Quarter"] = ((df["Month"] - 1) // 3) + 1
    df["MonthSin"] = np.sin(2 * np.pi * df["Month"] / 12)
    df["MonthCos"] = np.cos(2 * np.pi * df["Month"] / 12)
    return df


# ---------------------------------------------------------------------------
# 5. Historical / Lag Features
# ---------------------------------------------------------------------------

def create_historical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag, rolling, EMA, growth-rate, momentum, and acceleration features.

    The dataframe must already be sorted by (H3Cell, Year, Month).
    All features are computed on CrimeCount grouped by H3Cell, shifted by 1
    to avoid data leakage (identical to the notebook).
    """
    df = df.copy().sort_values(["H3Cell", "Year", "Month"]).reset_index(drop=True)

    grp = df.groupby("H3Cell")["CrimeCount"]

    # Lags
    for lag in [1, 2, 3, 6]:
        df[f"Lag_{lag}"] = grp.shift(lag)

    # Rolling statistics (shift(1) inside transform to avoid leakage)
    df["RollingMean3"] = grp.transform(lambda x: x.shift(1).rolling(3, min_periods=1).mean())
    df["RollingMean6"] = grp.transform(lambda x: x.shift(1).rolling(6, min_periods=1).mean())
    df["RollingStd3"]  = grp.transform(lambda x: x.shift(1).rolling(3, min_periods=2).std())
    df["RollingStd6"]  = grp.transform(lambda x: x.shift(1).rolling(6, min_periods=2).std())
    df["RollingMax6"]  = grp.transform(lambda x: x.shift(1).rolling(6, min_periods=1).max())
    df["RollingMin6"]  = grp.transform(lambda x: x.shift(1).rolling(6, min_periods=1).min())

    # Exponential moving averages
    df["EMA3"] = grp.transform(lambda x: x.shift(1).ewm(span=3).mean())
    df["EMA6"] = grp.transform(lambda x: x.shift(1).ewm(span=6).mean())

    # Derived momentum features
    df["GrowthRate"]   = df["Lag_1"] - df["Lag_2"]
    df["Momentum"]     = df["RollingMean3"] - df["Lag_1"]
    df["Acceleration"] = df["GrowthRate"] - df.groupby("H3Cell")["GrowthRate"].shift(1)

    df.fillna(0, inplace=True)
    return df


# ---------------------------------------------------------------------------
# 6. Neighbor Features
# ---------------------------------------------------------------------------

def create_neighbor_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add NeighborCrimeCount, NeighborDensity, and LocalDensityRatio.

    Uses H3 grid_disk(cell, 1) to find the 6 immediate neighbors and looks up
    their CrimeCount for the same YearMonth (identical to the notebook).
    """
    df = df.copy()

    # Build neighbor map once
    unique_cells = df["H3Cell"].unique()
    neighbor_map: dict[str, list[str]] = {}
    for cell in unique_cells:
        try:
            neighbors = list(h3.grid_disk(cell, 1))
            neighbors.remove(cell)
            neighbor_map[cell] = neighbors
        except Exception:
            neighbor_map[cell] = []

    # Build (cell, yearmonth) → CrimeCount lookup
    crime_lookup: dict[tuple[str, str], float] = {
        (row["H3Cell"], row["YearMonth"]): row["CrimeCount"]
        for _, row in df.iterrows()
    }

    neighbor_counts = [
        sum(crime_lookup.get((n, row["YearMonth"]), 0) for n in neighbor_map[row["H3Cell"]])
        for _, row in df.iterrows()
    ]

    df["NeighborCrimeCount"] = neighbor_counts
    df["NeighborDensity"]    = df["NeighborCrimeCount"] / 6.0
    df["LocalDensityRatio"]  = df["CrimeCount"] / (df["NeighborCrimeCount"] + 1)

    logger.info("create_neighbor_features: done.")
    return df


# ---------------------------------------------------------------------------
# 7. Station Features
# ---------------------------------------------------------------------------

def create_station_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add StationCrimeIntensity = CrimeCount / UniqueStations (clipped ≥ 1)."""
    df = df.copy()
    df["StationCrimeIntensity"] = df["CrimeCount"] / df["UniqueStations"].clip(lower=1)
    return df


# ---------------------------------------------------------------------------
# 8. Master Pipeline
# ---------------------------------------------------------------------------

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """End-to-end feature engineering pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        Raw crime records (see REQUIRED_INPUT_COLUMNS).

    Returns
    -------
    pd.DataFrame
        Monthly H3-cell dataframe with all 31 model features plus
        H3Cell and YearMonth identifier columns.
        Feature columns are in the same order as FEATURE_COLUMNS /
        feature_columns.json.
    """
    logger.info("build_features: starting pipeline.")

    df = validate_dataframe(df)
    df = create_h3_cells(df)
    monthly = aggregate_monthly(df)
    monthly = create_temporal_features(monthly)
    monthly = create_historical_features(monthly)
    monthly = create_neighbor_features(monthly)
    monthly = create_station_features(monthly)

    # Target: next-month crime count per H3 cell (matches training notebook exactly)
    monthly["TargetCrimeCount"] = (
        monthly.groupby("H3Cell")["CrimeCount"].shift(-1)
    )
    monthly = monthly.dropna(subset=["TargetCrimeCount"]).reset_index(drop=True)

    monthly.fillna(0, inplace=True)

    # Ensure feature column order matches training
    output_cols = ["H3Cell", "YearMonth", "TargetCrimeCount"] + FEATURE_COLUMNS
    missing_feat = [c for c in FEATURE_COLUMNS if c not in monthly.columns]
    if missing_feat:
        raise RuntimeError(f"Feature engineering produced missing columns: {missing_feat}")

    logger.info(
        "build_features: complete. Shape=%s, features=%d.",
        monthly.shape, len(FEATURE_COLUMNS),
    )
    return monthly[output_cols]
