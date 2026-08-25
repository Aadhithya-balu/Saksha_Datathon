import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

// jsdom lacks ResizeObserver, which recharts' ResponsiveContainer requires.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal('ResizeObserver', ResizeObserverStub);

const riskPayload = (prediction_mode: string) => ({
  district_id: null,
  window: 'next_7d',
  model_version: '1.0.0',
  prediction_mode,
  risk_model_loaded: prediction_mode === 'ML',
  data_provenance: 'LIVE_DB',
  grid_predictions: [
    {
      district: 'Bengaluru Urban',
      year_month: 'current',
      risk_score: 82,
      predicted_crime_count: 12,
      risk_band: 'HIGH',
      confidence: 0.5,
      top_factors: [],
      resource_recommendation: 'Increase patrol frequency.',
    },
  ],
});

vi.mock('../services/api', () => ({
  getRiskScores: vi.fn(),
  getAnomalies: vi.fn(),
  getModelInfo: vi.fn(),
  getSeasonBreakdown: vi.fn(),
  getEmergingTrends: vi.fn(),
  trainRiskModels: vi.fn(),
  getSociologicalSocioeconomic: vi.fn(),
}));

import { getRiskScores, getAnomalies, getModelInfo, getSeasonBreakdown, getEmergingTrends, getSociologicalSocioeconomic } from '../services/api';
import { Predictions } from '../pages/Predictions';

beforeEach(() => {
  vi.mocked(getRiskScores).mockReset();
  vi.mocked(getAnomalies).mockReset();
  vi.mocked(getModelInfo).mockReset();
  vi.mocked(getSeasonBreakdown).mockReset();
  vi.mocked(getEmergingTrends).mockReset();
  vi.mocked(getSociologicalSocioeconomic).mockReset();
  vi.mocked(getAnomalies).mockResolvedValue({ anomalies: [] });
  vi.mocked(getModelInfo).mockResolvedValue({
    model_name: 'SAKSHA District Risk & Forecast',
    risk_algorithm: 'RandomForest',
    forecast_algorithm: 'XGBoost',
    version: '1.0.0',
    trained_on: null,
    training_rows: 0,
    risk_metrics: {},
    forecast_metrics: {},
    risk_model_loaded: false,
    forecast_model_loaded: false,
  });
  vi.mocked(getSeasonBreakdown).mockResolvedValue({ seasons: [] });
  vi.mocked(getEmergingTrends).mockResolvedValue([]);
  vi.mocked(getSociologicalSocioeconomic).mockRejectedValue(new Error('offline'));
});

function renderPredictions() {
  return render(<Predictions />);
}

describe('Predictions page intelligence status (issue 9 §28)', () => {
  it('Test 1 — backend prediction_mode=ML renders LIVE ML', async () => {
    vi.mocked(getRiskScores).mockResolvedValue(riskPayload('ML'));
    renderPredictions();
    await waitFor(() => expect(screen.getAllByText(/LIVE ML/).length).toBeGreaterThan(0));
  });

  it('Test 2 — backend prediction_mode=FALLBACK renders STATISTICAL FALLBACK without any LIVE ML label', async () => {
    vi.mocked(getRiskScores).mockResolvedValue(riskPayload('FALLBACK'));
    renderPredictions();
    await waitFor(() => expect(screen.getAllByText(/STATISTICAL FALLBACK/).length).toBeGreaterThan(0));
    expect(screen.queryByText(/LIVE ML/)).not.toBeInTheDocument();
  });

  it('Test 5 — low backend confidence surfaces the LOW CONFIDENCE warning', async () => {
    vi.mocked(getRiskScores).mockResolvedValue(riskPayload('FALLBACK'));
    renderPredictions();
    await waitFor(() => expect(screen.getByText('LOW CONFIDENCE')).toBeInTheDocument());
    // Confidence value itself is only shown because the backend supplied 0.5.
    expect(screen.getByText(/Confidence: 50%/)).toBeInTheDocument();
  });

  it('Test 8 — API failure shows a controlled error state, no fabricated status', async () => {
    vi.mocked(getRiskScores).mockRejectedValue(new Error('Service unavailable'));
    renderPredictions();
    await waitFor(() => expect(screen.getByText(/Failed to load prediction data/i)).toBeInTheDocument());
    expect(screen.queryByText(/LIVE ML/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Retry/i)).toBeInTheDocument();
  });

  it('Test 9 — missing prediction_mode never claims LIVE ML', async () => {
    const payload = riskPayload('ML');
    delete (payload as Record<string, unknown>).prediction_mode;
    vi.mocked(getRiskScores).mockResolvedValue(payload);
    renderPredictions();
    await waitFor(() => expect(screen.getByText('STATUS UNAVAILABLE')).toBeInTheDocument());
    expect(screen.queryByText(/LIVE ML/)).not.toBeInTheDocument();
  });

  it('Test 10 — refresh updates the badge from LIVE ML to STATISTICAL FALLBACK with no stale status', async () => {
    vi.mocked(getRiskScores).mockResolvedValueOnce(riskPayload('ML'));
    const first = renderPredictions();
    await waitFor(() => expect(screen.getAllByText(/LIVE ML/).length).toBeGreaterThan(0));

    vi.mocked(getRiskScores).mockResolvedValue(riskPayload('FALLBACK'));
    first.unmount();
    render(<Predictions />);
    await waitFor(() => expect(screen.getAllByText(/STATISTICAL FALLBACK/).length).toBeGreaterThan(0));
    expect(screen.queryByText(/LIVE ML/)).not.toBeInTheDocument();
  });
});

