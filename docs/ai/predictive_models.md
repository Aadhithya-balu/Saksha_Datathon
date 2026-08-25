# SAKSHA Predictive Intelligence: District Risk, Forecast & Hotspot ML Models

## 1. Overview
SAKSHA's predictive intelligence pipeline provides empirical, time-aware machine learning forecasts for crime patterns across Karnataka police jurisdictions. The system adheres to strict operational principles:
- **Zero Fabricated Intelligence**: Predictions, confidence levels, and validation metrics are grounded directly in real PostgreSQL database records (`crime_cases`, `locations`, `crime_categories`, `firs`).
- **Explicit ML Mode vs Fallback Mode**: If a validated, compatible model artifact is unavailable or input data is sparse, the system explicitly returns `prediction_mode: "FALLBACK"` (or `"UNAVAILABLE"`), never misrepresenting heuristics as trained ML intelligence.
- **Time-Aware Validation & No Data Leakage**: Models are trained and evaluated chronologically using `TimeSeriesSplit` and historical holdout splits to ensure no future data leaks into past feature computations.

---

## 2. Prediction Targets & Formulations

### A. District Risk Scoring (`DistrictRiskModel`)
- **Unit of Prediction**: District $\times$ Target Month.
- **Target Formulation**: `TargetRiskScore` — A normalized relative risk index (0 to 100) reflecting overall incident density, violent/serious crime concentration, and night/weekend temporal spikes.
- **Algorithm**: `RandomForestRegressor` with bounded non-linear feature interactions and tree-based feature importances.
- **Baseline Model**: Historical district mean risk index.
- **Evaluation Metrics**:
  - Root Mean Squared Error (RMSE)
  - Mean Absolute Error (MAE)
  - Coefficient of Determination ($R^2$)
  - Baseline Improvement Percentage: $\frac{\text{RMSE}_{\text{baseline}} - \text{RMSE}_{\text{model}}}{\text{RMSE}_{\text{baseline}}} \times 100\%$

### B. District Crime Count Forecasting (`DistrictForecastModel`)
- **Unit of Prediction**: District $\times$ Next Month.
- **Target Formulation**: `TargetCrimeCount` — Forecasted total incident count per district.
- **Algorithm**: `XGBoostRegressor` (with `LightGBM` fallback) with lag features ($Lag_1, Lag_2, Lag_3, Lag_6$), moving averages (3-month, 6-month), EMA, and seasonal sinusoidal cycles.
- **Baseline Model**: Previous month volume ($Lag_1$) and 3-month moving average.
- **Confidence Interval**: 95% prediction interval $[\hat{y} - 1.96 \cdot \text{RMSE}, \hat{y} + 1.96 \cdot \text{RMSE}]$.

### C. Spatial Hotspot Prediction (`HotspotModel`)
- **Unit of Prediction**: Uber H3 Hexagonal Grid Cell (Resolution 7 $\approx 1.2\text{ km}^2$) $\times$ Next Month.
- **Target Formulation**: `TargetCrimeCount` — Number of crime incidents occurring within each H3 hex cell during the target month.
- **Algorithm**: `LightGBMRegressor` with spatial neighbor density, time-of-day ratios (evening, late night, morning), and localized historical crime rate lags.
- **Baseline Model**: Historical spatial cell moving average (`RollingMean3`).
- **Ranking & Validation Metrics**:
  - Precision@K: Fraction of top $K$ predicted cells that are true top $K$ historical hot zones in the held-out test period.
  - Hit Rate: Probability that predicted critical zones capture subsequent actual incidents.

---

## 3. Feature Engineering & Temporal Integrity

### Extracted Feature Schema

#### District Risk Features (`RISK_FEATURE_COLUMNS`)
1. `crime_count`: Total incident count in current period.
2. `night_crime_ratio`: Fraction of incidents between 20:00 and 05:00.
3. `weekend_crime_ratio`: Fraction of incidents on Saturday/Sunday.
4. `unique_categories`: Number of distinct crime heads/categories active in the district.
5. `month_sin`, `month_cos`: Trigonometric seasonal encoding.
6. `season_summer`, `season_monsoon`, `season_post_monsoon`: Karnataka seasonal flags.
7. `lag_1`, `lag_3`: Historical incident count at 1 and 3 months prior.
8. `rolling_mean_3`, `rolling_std_3`: 3-month rolling mean and volatility.
9. `yoy_growth`: Year-over-year rate of change.

#### Hotspot Features (`FEATURE_COLUMNS`)
1. `CrimeCount`, `NightCrime`, `WeekendCrime`, `AvgHour`: Core volume and temporal signals.
2. `UniqueStations`, `MajorCrimeTypes`, `GravityMean`: Jurisdictional and severity indicators.
3. `Lag_1`, `Lag_2`, `Lag_3`, `Lag_6`: Spatial temporal lags.
4. `RollingMean3`, `RollingMean6`, `RollingStd3`, `RollingMax6`, `EMA3`: Rolling window filters.
5. `GrowthRate`, `Momentum`, `Acceleration`: First and second derivatives of crime rate.
6. `NeighborCrimeCount`, `NeighborDensity`, `LocalDensityRatio`: 1-ring H3 topological neighbor density.
7. `EveningCrime`, `AfternoonCrime`, `LateNightCrime`, `HolidayCrime`: Granular temporal breakdowns including fixed Karnataka public holidays.

---

## 4. Model Artifact Management & Serialization

Trained artifacts are serialized in `app/ai/models/` and synced with `app/models/`:
- `risk_model.pkl` & `risk_model_meta.json`
- `forecast_model.pkl` & `forecast_model_meta.json`
- `hotspot_model.pkl` & `feature_columns.json`
- `model_metadata.json`: Full lineage, including `version`, `trained_on`, `training_period`, `validation_period`, `validation_status`, `feature_count`, and `features`.
- `training_metrics.json`: Empirical test metrics alongside `baseline_comparison` measurements.

---

## 5. Explainability & Authentic Confidence

1. **Explainable Factors**: For any prediction, the top contributing factors are computed directly from the model's feature importance vectors mapped to the input feature deviations relative to district baselines.
2. **Confidence Computation**:
   - In `ML` mode: $\text{Confidence} = \max\left(0.1, 1.0 - \frac{\text{RMSE}}{\hat{y} + \epsilon}\right)$, scaled by feature completeness.
   - In `FALLBACK` mode: Explicitly fixed to $0.5$ (or `LOW`) with `prediction_mode: "FALLBACK"` so callers are never misled.

---

## 6. Retraining Workflow

```text
New DB Crime Records
        ↓
Data Validation & Cleaning
        ↓
Time-Aware Feature Extraction (No Future Leakage)
        ↓
Chronological Train / Validation Split
        ↓
Hyperparameter Optimization (Optuna / CV)
        ↓
Held-Out Test Evaluation & Baseline Benchmarking
        ↓
Artifact Serialization + Metadata Lineage
        ↓
In-Memory Cache Invalidation (Hot Reload via refresh service)
```

Retraining can be invoked programmatically via `POST /api/v2/ai/predictions/train` by authorized administrators (`ROLE_ADMIN`).
