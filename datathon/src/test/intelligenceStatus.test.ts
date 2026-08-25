import { describe, expect, it } from 'vitest';
import {
  getIntelligenceStatus,
  getPredictionLabel,
  getProvenanceLabel,
  getConfidenceLabel,
} from '../services/intelligenceStatus';

const kinds = (signals: Parameters<typeof getIntelligenceStatus>[0]) =>
  getIntelligenceStatus(signals).map((b) => b.kind);

describe('intelligence status model (issue 9)', () => {
  it('Test 1 — prediction_mode=ML maps to LIVE ML', () => {
    expect(kinds({ predictionMode: 'ML', dataProvenance: 'LIVE_DB' })).toEqual(['LIVE_ML']);
    expect(getPredictionLabel({ predictionMode: 'ML', modelVersion: '3' })).toBe('LIVE ML · Model v3');
  });

  it('Test 2 — prediction_mode=FALLBACK maps to STATISTICAL FALLBACK, never LIVE ML', () => {
    const badges = kinds({ predictionMode: 'FALLBACK', dataProvenance: 'LIVE_DB' });
    expect(badges).toContain('STATISTICAL_FALLBACK');
    expect(badges).not.toContain('LIVE_ML');
  });

  it('Test 3 — provenance=DEMO maps to DEMO DATA (primary) with ML noted secondarily', () => {
    const badges = getIntelligenceStatus({ predictionMode: 'ML', dataProvenance: 'DEMO' });
    expect(badges[0].kind).toBe('DEMO');
    expect(badges[0].label).toBe('DEMO DATA');
    expect(badges.map((b) => b.kind)).not.toContain('MIXED_PROVENANCE');
  });

  it('Test 4 — LIVE + DEMO maps to mixed-provenance warning, not plain LIVE', () => {
    const badges = getIntelligenceStatus({ predictionMode: 'ML', dataProvenance: 'LIVE + DEMO' });
    expect(badges.map((b) => b.kind)).toEqual(['MIXED_PROVENANCE', 'LIVE_ML']);
    expect(getProvenanceLabel('LIVE + DEMO')).toBe('Live + Demo Records');
  });

  it('Test 5 — numeric confidence <0.6 is flagged LOW CONFIDENCE', () => {
    expect(getConfidenceLabel(0.5)?.lowConfidence).toBe(true);
    expect(getConfidenceLabel(0.5)?.label).toBe('Confidence: 50%');
    expect(getConfidenceLabel(0.9)?.level).toBe('HIGH');
  });

  it('Test 6 — statistical analysis of recorded history is HISTORICAL, not predictive ML', () => {
    expect(kinds({ analysisMode: 'STATISTICAL', dataProvenance: 'LIVE_DB', historicalOnly: true })).toEqual(['HISTORICAL']);
  });

  it('Test 7 — model unavailable yields PREDICTION UNAVAILABLE with no score claim', () => {
    const badges = getIntelligenceStatus({ predictionMode: 'UNAVAILABLE', modelLoaded: false });
    expect(badges[0].kind).toBe('UNAVAILABLE');
    expect(badges[0].label).toBe('PREDICTION UNAVAILABLE');
  });

  it('Test 9 — missing metadata yields STATUS UNAVAILABLE, never assumed LIVE ML', () => {
    const badges = getIntelligenceStatus({});
    expect(badges).toHaveLength(1);
    expect(badges[0].kind).toBe('UNKNOWN');
    expect(badges[0].label).toBe('STATUS UNAVAILABLE');
  });

  it('priority orders UNAVAILABLE above DEMO above FALLBACK', () => {
    const badges = getIntelligenceStatus({ predictionMode: 'FALLBACK', modelLoaded: false, dataProvenance: 'DEMO' });
    expect(badges[0].kind).toBe('UNAVAILABLE');
    expect(badges[1].kind).toBe('DEMO');
    expect(badges[2].kind).toBe('STATISTICAL_FALLBACK');
  });

  it('confidence is null when the backend supplies none — scores are not repurposed', () => {
    expect(getConfidenceLabel(undefined)).toBeNull();
    expect(getConfidenceLabel(null)).toBeNull();
    expect(getConfidenceLabel(NaN)).toBeNull();
  });
});
