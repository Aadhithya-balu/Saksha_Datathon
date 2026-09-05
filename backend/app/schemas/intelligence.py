"""Pydantic schemas for the SAKSHA Intelligence Fusion & Action Pipeline.

Defines structured types for multi-signal intelligence fusion:
- Historical baseline comparison
- Supporting analytical signals (anomaly, temporal, spatial, forecast, MO, entities)
- Unified intelligence results with full provenance and explainability
- Action recommendations preformatted for the intervention system
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class ChangeFromBaseline(BaseModel):
    """Historical baseline deviation metrics."""
    baseline_count: float = Field(..., description="Expected/normalized incident count in baseline window")
    current_count: int = Field(..., description="Observed incident count in current window")
    change_percentage: float = Field(..., description="Percentage change from baseline (e.g. +137.5)")
    direction: str = Field("stable", description="Direction of trend: increasing, decreasing, or stable")
    baseline_window_days: int = Field(90, description="Baseline lookback window in days")
    current_window_days: int = Field(30, description="Current observation window in days")


class SupportingSignal(BaseModel):
    """An analytical signal contributing to the intelligence result."""
    signal_type: str = Field(..., description="Type of signal: anomaly, temporal, spatial_hotspot, forecast, mo_pattern, entity_link")
    description: str = Field(..., description="Human-readable description of the signal finding")
    score: float | None = Field(None, description="Normalized signal strength or score (0.0 - 1.0 or count)")
    status: str = Field("CONFIRMED", description="Signal status: CONFIRMED, PROBABLE, POSSIBLE, or UNAVAILABLE")
    evidence_details: dict[str, Any] = Field(default_factory=dict, description="Structured backing evidence")


class ForecastResult(BaseModel):
    """Predictive forecast information contributing to intelligence."""
    predicted_crime_count: float = Field(..., description="Forecasted incident count for upcoming period")
    lower_bound: float | None = Field(None, description="Lower prediction interval bound")
    upper_bound: float | None = Field(None, description="Upper prediction interval bound")
    trend: str = Field("stable", description="Predicted trajectory: increasing, decreasing, stable")
    prediction_mode: str = Field("ML", description="Inference mode: ML or FALLBACK")
    period: str = Field("next_month", description="Forecast target period")


class RecommendedAction(BaseModel):
    """Actionable recommendation synthesized from fused intelligence."""
    title: str = Field(..., description="Concise action title")
    action_type: str = Field(..., description="Intervention type: patrol_surge, checkpoint, surveillance, cctv_deployment, investigation")
    description: str = Field(..., description="Actionable recommendation details for field commanders")
    priority: str = Field("HIGH", description="Action priority: CRITICAL, HIGH, MEDIUM, LOW")
    suggested_intervention: dict[str, Any] | None = Field(
        None, description="Pre-structured payload ready for submission to POST /interventions"
    )


class UnifiedIntelligenceResult(BaseModel):
    """Unified intelligence result produced by the fusion pipeline."""
    intelligence_id: str = Field(..., description="Unique intelligence identifier")
    pattern_type: str = Field(..., description="Identified pattern name, e.g. 'Emerging Theft Cluster'")
    location: dict[str, Any] = Field(..., description="Jurisdiction information: district, stations, coordinates")
    affected_h3_cells: list[str] = Field(default_factory=list, description="List of affected H3 geospatial cells (res 7)")
    time_window: str = Field(..., description="Time window evaluated, e.g. 'last_30_days'")
    change_from_baseline: ChangeFromBaseline = Field(..., description="Baseline vs current metrics")
    risk_score: float = Field(..., description="Fused composite risk score (0.0 - 1.0)")
    forecast: ForecastResult | None = Field(None, description="Forecasting model output if available")
    confidence: float = Field(..., description="Overall fusion confidence score (0.0 - 1.0)")
    supporting_signals: list[SupportingSignal] = Field(default_factory=list, description="Contributing analytical signals")
    related_fir_ids: list[str] = Field(default_factory=list, description="IDs / numbers of related FIRs")
    related_entity_ids: list[str] = Field(default_factory=list, description="IDs of linked criminals, suspects, victims")
    recommended_action_input: RecommendedAction = Field(..., description="Actionable recommendation")
    ml_status: str = Field("ML", description="Overall prediction mode: ML, FALLBACK, RULE_BASED, or HYBRID")
    model_name: str = Field("SAKSHA Intelligence Fusion", description="Name of contributing model(s)")
    model_version: str = Field("v1.0", description="Model version(s)")
    detection_timestamp: str = Field(..., description="ISO timestamp of intelligence generation")
    explanation: str = Field("", description="Detailed narrative explaining why intelligence was generated")
    contributing_analytics: dict[str, Any] = Field(default_factory=dict, description="Breakdown of contributing sources")
    data_provenance: str = Field("LIVE_DB", description="Dataset provenance: LIVE_DB, DEMO, MIXED, or UNKNOWN")


class FusionThresholdsInput(BaseModel):
    """Configurable thresholds for pattern detection & fusion."""
    min_anomaly_score: float = Field(0.60, ge=0.0, le=1.0, description="Minimum score to consider an anomaly significant")
    min_percentage_change: float = Field(20.0, description="Minimum percentage increase from baseline to flag")
    min_risk_score: float = Field(0.40, ge=0.0, le=1.0, description="Minimum fused risk score")
    min_confidence: float = Field(0.50, ge=0.0, le=1.0, description="Minimum confidence score required")
    min_supporting_signals: int = Field(2, ge=1, le=10, description="Minimum number of concurring signals required")
    min_current_incidents: int = Field(2, ge=1, description="Minimum recent incidents required")
    current_window_days: int = Field(30, ge=1, le=365, description="Observation window in days")
    baseline_window_days: int = Field(90, ge=1, le=730, description="Historical baseline window in days")


class IntelligenceFusionRequest(BaseModel):
    """Request payload for on-demand intelligence fusion."""
    district: str | None = Field(None, description="Optional district filter")
    category: str | None = Field(None, description="Optional crime category filter")
    thresholds: FusionThresholdsInput | None = Field(None, description="Optional custom threshold overrides")


class IntelligenceFusionResponse(BaseModel):
    """Response payload for intelligence fusion queries."""
    total: int = Field(..., description="Number of fused intelligence patterns returned")
    generated_at: str = Field(..., description="ISO timestamp of generation")
    patterns: list[UnifiedIntelligenceResult] = Field(default_factory=list, description="Fused intelligence results")
    thresholds_applied: dict[str, Any] = Field(default_factory=dict, description="Thresholds used for detection")
