"""
SAKSHA – Crime Hotspot Prediction
Production Feature Engineering Module

Reproduces EXACTLY the transformations from the Colab training notebook so that
inference features are identical to training features.

Output feature order matches feature_columns.json. Legacy artifact set (31):
    CrimeCount, NightCrime, WeekendCrime, AvgHour, UniqueStations,
    MajorCrimeTypes, GravityMean, Year, Month, Quarter, MonthSin, MonthCos,
    Lag_1, Lag_2, Lag_3, Lag_6, RollingMean3, RollingMean6, RollingStd3,
    RollingStd6, RollingMax6, RollingMin6, EMA3, EMA6,
    GrowthRate, Momentum, Acceleration,
    NeighborCrimeCount, NeighborDensity, LocalDensityRatio,
    StationCrimeIntensity

Temporal extension (issue #143 gap 131.2, appended after the legacy set):
    EveningCrime, AfternoonCrime, LateNightCrime, MorningCrime,
    HolidayCrime, HourSin, HourCos, DowSin, DowCos

Older trained artifacts subset by their stored feature_columns.json, so the
extra columns are simply ignored until the next full retraining.
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

LEGACY_FEATURE_COLUMNS: List[str] = [
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

TEMPORAL_FEATURE_COLUMNS: List[str] = [
    "EveningCrime", "AfternoonCrime", "LateNightCrime", "MorningCrime",
    "HolidayCrime", "HourSin", "HourCos", "DowSin", "DowCos",
]

FEATURE_COLUMNS: List[str] = LEGACY_FEATURE_COLUMNS + TEMPORAL_FEATURE_COLUMNS


# ---------------------------------------------------------------------------
# Holiday calendar (issue #143 gap 131.2)
# ---------------------------------------------------------------------------

# Fixed-date Karnataka / national public holidays as (month, day).
# Lunar-calendar festivals (Ugadi, Diwali, Ganesh Chaturthi, Eid...) shift
# every year and are intentionally excluded to stay deterministic.
KARNATAKA_FIXED_HOLIDAYS: set[tuple[int, int]] = {
    (1, 1),    # New Year's Day
    (1, 26),   # Republic Day
    (5, 1),    # Labour Day / May Day
    (8, 15),   # Independence Day
    (10, 2),   # Gandhi Jayanti
    (11, 1),   # Karnataka Rajyotsava
    (12, 25),  # Christmas
}


def is_karnataka_holiday(ts: pd.Timestamp) -> bool:
    """True when the timestamp falls on a fixed-date Karnataka/national holiday."""
    return (ts.month, ts.day) in KARNATAKA_FIXED_HOLIDAYS


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

    # GravityOffenceID feeds the GravityMean aggregate; API callers may send
    # string IDs ("G-1") instead of numeric CCTNS gravity codes — coerce to
    # numeric (NaN for purely categorical IDs) so mean() never crashes (#146).
    df["GravityOffenceID"] = pd.to_numeric(df["GravityOffenceID"], errors="coerce")

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


def _latlng_to_cell(lat: float, lon: float, res: int) -> str:
    if hasattr(h3, "latlng_to_cell"):
        return h3.latlng_to_cell(lat, lon, res)
    if hasattr(h3, "geo_to_h3"):
        return h3.geo_to_h3(lat, lon, res)
    return f"cell_{round(lat, 3)}_{round(lon, 3)}"


def _grid_disk(cell: str, k: int = 1) -> list[str]:
    if hasattr(h3, "grid_disk"):
        return list(h3.grid_disk(cell, k))
    if hasattr(h3, "k_ring"):
        return list(h3.k_ring(cell, k))
    return []


# ---------------------------------------------------------------------------
# 2. H3 Cells
# ---------------------------------------------------------------------------

def _latlng_to_cell(lat: float, lon: float, res: int) -> str:
    """Compatibility helper across h3-py v3 and v4."""
    if hasattr(h3, "latlng_to_cell"):
        return h3.latlng_to_cell(lat, lon, res)
    elif hasattr(h3, "geo_to_h3"):
        return h3.geo_to_h3(lat, lon, res)
    return f"cell_{round(lat, 4)}_{round(lon, 4)}_{res}"


def _grid_disk(cell: str, k: int) -> list[str]:
    """Compatibility helper across h3-py v3 and v4."""
    if hasattr(h3, "grid_disk"):
        return list(h3.grid_disk(cell, k))
    elif hasattr(h3, "k_ring"):
        return list(h3.k_ring(cell, k))
    return [cell]


def create_h3_cells(df: pd.DataFrame) -> pd.DataFrame:
    """Assign H3 cell index (resolution 7) to every crime record."""
    df = df.copy()
    df["H3Cell"] = [
        _latlng_to_cell(lat, lon, H3_RESOLUTION)
        for lat, lon in zip(df["latitude"], df["longitude"])
    ]
    logger.info("create_h3_cells: %d unique H3 cells.", df["H3Cell"].nunique())
    return df


# ---------------------------------------------------------------------------
# 3. Monthly Aggregation
# ---------------------------------------------------------------------------

def _add_time_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add night/weekend flags, hour bins, holiday flag, and cyclical
    hour/day-of-week encodings needed for aggregation (issue #143 gap 131.2)."""
    df = df.copy()
    hour = df["IncidentFromDate"].dt.hour
    weekday = df["IncidentFromDate"].dt.weekday
    df["IsNight"] = ((hour >= 20) | (hour <= 5)).astype(int)
    df["IsWeekend"] = weekday.isin([5, 6]).astype(int)
    df["Hour"] = hour

    # Hour-of-day bins (4 x 6-hour blocks)
    df["IsLateNight"] = hour.between(0, 5).astype(int)
    df["IsMorning"] = hour.between(6, 11).astype(int)
    df["IsAfternoon"] = hour.between(12, 17).astype(int)
    df["IsEvening"] = hour.between(18, 23).astype(int)

    # Fixed-date Karnataka/national holiday calendar
    df["IsHoliday"] = df["IncidentFromDate"].map(is_karnataka_holiday).astype(int)

    # Cyclical encodings for circular means over the aggregation window
    df["HourSinRaw"] = np.sin(2 * np.pi * hour / 24.0)
    df["HourCosRaw"] = np.cos(2 * np.pi * hour / 24.0)
    df["DowSinRaw"] = np.sin(2 * np.pi * weekday / 7.0)
    df["DowCosRaw"] = np.cos(2 * np.pi * weekday / 7.0)
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
            # Temporal hotspot features (issue #143 gap 131.2)
            EveningCrime=("IsEvening", "sum"),
            AfternoonCrime=("IsAfternoon", "sum"),
            LateNightCrime=("IsLateNight", "sum"),
            MorningCrime=("IsMorning", "sum"),
            HolidayCrime=("IsHoliday", "sum"),
            HourSin=("HourSinRaw", "mean"),
            HourCos=("HourCosRaw", "mean"),
            DowSin=("DowSinRaw", "mean"),
            DowCos=("DowCosRaw", "mean"),
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
            neighbors = list(_grid_disk(cell, 1))
            neighbors = _grid_disk(cell, 1)
            if cell in neighbors:
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

def build_features(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """End-to-end feature engineering pipeline.

    Parameters
    ----------
    df : pd.DataFrame
        Raw crime records (see REQUIRED_INPUT_COLUMNS).
    include_target : bool
        When True (default), include the training target column and drop rows
        that have no next-month target. When False, keep all engineered rows so
        inference can score fresh input even with a single record.

    Returns
    -------
    pd.DataFrame
        Monthly H3-cell dataframe with all model features (legacy 31 plus the
        temporal extension, in FEATURE_COLUMNS order) plus H3Cell and
        YearMonth identifier columns.
    """
    logger.info("build_features: starting pipeline (include_target=%s).", include_target)

    df = validate_dataframe(df)
    df = create_h3_cells(df)

    if include_target and len(df) > 0:
        cells = df["H3Cell"].unique()
        min_date = df["IncidentFromDate"].min()
        max_date = df["IncidentFromDate"].max()
        if len(cells) > 0 and pd.notna(min_date) and pd.notna(max_date):
            all_months = pd.period_range(
                start=min_date.to_period("M"),
                end=max_date.to_period("M"),
                freq="M"
            )
            all_months_str = [str(m) for m in all_months]
            grid = pd.MultiIndex.from_product(
                [cells, all_months_str],
                names=["H3Cell", "YearMonth"]
            ).to_frame().reset_index(drop=True)

            monthly_obs = aggregate_monthly(df)
            monthly = pd.merge(grid, monthly_obs, on=["H3Cell", "YearMonth"], how="left")

            count_cols = [
                "CrimeCount", "NightCrime", "WeekendCrime",
                "EveningCrime", "AfternoonCrime", "LateNightCrime",
                "MorningCrime", "HolidayCrime", "UniqueStations", "MajorCrimeTypes",
            ]
            for c in count_cols:
                if c in monthly.columns:
                    monthly[c] = monthly[c].fillna(0)
            if "AvgHour" in monthly.columns:
                monthly["AvgHour"] = monthly["AvgHour"].fillna(12.0)
            if "GravityMean" in monthly.columns:
                monthly["GravityMean"] = monthly["GravityMean"].fillna(1.0)
            for c in ["HourSin", "HourCos", "DowSin", "DowCos"]:
                if c in monthly.columns:
                    monthly[c] = monthly[c].fillna(0.0)
            monthly = monthly.sort_values(["H3Cell", "YearMonth"]).reset_index(drop=True)
        else:
            monthly = aggregate_monthly(df)
    else:
        monthly = aggregate_monthly(df)

    monthly = create_temporal_features(monthly)
    monthly = create_historical_features(monthly)
    monthly = create_neighbor_features(monthly)
    monthly = create_station_features(monthly)

    # Target: next-month crime count per H3 cell (matches training notebook exactly)
    monthly["TargetCrimeCount"] = (
        monthly.groupby("H3Cell")["CrimeCount"].shift(-1)
    )
    if include_target:
        monthly = monthly.dropna(subset=["TargetCrimeCount"]).reset_index(drop=True)
    else:
        monthly["TargetCrimeCount"] = monthly["TargetCrimeCount"].fillna(0)

    monthly.fillna(0, inplace=True)

    # Ensure feature column order matches training
    output_cols = ["H3Cell", "YearMonth"] + FEATURE_COLUMNS
    if include_target:
        output_cols = ["H3Cell", "YearMonth", "TargetCrimeCount"] + FEATURE_COLUMNS

    missing_feat = [c for c in FEATURE_COLUMNS if c not in monthly.columns]
    if missing_feat:
        raise RuntimeError(f"Feature engineering produced missing columns: {missing_feat}")

    logger.info(
        "build_features: complete. Shape=%s, features=%d.",
        monthly.shape, len(FEATURE_COLUMNS),
    )
    return monthly[output_cols]
