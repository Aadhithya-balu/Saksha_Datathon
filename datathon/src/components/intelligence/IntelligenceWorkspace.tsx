import React, { useEffect, useState } from 'react';
import {
  Brain, ArrowLeft, ChevronDown, Link2, FileText,
  Clock, AlertTriangle, Shield, ShieldCheck, ShieldAlert,
  Fingerprint, Target, GitBranch, Activity, ExternalLink, Sparkles,
  Network, BarChart3, Crosshair, Info, Radar, Send,
} from 'lucide-react';
import {
  buildIntelligence,
  type IntelligenceReport,
  type SupportingSignal,
  type UnifiedIntelligenceResult,
} from '../../services/api';
import { CardSkeleton } from '../ui/Skeleton';

interface IntelligenceWorkspaceProps {
  entityType: 'fir' | 'criminal' | 'case' | 'victim';
  entityId: string;
  entityLabel?: string;
  onClose?: () => void;
}

type ConfidenceLevel = 'confirmed' | 'probable' | 'possible' | 'insufficient';

interface SourceRecord {
  type: string;
  id: string;
  label: string;
}

const confidenceStyles: Record<ConfidenceLevel, { label: string; cls: string; icon: React.ReactNode }> = {
  confirmed: { label: 'CONFIRMED', cls: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40', icon: <ShieldCheck className="w-2.5 h-2.5" /> },
  probable: { label: 'PROBABLE', cls: 'bg-amber-500/10 text-amber-400 border-amber-500/40', icon: <ShieldAlert className="w-2.5 h-2.5" /> },
  possible: { label: 'POSSIBLE', cls: 'bg-blue-500/10 text-[#1E6FD9] border-[#1E6FD9]/40', icon: <Shield className="w-2.5 h-2.5" /> },
  insufficient: { label: 'INSUFFICIENT', cls: 'bg-gray-500/10 text-gray-400 border-gray-500/40', icon: <Info className="w-2.5 h-2.5" /> },
};

function confidenceClass(c: string): ConfidenceLevel {
  return (['confirmed', 'probable', 'possible', 'insufficient'] as ConfidenceLevel[]).includes(c as ConfidenceLevel)
    ? c as ConfidenceLevel
    : 'insufficient';
}

const ConfidenceBadge: React.FC<{ confidence: string }> = ({ confidence }) => {
  const lvl = confidenceClass(confidence);
  const s = confidenceStyles[lvl];
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[7.5px] font-bold uppercase tracking-wider ${s.cls}`}>
      {s.icon}
      {s.label}
    </span>
  );
};

const entityTypeColor: Record<string, string> = {
  criminal: 'text-[#C94A2A] border-[#C94A2A]/40',
  fir: 'text-[#1E6FD9] border-[#1E6FD9]/40',
  case: 'text-[#a855f7] border-[#a855f7]/40',
  victim: 'text-[#0E9E78] border-[#0E9E78]/40',
  officer: 'text-[#D4820A] border-[#D4820A]/40',
  location: 'text-[#D4820A] border-[#D4820A]/40',
  organization: 'text-[#a855f7] border-[#a855f7]/40',
  vehicle: 'text-[#0E9E78] border-[#0E9E78]/40',
  weapon: 'text-[#C94A2A] border-[#C94A2A]/40',
};

function navigateTo(type: string, id: string) {
  const tabMap: Record<string, string> = {
    fir: 'fir',
    case: 'crime_cases',
    crime: 'crime_cases',
    crime_case: 'crime_cases',
    criminal: 'criminals',
    victim: 'victims',
    officer: 'officers',
    evidence: 'evidence',
    investigation_note: 'investigation',
    audit_log: 'notifications',
    organization: 'network',
    vehicle: 'network',
    weapon: 'network',
    location: 'network',
  };
  const tab = tabMap[type] || 'dashboard';
  window.dispatchEvent(
    new CustomEvent('navigate-tab', { detail: { tab, targetId: id } })
  );
}

const SourceLinks: React.FC<{ records: SourceRecord[] }> = ({ records }) => {
  if (!records || records.length === 0) {
    return <span className="text-[8px] text-[var(--text-muted)] italic">No source records</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {records.map((r, i) => (
        <button
          key={i}
          onClick={() => navigateTo(r.type, r.id)}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded border bg-[var(--bg-tertiary)]/40 hover:bg-[#1E6FD9]/10 text-[8px] font-mono text-[#1E6FD9] hover:text-[var(--text-primary)] transition-colors cursor-pointer"
        >
          <FileText className="w-2.5 h-2.5 shrink-0" />
          <span className="truncate max-w-[140px]">{r.label || `${r.type}·${r.id.slice(0, 8)}`}</span>
          <ExternalLink className="w-2 h-2 shrink-0" />
        </button>
      ))}
    </div>
  );
};

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string; accent?: string; tag?: React.ReactNode }> = ({ icon, title, accent = '#1E6FD9', tag }) => (
  <div className="flex items-center justify-between gap-2 w-full">
    <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider">
      <span style={{ color: accent }}>{icon}</span>
      <span className="text-[var(--text-primary)]">{title}</span>
    </span>
    {tag}
  </div>
);

const ExpandableSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  count?: number;
  accent?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  headerRight?: React.ReactNode;
}> = ({ title, icon, count, accent = '#1E6FD9', defaultOpen = false, children, headerRight }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/35 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 hover:bg-[var(--bg-elevated)]/30 transition-colors cursor-pointer text-left"
      >
        <SectionHeader
          icon={icon}
          title={count !== undefined && count > 0 ? `${title} (${count})` : title}
          accent={accent}
        />
        <span className="flex items-center gap-1.5 shrink-0">
          {headerRight}
          <ChevronDown className={`w-3.5 h-3.5 text-[var(--text-muted)] transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>
      {open && <div className="px-3.5 pb-4 pt-1 border-t border-[var(--border-primary)] space-y-2.5">{children}</div>}
    </div>
  );
};

const NetworkSnapshot: React.FC<{ snapshot: IntelligenceReport['network_snapshot'] }> = ({ snapshot }) => {
  const nodes = snapshot?.nodes || [];
  const edges = snapshot?.edges || [];
  if (nodes.length === 0) {
    return <div className="text-[9px] text-[var(--text-secondary)] uppercase">No network snapshot available</div>;
  }

  const radius = 105;
  const cx = 160;
  const cy = 140;

  const nodeColor = (type: string) =>
    type === 'criminal' ? '#C94A2A'
    : type === 'fir' ? '#1E6FD9'
    : type === 'case' ? '#a855f7'
    : type === 'victim' ? '#0E9E78'
    : '#D4820A';

  const positions: Array<{ id: string; x: number; y: number }> = nodes.map((n, i) => {
    if (i === 0) return { id: n.id, x: cx, y: cy };
    const idx = i - 1;
    const perRow = Math.max(1, nodes.length - 1);
    const angle = (2 * Math.PI * idx) / Math.max(1, perRow) - Math.PI / 2;
    return { id: n.id, x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
  });

  const posOf = (id: string) => positions.find((p) => p.id === id);

  return (
    <div>
      <svg viewBox="0 0 320 280" className="w-full max-h-[280px]">
        <defs>
          <marker id="ie-arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="#2a3a52" />
          </marker>
        </defs>
        {edges.map((e, i) => {
          const s = posOf(e.source);
          const t = posOf(e.target);
          if (!s || !t) return null;
          return (
            <g key={i}>
              <line
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke="#2a3a52"
                strokeWidth={1}
                markerEnd="url(#ie-arrow)"
              />
              <text
                x={(s.x + t.x) / 2}
                y={(s.y + t.y) / 2 - 3}
                textAnchor="middle"
                fontSize="6"
                fill="#5b6b82"
                fontFamily="monospace"
              >
                {e.relationship}
              </text>
            </g>
          );
        })}
        {positions.map((p, i) => {
          const n = nodes[i];
          const isCenter = i === 0;
          return (
            <g key={p.id} className="cursor-pointer" onClick={() => navigateTo(n.type, n.id)}>
              <circle cx={p.x} cy={p.y} r={isCenter ? 12 : 7} fill={nodeColor(n.type)} opacity={0.9} />
              <text
                x={p.x}
                y={p.y + (isCenter ? 18 : 14)}
                textAnchor="middle"
                fontSize={isCenter ? 7 : 6}
                fill="#E8EDF5"
                fontFamily="monospace"
              >
                {n.name.length > 14 ? n.name.slice(0, 13) + '…' : n.name}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-2.5 text-[7px] font-mono text-[var(--text-muted)] uppercase mt-1">
        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#C94A2A]" /> Criminal</span>
        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#1E6FD9]" /> FIR</span>
        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#a855f7]" /> Case</span>
        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#0E9E78]" /> Victim</span>
        <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#D4820A]" /> Other</span>
      </div>
    </div>
  );
};

const signalStatusStyle: Record<string, string> = {
  CONFIRMED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/40',
  PROBABLE: 'bg-amber-500/10 text-amber-400 border-amber-500/40',
  POSSIBLE: 'bg-blue-500/10 text-[#1E6FD9] border-[#1E6FD9]/40',
  UNAVAILABLE: 'bg-gray-500/10 text-gray-400 border-gray-500/40',
};

const EmergingIntelligenceSection: React.FC<{ intel: UnifiedIntelligenceResult | null | undefined }> = ({ intel }) => {
  if (!intel) return null;
  const change = intel.change_from_baseline;
  const mlCls: Record<string, string> = {
    ML: 'text-emerald-400 border-emerald-500/40',
    HYBRID: 'text-[#D4820A] border-[#D4820A]/40',
    FALLBACK: 'text-amber-400 border-amber-500/40',
    RULE_BASED: 'text-[#1E6FD9] border-[#1E6FD9]/40',
  };
  const priorityCls: Record<string, string> = {
    CRITICAL: 'text-[#C94A2A] border-[#C94A2A]/40',
    HIGH: 'text-amber-400 border-amber-500/40',
    MEDIUM: 'text-[#D4820A] border-[#D4820A]/40',
    LOW: 'text-[var(--text-muted)] border-[var(--border-primary)]',
  };

  return (
    <div className="rounded-xl border border-[#C94A2A]/30 bg-[#C94A2A]/5 overflow-hidden">
      <div className="px-3 py-2.5 border-b border-[var(--border-primary)] flex items-center justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[#C94A2A]">
          <Radar className="w-3.5 h-3.5" /> Fused Emerging Intelligence
        </span>
        <span className="flex items-center gap-1 text-[7.5px] text-[var(--text-muted)] uppercase shrink-0">
          <span className={`px-1.5 py-0.5 rounded border font-mono font-bold ${mlCls[intel.ml_status] || mlCls.RULE_BASED}`}>
            {intel.ml_status}
          </span>
        </span>
      </div>

      <div className="px-3.5 py-3 space-y-2.5">
        {/* Pattern + location */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-[10px] font-mono font-bold text-[var(--text-primary)] uppercase">
            {intel.pattern_type}
          </span>
          <div className="flex items-center gap-1.5 font-mono">
            <span className="text-[8px] px-1.5 py-0.5 rounded border text-[#C94A2A] border-[#C94A2A]/40">
              RISK {(intel.risk_score * 100).toFixed(0)}%
            </span>
            <span className="text-[8px] px-1.5 py-0.5 rounded border text-[#0E9E78] border-[#0E9E78]/40">
              CONF {(intel.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
        <p className="text-[8.5px] font-mono text-[var(--text-secondary)]">
          {intel.location?.district} • {intel.location?.stations?.join(', ') || '—'} • {intel.time_window}
        </p>

        {/* Baseline change */}
        <div className="grid grid-cols-3 gap-2 text-center font-mono">
          <div className="p-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/40">
            <span className="block text-[10px] font-bold text-[var(--text-primary)]">{change.current_count ?? '-'}</span>
            <span className="text-[7px] uppercase text-[var(--text-muted)]">current</span>
          </div>
          <div className="p-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/40">
            <span className="block text-[10px] font-bold text-[var(--text-primary)]">{(change.baseline_count ?? 0).toFixed(1)}</span>
            <span className="text-[7px] uppercase text-[var(--text-muted)]">baseline</span>
          </div>
          <div className="p-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/40">
            <span className={`block text-[10px] font-bold ${Number(change.change_percentage) >= 0 ? 'text-[#C94A2A]' : 'text-[#0E9E78]'}`}>
              {Number(change.change_percentage) >= 0 ? '+' : ''}{change.change_percentage ?? 0}%
            </span>
            <span className="text-[7px] uppercase text-[var(--text-muted)]">{change.direction || 'change'}</span>
          </div>
        </div>

        {/* Metric chips */}
        <div className="flex flex-wrap gap-1.5 text-[7.5px] font-mono uppercase">
          <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
            {intel.supporting_signals?.length || 0} signals
          </span>
          <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
            {intel.related_fir_ids?.length || 0} FIRs
          </span>
          <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
            {intel.related_entity_ids?.length || 0} entities
          </span>
          <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
            {intel.affected_h3_cells?.length || 0} H3 cells
          </span>
          <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[var(--text-muted)]">
            v{intel.model_version}
          </span>
        </div>

        {/* Supporting signals */}
        {intel.supporting_signals && intel.supporting_signals.length > 0 && (
          <div className="space-y-1">
            {intel.supporting_signals.slice(0, 6).map((s: SupportingSignal, i: number) => (
              <div key={i} className="flex items-start gap-2">
                <span className={`mt-0.5 shrink-0 px-1 py-0.5 rounded border text-[6.5px] font-mono uppercase font-bold ${signalStatusStyle[s.status] || signalStatusStyle.POSSIBLE}`}>
                  {s.status}
                </span>
                <div className="min-w-0">
                  <span className="text-[8.5px] text-[var(--text-secondary)]">{s.description}</span>
                  {s.score != null && (
                    <span className="text-[7px] text-[var(--text-muted)] font-mono ml-1">({Math.round(s.score * 100)}%)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Forecast */}
        {intel.forecast && (
          <div className="flex items-center gap-2 p-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/40 text-[8.5px] font-mono">
            <BarChart3 className="w-3 h-3 text-[#D4820A] shrink-0" />
            <span className="text-[var(--text-muted)] uppercase text-[7.5px]">Forecast</span>
            <span className="text-[var(--text-primary)]">~{intel.forecast.predicted_crime_count}</span>
            <span className="text-[var(--text-muted)]">{intel.forecast.trend}</span>
            <span className={`ml-auto text-[7px] uppercase ${intel.forecast.prediction_mode === 'ML' ? 'text-emerald-400' : 'text-amber-400'}`}>
              {intel.forecast.prediction_mode}
            </span>
          </div>
        )}

        {/* Recommended action */}
        {intel.recommended_action_input && (
          <div className="p-2 rounded border border-[#1E6FD9]/30 bg-[#1E6FD9]/5">
            <div className="flex items-center justify-between gap-2">
              <span className="flex items-center gap-1.5 text-[8.5px] font-mono font-bold text-[#1E6FD9] uppercase">
                <Send className="w-3 h-3" /> {intel.recommended_action_input.title}
              </span>
              <span className={`text-[7px] font-mono uppercase font-bold px-1.5 py-0.5 rounded border ${priorityCls[intel.recommended_action_input.priority] || priorityCls.HIGH}`}>
                {intel.recommended_action_input.priority}
              </span>
            </div>
            <p className="text-[8.5px] text-[var(--text-secondary)] mt-1">
              {intel.recommended_action_input.description}
            </p>
          </div>
        )}

        {/* Provenance */}
        <p className="text-[7px] font-mono text-[var(--text-muted)] uppercase">
          id {intel.intelligence_id} • provenance {intel.data_provenance} • {intel.detection_timestamp ? new Date(intel.detection_timestamp).toLocaleString() : '—'}
        </p>
      </div>
    </div>
  );
};

const IntelligenceWorkspace: React.FC<IntelligenceWorkspaceProps> = ({ entityType, entityId, entityLabel, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<IntelligenceReport | null>(null);

  // Guard against redundant in-flight builds (React StrictMode double-mounts
  // effects in dev, which previously fired two POST /intelligence/build calls
  // and produced duplicate history rows).
  const loadKey = React.useRef('');
  const loadInFlight = React.useRef<Promise<void> | null>(null);

  const load = async () => {
    const key = `${entityType}:${entityId}`;
    if (loadInFlight.current && loadKey.current === key) return loadInFlight.current;
    setLoading(true);
    setError(null);
    const run = (async () => {
      try {
        const data = await buildIntelligence(entityType, entityId);
        setReport(data);
      } catch (e: any) {
        setError(e?.message || 'Failed to build intelligence report');
      } finally {
        setLoading(false);
      }
    })();
    loadKey.current = key;
    loadInFlight.current = run;
    try {
      await run;
    } finally {
      if (loadKey.current === key) loadInFlight.current = null;
    }
  };

  useEffect(() => {
    load();
  }, [entityType, entityId]);

  const hasData = report && (
    report.summary ||
    (report.connections && report.connections.length > 0) ||
    (report.common_threads && report.common_threads.length > 0) ||
    (report.investigation_leads && report.investigation_leads.length > 0) ||
    (report.timeline && report.timeline.length > 0) ||
    (report.network_snapshot && report.network_snapshot.nodes && report.network_snapshot.nodes.length > 0) ||
    (report.pattern_breaks && report.pattern_breaks.length > 0) ||
    !!report.emerging_intelligence
  );

  const reportTitle = report?.entity_info?.entity_name?.trim() || entityLabel || `${entityType} ${entityId.slice(0, 8)}`;

  return (
    <div className="flex flex-col gap-3 select-none">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-2 px-3 py-2 bg-[var(--bg-tertiary)]/40 border border-[var(--border-primary)] rounded-card font-mono shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          {onClose && (
            <button
              onClick={onClose}
              className="flex items-center gap-1 px-2 py-1 rounded border border-[var(--border-primary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]/30 transition-colors cursor-pointer text-[9px] uppercase font-bold"
            >
              <ArrowLeft className="w-3 h-3" /> Back
            </button>
          )}
          <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)] truncate">
            <Brain className="w-3.5 h-3.5 text-[#a855f7]" />
            Intelligence Report for {reportTitle}
          </span>
        </div>
        <span className="text-[7.5px] text-[var(--text-muted)] uppercase shrink-0 hidden sm:block">
          Engine v2
        </span>
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center gap-3 py-14">
          <div className="w-7 h-7 border-2 border-[#a855f7]/20 border-t-[#a855f7] rounded-full animate-spin" />
          <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase tracking-wider">
            Building intelligence report...
          </span>
          <CardSkeleton className="w-full max-w-lg" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center gap-3 py-14 rounded-card border border-[#C94A2A]/30 bg-[#C94A2A]/5">
          <AlertTriangle className="w-6 h-6 text-[#C94A2A]" />
          <span className="text-[10px] font-mono text-[var(--text-secondary)] uppercase tracking-wider text-center px-6">
            {error}
          </span>
          <button
            onClick={load}
            className="px-3 py-1.5 rounded border border-[#1E6FD9]/40 text-[#1E6FD9] hover:bg-[#1E6FD9]/10 font-mono text-[9px] uppercase font-bold transition-colors cursor-pointer"
          >
            Retry
          </button>
        </div>
      ) : !report || !hasData ? (
        <div className="flex flex-col items-center justify-center gap-3 py-14 rounded-card border border-dashed border-[var(--border-primary)]">
          <Brain className="w-6 h-6 text-[var(--text-muted)]" />
          <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
            No intelligence data available for this entity
          </span>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {/* Summary (always visible) */}
          {report.summary && (
            <div className="rounded-xl border border-[#a855f7]/25 bg-[#a855f7]/5 overflow-hidden">
              <div className="px-3 py-2.5 border-b border-[var(--border-primary)]">
                <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[#a855f7]">
                  <Sparkles className="w-3.5 h-3.5" /> Intelligence Summary
                </span>
              </div>
              <p className="px-3.5 py-3 text-[10.5px] text-[var(--text-secondary)] leading-relaxed">
                {report.summary}
              </p>
            </div>
          )}

          {/* Fused Emerging Intelligence */}
          {report.emerging_intelligence && (
            <EmergingIntelligenceSection intel={report.emerging_intelligence} />
          )}

          {/* Key Connections */}
          {report.connections && report.connections.length > 0 && (
            <ExpandableSection
              title="Key Connections"
              icon={<Link2 className="w-3.5 h-3.5" />}
              count={report.connections.length}
              accent="#1E6FD9"
            >
              {report.connections.slice(0, 5).map((c, i) => (
                <div key={i} className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-[9.5px] font-mono font-bold text-[var(--text-primary)] min-w-0">
                      <span className={`shrink-0 w-3 h-3 rounded-full border ${entityTypeColor[c.entity_type] || 'text-[#D4820A] border-[#D4820A]/40'}`} />
                      <span className="truncate">{c.entity_name || c.entity_type}</span>
                    </span>
                    <ConfidenceBadge confidence={c.confidence} />
                  </div>
                  {c.entity_detail && (
                    <p className="text-[9px] text-[var(--text-secondary)]">{c.entity_detail}</p>
                  )}
                  <div className="flex items-start gap-1">
                    <Info className="w-2.5 h-2.5 shrink-0 text-[var(--text-muted)] mt-0.5" />
                    <p className="text-[8.5px] text-[var(--text-secondary)]">{c.explanation}</p>
                  </div>
                  <SourceLinks records={c.source_records} />
                </div>
              ))}
            </ExpandableSection>
          )}

          {/* Common Threads */}
          {report.common_threads && report.common_threads.length > 0 && (
            <ExpandableSection
              title="Common Threads"
              icon={<GitBranch className="w-3.5 h-3.5" />}
              count={report.common_threads.length}
              accent="#0E9E78"
            >
              {report.common_threads.map((t, i) => (
                <div key={i} className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[9.5px] font-mono font-bold text-[var(--text-primary)] uppercase">
                      {t.attribute}: <span className="text-[#0E9E78]">{t.value}</span>
                    </span>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-[8px] text-[var(--text-muted)]">×{t.case_count}</span>
                      <ConfidenceBadge confidence={t.confidence} />
                    </div>
                  </div>
                  <SourceLinks records={t.source_records} />
                </div>
              ))}
            </ExpandableSection>
          )}

          {/* Crime DNA / MO Similarity */}
          {report.crime_dna && (Object.keys(report.crime_dna.profile || {}).length > 0 || (report.crime_dna.similar_cases || []).length > 0) ? (
            <ExpandableSection
              title="Crime DNA / MO Similarity"
              icon={<Fingerprint className="w-3.5 h-3.5" />}
              count={(report.crime_dna.similar_cases || []).length}
              accent="#a855f7"
            >
              {report.crime_dna.profile && Object.keys(report.crime_dna.profile).length > 0 && (
                <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-2.5">
                  <span className="text-[8px] text-[var(--text-muted)] uppercase font-bold tracking-wider block mb-1.5">Signature Profile</span>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-3 gap-y-1.5 text-[9px]">
                    {Object.entries(report.crime_dna.profile).map(([k, v]) => (
                      <div key={k}>
                        <span className="text-[var(--text-muted)] uppercase text-[7.5px] block">{k}</span>
                        <span className="text-[var(--text-secondary)]">{v || '—'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {(report.crime_dna.similar_cases || []).map((sc, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-2.5 space-y-1.5 cursor-pointer hover:border-[#a855f7]/40 transition-colors"
                  onClick={() => navigateTo(sc.kind === 'criminal' ? 'criminal' : sc.kind === 'fir' ? 'fir' : 'case', sc.case_id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center gap-1.5 text-[9.5px] font-mono font-bold text-[var(--text-primary)]">
                      <FileText className="w-3 h-3 text-[#a855f7]" /> {sc.case_number}
                    </span>
                    <span className="text-[8px] text-[#a855f7] font-bold">
                      {Math.round((sc.similarity_score || 0) * 100)}% Match
                    </span>
                  </div>
                  {sc.matching_attributes && sc.matching_attributes.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {sc.matching_attributes.map((m, j) => (
                        <span key={j} className="text-[7.5px] text-emerald-400 font-mono">✓ {m}</span>
                      ))}
                    </div>
                  )}
                  {sc.explanation && <p className="text-[8.5px] text-[var(--text-secondary)]">{sc.explanation}</p>}
                </div>
              ))}
              {report.crime_dna.method && (
                <p className="text-[7.5px] text-[var(--text-muted)] uppercase italic">Method: {report.crime_dna.method}</p>
              )}
            </ExpandableSection>
          ) : null}

          {/* Investigation Leads */}
          {report.investigation_leads && report.investigation_leads.length > 0 && (
            <ExpandableSection
              title="Investigation Leads"
              icon={<Target className="w-3.5 h-3.5" />}
              count={report.investigation_leads.length}
              accent="#D4820A"
            >
              {report.investigation_leads
                .slice()
                .sort((a, b) => a.rank - b.rank)
                .map((l, i) => (
                  <div
                    key={i}
                    className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-2.5 space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5 text-[9.5px] font-mono font-bold text-[var(--text-primary)] min-w-0">
                        <Crosshair className="w-3 h-3 text-[#D4820A] shrink-0" />
                        <span className="text-[var(--text-muted)]">#{l.rank}</span>
                        <span className="truncate">{l.entity_name || `${l.entity_type}·${l.entity_id.slice(0, 8)}`}</span>
                      </span>
                      <span className="text-[8px] text-[#D4820A] font-bold shrink-0">
                        Relevance {Math.round((l.relevance_score || 0) * 100)}%
                      </span>
                    </div>
                    {l.entity_detail && <p className="text-[9px] text-[var(--text-secondary)]">{l.entity_detail}</p>}
                    <div className="flex items-start gap-1">
                      <Info className="w-2.5 h-2.5 shrink-0 text-[var(--text-muted)] mt-0.5" />
                      <p className="text-[8.5px] text-[var(--text-secondary)]">{l.reason}</p>
                    </div>
                    <SourceLinks records={l.source_records} />
                  </div>
                ))}
            </ExpandableSection>
          )}

          {/* Timeline */}
          {report.timeline && report.timeline.length > 0 && (
            <ExpandableSection
              title="Timeline"
              icon={<Clock className="w-3.5 h-3.5" />}
              count={report.timeline.length}
              accent="#1E6FD9"
            >
              <div className="relative pl-4 border-l border-[var(--border-primary)] space-y-3">
                {report.timeline
                  .slice()
                  .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
                  .map((ev, i) => (
                    <div key={i} className="relative">
                      <span className="absolute -left-[19px] top-1 w-2 h-2 rounded-full bg-[#1E6FD9]" />
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[9px] font-mono font-bold text-[var(--text-primary)] uppercase">
                          {ev.event}
                        </span>
                        <span className="text-[8px] text-[var(--text-muted)] shrink-0">
                          {new Date(ev.timestamp).toLocaleString('en-IN')}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 mt-1">
                        <button
                          onClick={() => navigateTo(ev.source_type, ev.source_id)}
                          className="text-[8px] text-[#1E6FD9] hover:underline font-mono cursor-pointer inline-flex items-center gap-1"
                        >
                          <FileText className="w-2.5 h-2.5" /> {ev.source_label || `${ev.source_type}·${ev.source_id.slice(0, 8)}`}
                          <ExternalLink className="w-2 h-2" />
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            </ExpandableSection>
          )}

          {/* Pattern Breaks */}
          {report.pattern_breaks && report.pattern_breaks.length > 0 && (
            <ExpandableSection
              title="Pattern Breaks"
              icon={<Activity className="w-3.5 h-3.5" />}
              count={report.pattern_breaks.length}
              accent="#C94A2A"
            >
              {report.pattern_breaks.map((p, i) => (
                <div key={i} className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-2.5 space-y-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[9.5px] font-mono font-bold text-[var(--text-primary)] uppercase">
                      <AlertTriangle className="w-3 h-3 text-[#C94A2A] inline mr-1" /> {p.pattern_type}
                    </span>
                    <ConfidenceBadge confidence={p.confidence} />
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[8.5px]">
                    <div className="p-1.5 bg-[var(--bg-tertiary)]/40 rounded border border-[var(--border-primary)]">
                      <span className="text-[7.5px] text-[var(--text-muted)] uppercase block">Baseline</span>
                      <span className="text-[var(--text-secondary)]">{p.baseline}</span>
                    </div>
                    <div className="p-1.5 bg-[#C94A2A]/5 rounded border border-[#C94A2A]/20">
                      <span className="text-[7.5px] text-[#C94A2A] uppercase block">Deviation</span>
                      <span className="text-[var(--text-secondary)]">{p.deviation}</span>
                    </div>
                  </div>
                  <SourceLinks records={p.supporting_records} />
                </div>
              ))}
            </ExpandableSection>
          )}

          {/* Network Snapshot */}
          {report.network_snapshot && report.network_snapshot.nodes && report.network_snapshot.nodes.length > 0 && (
            <ExpandableSection
              title="Network Snapshot"
              icon={<Network className="w-3.5 h-3.5" />}
              count={report.network_snapshot.nodes.length}
              accent="#0E9E78"
            >
              <NetworkSnapshot snapshot={report.network_snapshot} />
            </ExpandableSection>
          )}

          {/* Confidence & Explainability Footer */}
          {(report.confidence_summary || report.explainability) && (
            <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/35 overflow-hidden">
              <div className="px-3 py-2.5 border-b border-[var(--border-primary)] flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">
                  <BarChart3 className="w-3.5 h-3.5 text-[#a855f7]" /> Confidence &amp; Explainability
                </span>
                <span className="flex items-center gap-1 text-[7.5px] text-[var(--text-muted)] uppercase">
                  <ShieldCheck className="w-2.5 h-2.5" /> {report.confidence_summary?.confirmed || 0} confirmed
                </span>
              </div>
              <div className="px-3.5 py-3 space-y-2.5">
                {report.confidence_summary && (
                  <div className="grid grid-cols-4 gap-2 text-center font-mono">
                    {(['confirmed', 'probable', 'possible', 'insufficient'] as ConfidenceLevel[]).map((lvl) => (
                      <div key={lvl} className={`p-1.5 rounded border ${confidenceStyles[lvl].cls}`}>
                        <span className="block text-[11px] font-bold">
                          {report.confidence_summary![lvl] ?? 0}
                        </span>
                        <span className="text-[7px] uppercase tracking-wider">{lvl}</span>
                      </div>
                    ))}
                  </div>
                )}
                {report.explainability && (
                  <>
                    {report.explainability.method && (
                      <div>
                        <span className="text-[7.5px] text-[var(--text-muted)] uppercase font-bold tracking-wider">Method</span>
                        <p className="text-[9px] text-[var(--text-secondary)]">{report.explainability.method}</p>
                      </div>
                    )}
                    {report.explainability.data_sources && report.explainability.data_sources.length > 0 && (
                      <div>
                        <span className="text-[7.5px] text-[var(--text-muted)] uppercase font-bold tracking-wider">Data Sources</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {report.explainability.data_sources.map((d, i) => (
                            <span key={i} className="text-[7.5px] bg-[var(--bg-elevated)]/30 border border-[var(--border-primary)] text-[var(--text-muted)] px-1.5 py-0.5 rounded font-mono uppercase">
                              {d}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {report.explainability.limitations && report.explainability.limitations.length > 0 && (
                      <div className="pt-1 border-t border-[var(--border-primary)]">
                        <span className="flex items-center gap-1 text-[7.5px] text-amber-400/80 uppercase font-bold tracking-wider">
                          <Info className="w-2.5 h-2.5" /> Limitations
                        </span>
                        <ul className="list-disc pl-4 text-[8px] text-[var(--text-secondary)] mt-1 space-y-0.5">
                          {report.explainability.limitations.map((l, i) => (
                            <li key={i}>{l}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default IntelligenceWorkspace;
export { IntelligenceWorkspace };
