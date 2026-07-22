from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AnomalyFeatureVector:
    feature_names: list[str]
    values: np.ndarray


def build_anomaly_features(event: dict[str, Any]) -> AnomalyFeatureVector:
    """Create a fixed-size numeric feature vector from an incoming event.

    Expected (best-effort) keys in `event`:
    - timestamp (epoch seconds or ISO string)
    - district_id
    - latitude, longitude
    - crime_category / offense_type / crime_type
    - officer_id
    - offender_id

    Missing keys are encoded as 0 / neutral values.

    Feature vector is intentionally simple to avoid duplicating shared preprocessing
    (none exists in this repo snapshot under anomaly paths).
    """

    # Timestamp feature: seconds since start of day (0..86399)
    ts = event.get("timestamp")
    day_seconds = 0.0
    if isinstance(ts, (int, float)):
        day_seconds = float(ts) % 86400.0
    elif isinstance(ts, str):
        # lightweight parsing: accept YYYY-MM-DDTHH:MM:SS
        try:
            t = ts.split("T")
            if len(t) > 1:
                time_part = t[1].split(":")
                if len(time_part) >= 2:
                    h = int(time_part[0])
                    m = int(time_part[1])
                    s = int(time_part[2].split("+")[0].split("Z")[0]) if len(time_part) > 2 else 0
                    day_seconds = float(h * 3600 + m * 60 + s)
        except Exception:
            day_seconds = 0.0

    lat = event.get("latitude")
    lon = event.get("longitude")
    lat_f = float(lat) if isinstance(lat, (int, float)) else 0.0
    lon_f = float(lon) if isinstance(lon, (int, float)) else 0.0

    # Categorical hashing into numeric buckets (stable per process only).
    # For explainability, the model uses feature names; bucket values are still meaningful.
    crime_cat = event.get("crime_category") or event.get("offense_type") or event.get("crime_type") or ""
    officer_id = event.get("officer_id") or ""
    offender_id = event.get("offender_id") or ""
    district_id = event.get("district_id") or ""

    def bucket(val: Any, mod: int) -> float:
        s = str(val)
        h = 0
        for ch in s:
            h = (h * 31 + ord(ch)) % 2**31
        return float(h % mod)

    crime_bucket = bucket(crime_cat, 97) / 97.0
    officer_bucket = bucket(officer_id, 53) / 53.0
    offender_bucket = bucket(offender_id, 101) / 101.0
    district_bucket = bucket(district_id, 29) / 29.0

    # Simple location normalization: scale lat/lon roughly into [-1,1]
    lat_norm = lat_f / 90.0
    lon_norm = lon_f / 180.0

    feature_names = [
        "day_seconds",
        "lat_norm",
        "lon_norm",
        "district_bucket",
        "crime_bucket",
        "officer_bucket",
        "offender_bucket",
    ]

    values = np.asarray(
        [
            float(day_seconds) / 86400.0,
            float(lat_norm),
            float(lon_norm),
            float(district_bucket),
            float(crime_bucket),
            float(officer_bucket),
            float(offender_bucket),
        ],
        dtype=np.float64,
    )

    return AnomalyFeatureVector(feature_names=feature_names, values=values)

