// Central intelligence-status model (issue 9).
//
// The backend is the single source of truth for whether a result is live ML,
// statistical/rule-based fallback, demo data, historical analysis, or
// unavailable. These helpers centralize that mapping so Hotspots, Predictions
// and any future consumer never re-implement status logic — and never infer
// "AI" merely because a numeric score exists.

export type IntelligenceStatusKind =
  | 'UNAVAILABLE'
  | 'DEMO'
  | 'STATISTICAL_FALLBACK'
  | 'MIXED_PROVENANCE'
  | 'HISTORICAL'
  | 'LOW_CONFIDENCE'
  | 'LIVE_ML'
  | 'UNKNOWN';

export type StatusTone = 'live' | 'warn' | 'danger' | 'muted';

export interface StatusBadge {
  kind: IntelligenceStatusKind;
  /** Short chip label — always rendered as text (never color-only). */
  label: string;
  tooltip: string;
  tone: StatusTone;
  priority: number;
}

/** Raw signals a backend response may carry. All fields optional/nullable. */
export interface IntelligenceSignals {
  /** Backend `prediction_mode`: 'ML' | 'FALLBACK' | 'UNAVAILABLE' | ... */
  predictionMode?: string | null;
  /** Backend explicit loaded flag, e.g. `risk_model_loaded`. */
  modelLoaded?: boolean | null;
  /** Backend provenance: 'LIVE_DB' | 'DEMO' | 'LIVE + DEMO' | ... */
  dataProvenance?: string | null;
  /** e.g. hotspot `analysis_mode: 'STATISTICAL'` */
  analysisMode?: string | null;
  /** True when the view aggregates recorded history only (no prediction). */
  historicalOnly?: boolean;
}

const BADGES: Record<IntelligenceStatusKind, Omit<StatusBadge, 'kind' | 'priority'>> = {
  UNAVAILABLE: {
    label: 'PREDICTION UNAVAILABLE',
    tooltip: 'Predictive intelligence is currently unavailable from the backend. No score is shown rather than a stale or estimated value.',
    tone: 'danger',
  },
  DEMO: {
    label: 'DEMO DATA',
    tooltip: 'This result includes seeded/demo records and should not be treated as live operational intelligence.',
    tone: 'warn',
  },
  STATISTICAL_FALLBACK: {
    label: 'STATISTICAL FALLBACK',
    tooltip: 'Validated ML model unavailable. This result uses the configured statistical/rule-based fallback.',
    tone: 'warn',
  },
  MIXED_PROVENANCE: {
    label: 'LIVE + DEMO',
    tooltip: 'This result includes records from multiple dataset provenance types.',
    tone: 'warn',
  },
  HISTORICAL: {
    label: 'HISTORICAL',
    tooltip: 'This view summarizes recorded historical incidents and is not a live prediction.',
    tone: 'muted',
  },
  LOW_CONFIDENCE: {
    label: 'LOW CONFIDENCE',
    tooltip: 'Interpret this result cautiously because the underlying evidence or model status is incomplete.',
    tone: 'warn',
  },
  LIVE_ML: {
    label: 'LIVE ML',
    tooltip: 'Generated using the validated machine-learning prediction model.',
    tone: 'live',
  },
  UNKNOWN: {
    label: 'STATUS UNAVAILABLE',
    tooltip: 'The backend did not provide intelligence status metadata for this result.',
    tone: 'muted',
  },
};

const PRIORITY: Record<IntelligenceStatusKind, number> = {
  UNAVAILABLE: 1,
  DEMO: 2,
  MIXED_PROVENANCE: 3,
  STATISTICAL_FALLBACK: 4,
  LOW_CONFIDENCE: 5,
  HISTORICAL: 6,
  UNKNOWN: 7,
  LIVE_ML: 8,
};

function makeBadge(kind: IntelligenceStatusKind): StatusBadge {
  return { kind, priority: PRIORITY[kind], ...BADGES[kind] };
}

/**
 * Resolve backend signals into ordered status badges (primary first).
 * Priority: UNAVAILABLE > DEMO > FALLBACK > LOW_CONFIDENCE > LIVE_ML.
 * Missing metadata yields UNKNOWN — never an assumed LIVE_ML.
 */
export function getIntelligenceStatus(signals: IntelligenceSignals): StatusBadge[] {
  const badges: StatusBadge[] = [];
  const mode = (signals.predictionMode || '').trim().toUpperCase();
  const provenance = (signals.dataProvenance || '').trim().toUpperCase();
  const analysisMode = (signals.analysisMode || '').trim().toUpperCase();
  const demoProvenance = provenance.includes('DEMO');
  const liveProvenance = provenance.includes('LIVE') && !provenance.includes('UNAVAILABLE');

  if (mode === 'UNAVAILABLE' || (signals.modelLoaded === false && mode !== 'ML')) {
    badges.push(makeBadge('UNAVAILABLE'));
  }
  if (demoProvenance && liveProvenance) {
    badges.push(makeBadge('MIXED_PROVENANCE'));
  } else if (demoProvenance) {
    badges.push(makeBadge('DEMO'));
  }
  if (mode === 'FALLBACK' || analysisMode === 'STATISTICAL_FALLBACK') {
    badges.push(makeBadge('STATISTICAL_FALLBACK'));
  } else if (mode === 'ML') {
    badges.push(makeBadge('LIVE_ML'));
  }
  if (analysisMode === 'STATISTICAL' && !badges.some((b) => b.kind === 'STATISTICAL_FALLBACK')) {
    // Statistical methodology over recorded history — honest, non-ML labeling.
    if (signals.historicalOnly !== false) badges.push(makeBadge('HISTORICAL'));
    else badges.push(makeBadge('STATISTICAL_FALLBACK'));
  } else if (signals.historicalOnly) {
    badges.push(makeBadge('HISTORICAL'));
  }

  if (badges.length === 0) badges.push(makeBadge('UNKNOWN'));
  return badges.sort((a, b) => a.priority - b.priority);
}

/** Chip label for a prediction result, e.g. 'LIVE ML · Model v3'. */
export function getPredictionLabel(
  signals: IntelligenceSignals & { modelVersion?: string | null },
): string {
  const [primary] = getIntelligenceStatus(signals);
  if (!primary) return BADGES.UNKNOWN.label;
  if (primary.kind === 'LIVE_ML' && signals.modelVersion && signals.modelVersion !== 'untrained') {
    return `LIVE ML · Model v${String(signals.modelVersion).replace(/^v/i, '')}`;
  }
  return primary.label;
}

/** Provenance display label; only uses values actually reported upstream. */
export function getProvenanceLabel(provenance?: string | null): string | null {
  if (!provenance) return null;
  const normalized = provenance.trim().toUpperCase();
  if (normalized === 'LIVE_DB' || normalized === 'LIVE') return 'SAKSHA Crime Records';
  if (normalized === 'DEMO') return 'Demo Dataset';
  if (normalized.includes('DEMO') && normalized.includes('LIVE')) return 'Live + Demo Records';
  return normalized;
}

export interface ConfidenceDisplay {
  level: 'HIGH' | 'MEDIUM' | 'LOW';
  pct: number;
  label: string;
  lowConfidence: boolean;
}

/**
 * Format a backend-provided confidence value. Returns null when the backend
 * supplied no confidence — a score is never repurposed as confidence.
 * Thresholds: >=0.75 HIGH, >=0.6 MEDIUM, otherwise LOW.
 */
export function getConfidenceLabel(confidence?: number | null): ConfidenceDisplay | null {
  if (confidence == null || !Number.isFinite(confidence)) return null;
  const pct = Math.round(confidence * 100);
  const level = pct >= 75 ? 'HIGH' : pct >= 60 ? 'MEDIUM' : 'LOW';
  return { level, pct, label: `Confidence: ${pct}%`, lowConfidence: level === 'LOW' };
}
