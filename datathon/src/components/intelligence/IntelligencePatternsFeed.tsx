import React, { useState } from 'react';
import {
  Activity,
  ChevronDown,
  Cpu,
  FileText,
  Flame,
  Info,
  MapPin,
  Radar,
  RefreshCw,
  Send,
  ShieldAlert,
  Target,
  TrendingUp,
} from 'lucide-react';
import {
  dispatchIntelligenceAction,
  type SupportingSignal,
  type UnifiedIntelligenceResult,
} from '../../services/api';

interface IntelligencePatternsFeedProps {
  patterns: UnifiedIntelligenceResult[];
  total: number;
  loading?: boolean;
  running?: boolean;
  error?: string | null;
  onRunFusion?: () => void;
}

/* ----------------------------- plain-language ----------------------------- */

interface PlainInsight {
  category: string;
  headline: string;
  summary: string;
  forecastLine: string;
  riskWord: string;
  confidenceWord: string;
  methodWord: string;
  evidence: { label: string; description: string }[];
}

function buildPlainInsight(p: UnifiedIntelligenceResult): PlainInsight {
  let category = (p.pattern_type || '')
    .replace(/^Emerging\s+/i, '')
    .replace(/\s*(MO Signature|Hotspot Cluster|Cluster|Spike)$/i, '')
    .trim();
  if (!category) category = 'Reported crime';

  const district = p.location?.district || 'the district';
  const stations = p.location?.stations || [];
  const c = p.change_from_baseline || ({} as any);
  const change = Number(c.change_percentage) || 0;
  const abs = Math.abs(change);
  const direction = change >= 0 ? 'up' : 'down';

  const baselineDays = c.baseline_window_days || 90;
  const currentDays = c.current_window_days || 30;

  let summary =
    `${category} incidents in ${district} are ${direction} by ${abs}% compared with the ` +
    `previous ${baselineDays}-day average (${Math.round(c.baseline_count || 0)} → ${c.current_count ?? 0} ` +
    `in the past ${currentDays} days).`;
  if (stations.length) {
    summary += ` The recent activity is concentrated around ${stations.slice(0, 3).join(', ')}${stations.length > 3 ? ` and ${stations.length - 3} more locations` : ''}.`;
  } else {
    summary += ' The pattern appears spread across the district.';
  }

  let forecastLine = '';
  if (p.forecast) {
    const trend =
      p.forecast.trend === 'increasing' ? 'continue rising'
      : p.forecast.trend === 'decreasing' ? 'continue falling'
      : 'stay relatively steady';
    forecastLine =
      `Next-month forecast: approximately ${Math.round(p.forecast.predicted_crime_count)} incidents — ` +
      `the trend is expected to ${trend}. ${p.forecast.prediction_mode === 'ML' ? 'This uses the trained forecasting model.' : 'This uses a rule-based estimate.'}`;
  }

  const riskScore = p.risk_score || 0;
  const riskWord = riskScore >= 0.7 ? 'HIGH RISK' : riskScore >= 0.4 ? 'MEDIUM RISK' : 'LOWER RISK';

  const conf = p.confidence || 0;
  const confidenceWord = conf >= 0.85 ? 'High confidence' : conf >= 0.6 ? 'Moderate confidence' : 'Lower confidence';

  const methodWord =
    p.ml_status === 'ML' ? 'trained predictive models'
    : p.ml_status === 'HYBRID' ? 'trained models combined with risk rules'
    : p.ml_status === 'FALLBACK' ? 'automated rules (live models unavailable)'
    : p.ml_status === 'RULE_BASED' ? 'deterministic analytical rules'
    : 'analytical rules';

  const signalLabels: Record<string, string> = {
    anomaly: 'Unusual activity spike',
    temporal: 'Timing pattern',
    spatial_hotspot: 'Geographic hotspot',
    forecast: 'Next-month forecast',
    mo_pattern: 'Shared modus operandi',
    entity_link: 'Linked persons / vehicles',
  };

  const evidence = (p.supporting_signals || []).map((s: SupportingSignal) => ({
    label: signalLabels[s.signal_type] || s.signal_type.replace(/_/g, ' '),
    description: s.description,
  }));

  const headline =
    p.recommended_action_input?.title && p.recommended_action_input.title !== 'Recommended Action'
      ? p.recommended_action_input.title
      : `${category} emerging in ${district}`;

  return { category, headline, summary, forecastLine, riskWord, confidenceWord, methodWord, evidence };
}

/* ----------------------------- pattern card ------------------------------ */

const priorityCls: Record<string, string> = {
  CRITICAL: 'text-[#C94A2A] border-[#C94A2A]/40',
  HIGH: 'text-amber-400 border-amber-500/40',
  MEDIUM: 'text-[#D4820A] border-[#D4820A]/40',
  LOW: 'text-[var(--text-muted)] border-[var(--border-primary)]',
};

const PatternCard: React.FC<{
  pattern: UnifiedIntelligenceResult;
  dispatching: boolean;
  dispatched: boolean;
  onDispatch: () => void;
}> = ({ pattern, dispatching, dispatched, onDispatch }) => {
  const [open, setOpen] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const insight = buildPlainInsight(pattern);
  const rec = pattern.recommended_action_input;
  const action = rec && rec.description ? rec : null;

  return (
    <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
      {/* Headline strip */}
      <div className="flex items-start gap-2 px-2.5 pt-2">
        <span className="w-7 h-7 rounded-md flex items-center justify-center shrink-0 border border-[#C94A2A]/40 bg-[#C94A2A]/10 text-[#C94A2A] mt-0.5">
          <Flame className="w-3.5 h-3.5" />
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="px-1.5 py-0.5 rounded border border-[#a855f7]/40 bg-[#a855f7]/5 text-[#a855f7] text-[7px] font-mono uppercase font-bold tracking-wide">
              {insight.category}
            </span>
            <span className="px-1.5 py-0.5 rounded border border-[#C94A2A]/40 text-[#C94A2A] text-[7px] font-mono uppercase font-bold tracking-wide">
              {insight.riskWord}
            </span>
            <span className="px-1.5 py-0.5 rounded border border-[#0E9E78]/40 text-[#0E9E78] text-[7px] font-mono uppercase font-bold tracking-wide">
              {insight.confidenceWord}
            </span>
          </div>
          <p className="text-[10.5px] font-semibold text-[var(--text-primary)] leading-snug mt-1">{insight.headline}</p>
          <p className="flex items-center gap-1 text-[8px] font-mono text-[var(--text-muted)] mt-0.5">
            <MapPin className="w-2.5 h-2.5" />
            {pattern.location?.district}
            {pattern.location?.stations?.length ? ` • ${pattern.location.stations.join(', ')}` : ''}
          </p>
        </div>
        <button
          onClick={() => setOpen((o) => !o)}
          className="mt-1.5 p-1 rounded hover:bg-[var(--bg-elevated)] text-[var(--text-muted)] transition-colors cursor-pointer shrink-0"
          title={open ? 'Hide analysis' : 'Show analysis'}
        >
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Plain-language summary (always visible) */}
      <p className="px-2.5 pt-1.5 text-[9px] leading-relaxed text-[var(--text-secondary)]">{insight.summary}</p>
      {insight.forecastLine && (
        <p className="px-2.5 pt-1 flex items-start gap-1 text-[9px] leading-relaxed text-[var(--text-secondary)]">
          <TrendingUp className="w-3 h-3 text-[#D4820A] shrink-0 mt-0.5" />
          {insight.forecastLine}
        </p>
      )}

      {/* Recommended action strip */}
      {action && (
        <div className="mx-2.5 mt-2 p-2 rounded border border-[#1E6FD9]/30 bg-[#1E6FD9]/5">
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-[8px] font-mono font-bold text-[#1E6FD9] uppercase tracking-wide">
              <Target className="w-3 h-3" /> Recommended action
            </span>
            <span className={`text-[6.5px] font-mono uppercase font-bold px-1.5 py-0.5 rounded border ${priorityCls[rec.priority] || priorityCls.HIGH}`}>
              {rec.priority === 'CRITICAL' ? 'Do now' : rec.priority}
            </span>
          </div>
          <p className="text-[10px] font-semibold text-[var(--text-primary)] mt-1">{rec.title}</p>
          <p className="text-[8.5px] text-[var(--text-secondary)] leading-relaxed mt-0.5">{rec.description}</p>
          <div className="flex items-center justify-between gap-2 mt-1.5">
            <span className="text-[7px] font-mono text-[var(--text-muted)] uppercase">
              {pattern.related_fir_ids?.length ? `Based on ${pattern.related_fir_ids.length} related FIR(s)` : 'No related FIR references'}
            </span>
            <button
              onClick={onDispatch}
              disabled={dispatching || dispatched}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded border text-[7.5px] font-mono font-bold uppercase transition-colors cursor-pointer ${
                dispatched
                  ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
                  : 'border-[#1E6FD9]/40 text-[#1E6FD9] hover:bg-[#1E6FD9]/10'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              <Send className="w-2.5 h-2.5" />
              {dispatching ? 'Dispatching…' : dispatched ? 'Dispatched' : 'Dispatch Action'}
            </button>
          </div>
        </div>
      )}

      {/* Expanded analysis */}
      {open && (
        <div className="px-2.5 pb-2 pt-2 mt-2 border-t border-[var(--border-primary)] space-y-2">
          {insight.evidence.length > 0 && (
            <div>
              <span className="text-[7.5px] font-mono uppercase font-bold tracking-wider text-[var(--text-muted)]">
                Why this was flagged
              </span>
              <div className="mt-1 space-y-1">
                {insight.evidence.map((e, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <span className="mt-0.5 shrink-0 w-1.5 h-1.5 rounded-full bg-[#D4820A]" />
                    <span className="text-[8.5px] text-[var(--text-secondary)] leading-relaxed">
                      <span className="text-[var(--text-primary)] font-semibold">{e.label}: </span>
                      {e.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-1.5 text-[7px] font-mono uppercase">
            <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
              {pattern.supporting_signals?.length || 0} corroborating indicators
            </span>
            <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
              {pattern.related_entity_ids?.length || 0} linked persons / vehicles / places
            </span>
            <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
              {pattern.affected_h3_cells?.length || 0} zones affected
            </span>
            <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
              Method: {insight.methodWord}
            </span>
          </div>

          {pattern.related_fir_ids?.length > 0 && (
            <p className="flex items-center gap-1.5 text-[8px] font-mono text-[var(--text-muted)]">
              <FileText className="w-3 h-3" /> Related FIRs: {pattern.related_fir_ids.slice(0, 5).join(', ')}
              {pattern.related_fir_ids.length > 5 ? ` +${pattern.related_fir_ids.length - 5}` : ''}
            </p>
          )}

          <button
            onClick={() => setShowDetail((s) => !s)}
            className="flex items-center gap-1 text-[7.5px] font-mono uppercase text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
          >
            <Info className="w-3 h-3" /> {showDetail ? 'Hide raw detail' : 'View raw analytical detail'}
          </button>

          {showDetail && (
            <div className="p-2 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/30 text-[7px] font-mono text-[var(--text-muted)] uppercase space-y-1">
              <p>id: {pattern.intelligence_id}</p>
              <p>status: {pattern.ml_status} v{pattern.model_version} · {pattern.data_provenance}</p>
              <p>risk: {pattern.risk_score} · confidence: {pattern.confidence}</p>
              <p>time window: {pattern.time_window || '—'} · generated: {pattern.detection_timestamp ? new Date(pattern.detection_timestamp).toLocaleString() : '—'}</p>
              <p className="break-all">h3: {(pattern.affected_h3_cells || []).join(', ') || '—'}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

/* -------------------------------- feed ----------------------------------- */

const IntelligencePatternsFeed: React.FC<IntelligencePatternsFeedProps> = ({
  patterns,
  total,
  loading = false,
  running = false,
  error = null,
  onRunFusion,
}) => {
  const [dispatchingId, setDispatchingId] = useState<string | null>(null);
  const [dispatchedId, setDispatchedId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const dispatch = async (p: UnifiedIntelligenceResult) => {
    setDispatchingId(p.intelligence_id);
    setActionError(null);
    setDispatchedId(null);
    try {
      await dispatchIntelligenceAction(p.intelligence_id, {});
      setDispatchedId(p.intelligence_id);
    } catch (e: any) {
      setActionError(e?.message || 'Dispatch failed');
    } finally {
      setDispatchingId(null);
    }
  };

  return (
    <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-elevated)]/40">
        <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[#C94A2A]">
          <Radar className="w-3.5 h-3.5" /> Emerging Crime Insights
        </span>
        <div className="flex items-center gap-2">
          <span className="text-[8px] font-mono text-[var(--text-muted)]">
            {total} pattern{total === 1 ? '' : 's'}
          </span>
          {onRunFusion && (
            <button
              onClick={onRunFusion}
              disabled={running || loading}
              className="inline-flex items-center gap-1 px-2 py-1 rounded border border-[#a855f7]/40 text-[#a855f7] hover:bg-[#a855f7]/10 font-mono text-[7.5px] uppercase font-bold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-2.5 h-2.5 ${running ? 'animate-spin' : ''}`} />
              {running ? 'Fusing…' : 'Run Fusion'}
            </button>
          )}
        </div>
      </div>

      <p className="px-3 py-1.5 border-b border-[var(--border-primary)] text-[7.5px] font-mono text-[var(--text-muted)]">
        Multi-signal fusion of anomaly detection, timing, hotspots, forecasting, modus operandi and entity links — explained in plain language.
      </p>

      {/* Body */}
      {loading ? (
        <div className="p-6 text-center">
          <div className="w-5 h-5 mx-auto mb-2 border-2 border-[#C94A2A]/20 border-t-[#C94A2A] rounded-full animate-spin" />
          <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase">Detecting emerging patterns…</span>
        </div>
      ) : error ? (
        <div className="p-6 text-center">
          <ShieldAlert className="w-6 h-6 text-amber-400 mx-auto mb-2" />
          <p className="text-[9.5px] font-mono text-[var(--text-secondary)]">{error}</p>
        </div>
      ) : patterns.length === 0 ? (
        <div className="p-8 text-center">
          <Activity className="w-6 h-6 text-[var(--text-muted)] mx-auto mb-2" />
          <p className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">No patterns detected for these filters</p>
          <p className="text-[8.5px] text-[var(--text-muted)] mt-1">
            Try widening the time window, switching detection to “Broad”, or clearing the district/category filters.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[var(--border-primary)/50] max-h-[560px] overflow-y-auto custom-scrollbar">
          {patterns.map((p) => (
            <div key={p.intelligence_id} className="p-2">
              <PatternCard
                pattern={p}
                dispatching={dispatchingId === p.intelligence_id}
                dispatched={dispatchedId === p.intelligence_id}
                onDispatch={() => dispatch(p)}
              />
            </div>
          ))}
        </div>
      )}

      {actionError && (
        <p className="px-3 py-1.5 border-t border-[var(--border-primary)] text-[8px] font-mono text-[#C94A2A]">
          {actionError}
        </p>
      )}

      {patterns.length > 0 && (
        <p className="px-3 py-1.5 border-t border-[var(--border-primary)] text-[7.5px] font-mono text-[var(--text-muted)] flex items-center gap-1">
          <Cpu className="w-2.5 h-2.5" />
          Modes: {Array.from(new Set(patterns.map((p) => p.ml_status))).join(' / ')} · Model v{patterns[0]?.model_version || '—'}
        </p>
      )}
    </div>
  );
};

export default IntelligencePatternsFeed;