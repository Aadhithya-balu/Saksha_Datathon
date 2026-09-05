import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Database,
  FileText,
  Gavel,
  Layers,
  Link2,
  Loader2,
  Lock,
  MapPin,
  Radar,
  Search,
  ShieldAlert,
  Siren,
  X,
} from 'lucide-react';
import {
  investigateIntelligencePattern,
  type IntelligenceInvestigationFIR,
  type IntelligenceInvestigationResponse,
  type UnifiedIntelligenceResult,
  type VerificationState,
} from '../../services/api';

/* ------------------------------------------------------------------ */
/* Provenance visual language (issue #250)                            */
/*   VERIFIED = solid / emerald · POTENTIAL = dashed / amber           */
/*   DEMO = dotted / purple · RESTRICTED = lock / coral                */
/* ------------------------------------------------------------------ */

const STATE_META: Record<VerificationState, { label: string; text: string; chip: string; icon: React.ReactNode }> = {
  VERIFIED: {
    label: 'Verified',
    text: 'text-emerald-400',
    chip: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
    icon: <CheckCircle2 className="w-2.5 h-2.5" />,
  },
  POTENTIAL: {
    label: 'Potential',
    text: 'text-amber-400',
    chip: 'border-dashed border-amber-500/40 bg-amber-500/10 text-amber-400',
    icon: <Layers className="w-2.5 h-2.5" />,
  },
  DEMO: {
    label: 'Demo',
    text: 'text-[#a855f7]',
    chip: 'border-[#a855f7]/40 bg-[#a855f7]/10 text-[#a855f7]',
    icon: <Database className="w-2.5 h-2.5" />,
  },
  RESTRICTED: {
    label: 'Restricted',
    text: 'text-[#C94A2A]',
    chip: 'border-[#C94A2A]/50 bg-[#C94A2A]/10 text-[#C94A2A]',
    icon: <Lock className="w-2.5 h-2.5" />,
  },
  UNVERIFIED: {
    label: 'Unverified',
    text: 'text-[var(--text-muted)]',
    chip: 'border-[var(--border-primary)] bg-[var(--bg-tertiary)] text-[var(--text-muted)]',
    icon: <AlertTriangle className="w-2.5 h-2.5" />,
  },
};

const stateMeta = (s?: string | VerificationState): typeof STATE_META.VERIFIED =>
  STATE_META[(s as VerificationState) || 'UNVERIFIED'] || STATE_META.UNVERIFIED;

const NODE_COLORS: Record<string, string> = {
  criminal: '#C94A2A',
  offender: '#C94A2A',
  suspect: '#E11D48',
  case: '#0E9E78',
  location: '#1E6FD9',
  victim: '#6A7A96',
  officer: '#14C997',
  gang: '#6C43CC',
  vehicle: '#D4820A',
  weapon: '#C0A16B',
};

const EDGE_STYLES: Record<VerificationState, { stroke: string; dash: string }> = {
  VERIFIED: { stroke: '#0E9E78', dash: '' },
  POTENTIAL: { stroke: '#F59E0B', dash: '7 5' },
  DEMO: { stroke: '#A855F7', dash: '2 4' },
  RESTRICTED: { stroke: '#C94A2A', dash: '9 3 2 3' },
  UNVERIFIED: { stroke: '#64748B', dash: '3 4' },
};

const SectionLabel: React.FC<{ icon: React.ReactNode; title: string; note?: string }> = ({ icon, title, note }) => (
  <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-elevated)]/40">
    <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">
      {icon}
      {title}
    </span>
    {note && <span className="text-[7px] font-mono text-[var(--text-muted)]">{note}</span>}
  </div>
);

const VerificationBadge: React.FC<{ state?: string | VerificationState; size?: 'sm' | 'md' }> = ({ state, size = 'sm' }) => {
  const meta = stateMeta(state);
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border font-mono uppercase font-bold ${
        size === 'md' ? 'px-1.5 py-0.5 text-[7.5px]' : 'px-1 py-0.5 text-[6.5px]'
      } ${meta.chip}`}
    >
      {meta.icon}
      {meta.label}
    </span>
  );
};

const EmptyHint: React.FC<{ icon: React.ReactNode; text: string; sub?: string }> = ({ icon, text, sub }) => (
  <div className="p-5 text-center">
    <div className="w-6 h-6 mx-auto mb-1.5 text-[var(--text-muted)] flex items-center justify-center">{icon}</div>
    <p className="text-[8.5px] font-mono text-[var(--text-muted)] uppercase tracking-wider">{text}</p>
    {sub && <p className="text-[7.5px] text-[var(--text-muted)] mt-1">{sub}</p>}
  </div>
);

/* ------------------------------------------------------------------ */
/* Lightweight SVG network graph (no 3D dependency in the drawer)      */
/* ------------------------------------------------------------------ */

const NetworkGraph: React.FC<{
  nodes: Array<{ id: string; name: string; category: string; verification_status?: string; isSeed?: boolean }>;
  edges: Array<{
    source: string; target: string; relationship: string;
    verification_status?: string; provenance?: string; operational_warning?: string | null;
  }>;
  onSelectNode: (nodeId: string) => void;
}> = ({ nodes, edges, onSelectNode }) => {
  const W = 640;
  const H = 400;
  const CX = W / 2;
  const CY = H / 2;

  const pos = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    if (!nodes.length) return map;
    const radiusX = 225;
    const radiusY = 145;
    nodes.forEach((n, i) => {
      const angle = (-Math.PI / 2) + (i / nodes.length) * Math.PI * 2;
      map.set(n.id, {
        x: CX + radiusX * Math.cos(angle),
        y: CY + radiusY * Math.sin(angle),
      });
    });
    return map;
  }, [nodes, CX, CY]);

  const orderedEdges = useMemo(
    () =>
      [...edges].sort((a, b) => {
        const order: Record<string, number> = { VERIFIED: 3, POTENTIAL: 2, DEMO: 1, RESTRICTED: 4, UNVERIFIED: 0 };
        return (order[(b.verification_status as VerificationState) || 'UNVERIFIED'] || 0) -
               (order[(a.verification_status as VerificationState) || 'UNVERIFIED'] || 0);
      }),
    [edges]
  );

  const resolveNode = (id: string) => {
    const n = nodes.find((x) => x.id === id);
    return n ? { ...pos.get(id), name: n.name } : null;
  };

  return (
    <div className="p-2">
      {nodes.length === 0 ? (
        <EmptyHint icon={<Link2 className="w-4 h-4" />} text="No network available" />
      ) : (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none" role="img" aria-label="Investigation network graph">
          {orderedEdges.map((e, i) => {
            const a = resolveNode(e.source);
            const b = resolveNode(e.target);
            if (!a || !b) return null;
            const style = EDGE_STYLES[(e.verification_status as VerificationState) || 'UNVERIFIED'] || EDGE_STYLES.UNVERIFIED;
            const midX = (a.x + b.x) / 2;
            const midY = (a.y + b.y) / 2;
            return (
              <g key={`e-${i}`}>
                <line
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke={style.stroke}
                  strokeWidth={e.verification_status === 'VERIFIED' ? 1.8 : 1.3}
                  strokeDasharray={style.dash}
                  strokeOpacity={0.85}
                >
                  <title>{`${a.name} ↔ ${b.name}: ${e.relationship} · ${(e.verification_status || 'UNVERIFIED').replace(/_/g, ' ').toLowerCase()}${e.operational_warning ? ' — ' + e.operational_warning : ''}`}</title>
                </line>
                {e.verification_status === 'RESTRICTED' && (
                  <g transform={`translate(${midX - 4}, ${midY - 4})`}>
                    <rect width="8" height="8" rx="1.5" fill="#C94A2A" opacity="0.9">
                      <title>Restricted analytical edge</title>
                    </rect>
                    <rect x="2" y="1.5" width="4" height="2.5" rx="0.75" fill="none" stroke="#FFF" strokeWidth="0.9" />
                    <rect x="1" y="4" width="6" height="3.5" rx="0.75" fill="#FFF" opacity="0.95" />
                  </g>
                )}
              </g>
            );
          })}
          {nodes.map((n) => {
            const p = pos.get(n.id);
            if (!p) return null;
            const isRestricted = n.verification_status === 'RESTRICTED';
            const fill = NODE_COLORS[n.category] || '#6C43CC';
            return (
              <g
                key={n.id}
                transform={`translate(${p.x}, ${p.y})`}
                className="cursor-pointer"
                onClick={() => onSelectNode(n.id)}
              >
                <circle r={7.5} fill={fill} opacity={n.isSeed ? 0.75 : 0.95} stroke="#0B1120" strokeWidth={1.5}>
                  <title>{n.name}</title>
                </circle>
                {isRestricted && (
                  <>
                    <rect x={-2.75} y={-3.25} width={5.5} height={4} rx={1} fill="#0B1120" />
                    <rect x={-3.75} y={-6.5} width={7.5} height={4} rx={1} fill="#C94A2A" stroke="#0B1120" strokeWidth={0.75}>
                      <title>Restricted record</title>
                    </rect>
                  </>
                )}
                <text
                  y={17}
                  textAnchor="middle"
                  fontSize={7}
                  fontFamily="JetBrains Mono, monospace"
                  fill="#94A3B8"
                >
                  {n.name.length > 22 ? `${n.name.slice(0, 21)}…` : n.name}
                </text>
              </g>
            );
          })}
        </svg>
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/* Main drawer                                                        */
/* ------------------------------------------------------------------ */

interface IntelligenceInvestigationDrawerProps {
  open: boolean;
  pattern: UnifiedIntelligenceResult | null;
  onClose: () => void;
}

const IntelligenceInvestigationDrawer: React.FC<IntelligenceInvestigationDrawerProps> = ({ open, pattern, onClose }) => {
  const [view, setView] = useState<IntelligenceInvestigationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [showWhy, setShowWhy] = useState(true);

  useEffect(() => {
    if (!open || !pattern) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setView(null);
    setSelectedCaseId(null);
    investigateIntelligencePattern(pattern.intelligence_id, pattern)
      .then((res) => {
        if (cancelled) return;
        setView(res);
        if (res.cases && res.cases.length) setSelectedCaseId(res.cases[0].id);
      })
      .catch((e: any) => {
        if (!cancelled) setError(e?.message || 'Failed to compose investigation view');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, pattern]);

  const selectedFIR = useMemo<IntelligenceInvestigationFIR | null>(() => {
    if (!view || !selectedCaseId) return null;
    return view.firs.find((f) => f.case_id === selectedCaseId || f.id === selectedCaseId) || null;
  }, [view, selectedCaseId]);

  const selectedEvidence = useMemo(() => {
    if (!view || !selectedCaseId) return [];
    return view.evidence.filter((e) => e.case_id === selectedCaseId);
  }, [view, selectedCaseId]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[1200] flex items-stretch justify-center p-1 sm:p-3 md:p-5 bg-black/70 backdrop-blur-sm">
      <div className="relative w-full max-w-[1300px] h-full flex flex-col rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)] overflow-hidden shadow-2xl">
        {/* ── Investigation Header ─────────────────────────────────── */}
        <div className="shrink-0 border-b border-[var(--border-primary)] bg-gradient-to-r from-[#0B1120] to-[#1A0F1F] px-3 py-2.5 sm:px-4 flex items-center gap-3">
          <span className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border border-[#C94A2A]/40 bg-[#C94A2A]/10 text-[#C94A2A]">
            <Gavel className="w-4 h-4" />
          </span>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <h3 className="text-[11px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)] truncate">
                Pattern Investigation · {pattern?.pattern_type || view?.pattern_type || '—'}
              </h3>
              {view && (
                <VerificationBadge state="VERIFIED" size="md" />
              )}
            </div>
            <p className="flex items-center gap-2 text-[8px] font-mono text-[var(--text-muted)] mt-0.5 truncate">
              <span className="flex items-center gap-0.5">
                <MapPin className="w-2.5 h-2.5" />
                {pattern?.location?.district || view?.location?.district || '—'}
              </span>
              <span>·</span>
              <span>risk {Math.round((pattern?.risk_score ?? view?.risk_score ?? 0) * 100)}%</span>
              <span>·</span>
              <span>conf {Math.round((pattern?.confidence ?? view?.confidence ?? 0) * 100)}%</span>
              {view?.generated_at && (
                <>
                  <span>·</span>
                  <span>{new Date(view.generated_at).toLocaleString()}</span>
                </>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)] transition-colors cursor-pointer shrink-0"
            title="Close investigation"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── Body ─────────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {loading ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-16">
              <Loader2 className="w-6 h-6 animate-spin text-[#D4820A] mb-2" />
              <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase">Composing investigation view…</span>
            </div>
          ) : error ? (
            <div className="h-full flex flex-col items-center justify-center text-center py-16 px-6">
              <ShieldAlert className="w-6 h-6 text-[#C94A2A] mb-2" />
              <p className="text-[9.5px] font-mono text-[var(--text-secondary)] max-w-sm">{error}</p>
            </div>
          ) : !view ? (
            <EmptyHint icon={<Radar className="w-5 h-5" />} text="Select a pattern to investigate" />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 p-3">
              {/* ── Left main column ─────────────────────────────── */}
              <div className="lg:col-span-7 space-y-3">
                {/* Related FIRs */}
                <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
                  <SectionLabel
                    icon={<FileText className="w-3 h-3 text-[#0E9E78]" />}
                    title="Related FIRs"
                    note={`${view.firs.length} resolved from intelligence`}
                  />
                  {view.firs.length === 0 ? (
                    <EmptyHint icon={<FileText className="w-4 h-4" />} text="No resolvable FIR references" />
                  ) : (
                    <div className="divide-y divide-[var(--border-primary)/50] max-h-[260px] overflow-y-auto custom-scrollbar">
                      {view.firs.map((fir) => (
                        <button
                          key={fir.id}
                          onClick={() => setSelectedCaseId(fir.case_id || fir.id)}
                          className={`w-full text-left px-3 py-2 transition-colors cursor-pointer flex items-start gap-2 ${
                            selectedCaseId === (fir.case_id || fir.id)
                              ? 'bg-[#1E6FD9]/10 border-l-2 border-l-[#1E6FD9]'
                              : 'hover:bg-[var(--bg-elevated)]/50'
                          }`}
                        >
                          <span className="mt-0.5 shrink-0 flex items-center justify-center w-6 h-6 rounded border border-[#0E9E78]/40 bg-[#0E9E78]/10 text-[#0E9E78]">
                            <FileText className="w-3 h-3" />
                          </span>
                          <span className="flex-1 min-w-0">
                            <span className="flex flex-wrap items-center gap-1.5">
                              <span className="text-[9.5px] font-semibold text-[var(--text-primary)]">FIR {fir.fir_number}</span>
                              <VerificationBadge state={fir.verification_status} />
                            </span>
                            <span className="block text-[7.5px] font-mono text-[var(--text-muted)] mt-0.5">
                              {fir.complainant_name} · {fir.sections || 'IPC'} · {fir.status}
                            </span>
                            <span className="block text-[7.5px] text-[var(--text-secondary)] mt-0.5 truncate">
                              {fir.narrative || fir.case_number || '—'}
                            </span>
                            {fir.evidence_count > 0 && (
                              <span className="block text-[6.5px] font-mono text-[#1E6FD9] mt-0.5 uppercase">
                                {fir.evidence_count} evidence item{fir.evidence_count === 1 ? '' : 's'} →
                              </span>
                            )}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* MO & Pattern Matches */}
                <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
                  <SectionLabel
                    icon={<Search className="w-3 h-3 text-amber-400" />}
                    title="MO / Pattern Matches"
                    note={view.mo_matches?.method || undefined}
                  />
                  <div className="p-3 space-y-2.5">
                    {view.mo_matches?.shared_tags?.length ? (
                      <div>
                        <span className="text-[7px] font-mono uppercase text-[var(--text-muted)]">Shared modus operandi tags</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {view.mo_matches.shared_tags.map((t) => (
                            <span key={t} className="px-1.5 py-0.5 rounded border border-amber-500/30 bg-amber-500/5 text-amber-300 text-[7px] font-mono uppercase">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null}

                    {view.mo_matches?.suspects?.length ? (
                      <div>
                        <span className="text-[7px] font-mono uppercase text-[var(--text-muted)]">Linked suspects</span>
                        <div className="mt-1 space-y-1">
                          {view.mo_matches.suspects.slice(0, 5).map((s) => (
                            <div key={s.criminal_id || s.full_name} className="flex items-center gap-2 p-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/40">
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[8.5px] font-semibold text-[var(--text-primary)] truncate">{s.full_name}</span>
                                  <VerificationBadge state={s.verification_status} />
                                </div>
                                <div className="flex items-center gap-1.5 mt-1">
                                  <div className="w-16 h-1 rounded bg-[var(--bg-primary)] overflow-hidden">
                                    <div className="h-full rounded" style={{ width: `${s.similarity_percent}%`, background: s.similarity_percent >= 50 ? '#F59E0B' : '#D4820A' }} />
                                  </div>
                                  <span className="text-[6.5px] font-mono text-[var(--text-muted)]">{s.similarity_percent}% · {s.match_level || 'match'}</span>
                                </div>
                              </div>
                              <span className="text-[6.5px] font-mono text-[var(--text-muted)] shrink-0 max-w-[90px] truncate">
                                {s.relationship_label || (s.is_confirmed_relationship ? 'Confirmed FIR accused' : 'Analytical MO lead')}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p className="text-[8px] text-[var(--text-secondary)]">No MO similarity leads found among the resolved entities.</p>
                    )}

                    {view.mo_matches?.matching_cases?.length ? (
                      <div>
                        <span className="text-[7px] font-mono uppercase text-[var(--text-muted)]">Similar related cases</span>
                        <div className="mt-1 space-y-1">
                          {view.mo_matches.matching_cases.slice(0, 5).map((c) => (
                            <div key={c.case_id || c.case_number} className="flex items-center gap-2 p-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/40">
                              <span className="text-[8.5px] font-semibold text-[var(--text-primary)]">{c.case_number}</span>
                              <VerificationBadge state={c.verification_status} />
                              <span className="ml-auto text-[6.5px] font-mono text-[var(--text-muted)]">{c.similarity_percent}% MO similarity</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                </div>

                {/* Network */}
                <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
                  <SectionLabel
                    icon={<Link2 className="w-3 h-3 text-[#6C43CC]" />}
                    title="Network Relationship Graph"
                    note={`${view.network?.nodes?.length || 0} nodes · ${view.network?.edges?.length || 0} edges`}
                  />
                  <NetworkGraph
                    nodes={view.network?.nodes || []}
                    edges={view.network?.edges || []}
                    onSelectNode={(nodeId) => {
                      if (nodeId.startsWith('case-')) {
                        const fir = view.firs.find((f) => `case-${f.id}` === nodeId);
                        if (fir) setSelectedCaseId(fir.case_id || fir.id);
                      }
                    }}
                  />
                  <div className="px-3 py-2 border-t border-[var(--border-primary)]/50">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                      {(['VERIFIED', 'POTENTIAL', 'DEMO', 'RESTRICTED'] as VerificationState[]).map((s) => {
                        const meta = stateMeta(s);
                        const style = EDGE_STYLES[s];
                        return (
                          <span key={s} className="inline-flex items-center gap-1 text-[6.5px] font-mono text-[var(--text-muted)] uppercase">
                            <svg width="18" height="6" className="inline-block">
                              <line x1="0" y1="3" x2="18" y2="3" stroke={style.stroke} strokeDasharray={style.dash} strokeWidth="2" />
                            </svg>
                            {meta.label}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Right column: Evidence Drawer + Why This Insight? ── */}
              <div className="lg:col-span-5 space-y-3">
                {/* Evidence Drawer */}
                <div className="rounded-lg border border-[#1E6FD9]/30 bg-[#1E6FD9]/5 overflow-hidden">
                  <SectionLabel
                    icon={<FileText className="w-3 h-3 text-[#1E6FD9]" />}
                    title="Evidence Drawer"
                    note={selectedFIR ? `FIR ${selectedFIR.fir_number}` : 'select a related FIR / case node'}
                  />
                  <div className="max-h-[300px] overflow-y-auto custom-scrollbar">
                    {!selectedFIR ? (
                      <EmptyHint
                        icon={<Gavel className="w-4 h-4" />}
                        text="Select a related FIR or case node"
                        sub="Evidence from the matched case is listed here"
                      />
                    ) : selectedEvidence.length === 0 ? (
                      <EmptyHint icon={<FileText className="w-4 h-4" />} text={`No evidence filed for FIR ${selectedFIR.fir_number}`} />
                    ) : (
                      <div className="divide-y divide-[var(--border-primary)/50]">
                        {selectedEvidence.map((ev) => {
                          return (
                            <div key={ev.id} className="px-3 py-2">
                              <div className="flex items-start gap-2">
                                <span className="mt-0.5 shrink-0 flex items-center justify-center w-6 h-6 rounded border border-[#1E6FD9]/40 bg-[#1E6FD9]/10 text-[#1E6FD9]">
                                  <FileText className="w-3 h-3" />
                                </span>
                                <div className="flex-1 min-w-0">
                                  <div className="flex flex-wrap items-center gap-1.5">
                                    <span className="text-[9px] font-semibold text-[var(--text-primary)]">{ev.title}</span>
                                    <VerificationBadge state={ev.verification_status} />
                                    {ev.is_restricted && !ev.masked && view.access?.has_restricted_access ? (
                                      <span className="px-1 py-0.5 rounded border border-[#C94A2A]/40 text-[#C94A2A] text-[6.5px] font-mono uppercase">
                                        <Lock className="w-2 h-2 inline-block mr-0.5" /> reviewer access
                                      </span>
                                    ) : null}
                                  </div>
                                  {ev.description && (
                                    <p className={`text-[8px] leading-relaxed mt-0.5 ${ev.masked ? 'text-[#C94A2A] font-mono uppercase' : 'text-[var(--text-secondary)]'}`}>
                                      {ev.description}
                                    </p>
                                  )}
                                  <p className="text-[6.5px] font-mono text-[var(--text-muted)] mt-0.5 uppercase">
                                    {ev.evidence_type} · {ev.status} · {ev.case_number || ev.fir_number || ''}
                                  </p>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {/* Why This Insight? */}
                <div className="rounded-lg border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
                  <button
                    onClick={() => setShowWhy((s) => !s)}
                    className="w-full flex items-center justify-between px-3 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-elevated)]/40 cursor-pointer"
                  >
                    <span className="flex items-center gap-1.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[#D4820A]">
                      <Radar className="w-3 h-3" /> Why This Insight?
                    </span>
                    <ChevronDown className={`w-3 h-3 text-[var(--text-muted)] transition-transform ${showWhy ? 'rotate-180' : ''}`} />
                  </button>
                  {showWhy && (
                    <div className="p-3 space-y-2.5 max-h-[340px] overflow-y-auto custom-scrollbar">
                      <p className="text-[8.5px] leading-relaxed text-[var(--text-secondary)] bg-[var(--bg-tertiary)]/40 p-2 rounded border border-[var(--border-primary)]">
                        {view.why_this_insight?.summary}
                      </p>

                      {view.why_this_insight?.signals?.length ? (
                        <div>
                          <span className="text-[7px] font-mono uppercase text-[var(--text-muted)]">Corroborating signals</span>
                          <div className="mt-1 space-y-1">
                            {view.why_this_insight.signals.map((s, i) => {
                              const statusColor =
                                s.status === 'CONFIRMED' ? 'text-emerald-400 border-emerald-500/40'
                                : s.status === 'PROBABLE' ? 'text-amber-400 border-amber-500/40'
                                : s.status === 'POSSIBLE' ? 'text-[#D4820A] border-[#D4820A]/40'
                                : 'text-[var(--text-muted)] border-[var(--border-primary)]';
                              return (
                                <div key={i} className="flex items-start gap-2 p-1.5 rounded border border-[var(--border-primary)] bg-[var(--bg-tertiary)]/30">
                                  <span className={`mt-0.5 shrink-0 px-1 py-0.5 rounded border text-[6px] font-mono uppercase font-bold ${statusColor}`}>{s.status}</span>
                                  <div className="min-w-0">
                                    <span className="block text-[7.5px] font-mono uppercase text-[var(--text-primary)]">{s.signal_type.replace(/_/g, ' ')}</span>
                                    <span className="block text-[7.5px] text-[var(--text-secondary)] leading-relaxed mt-0.5">{s.description}</span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ) : null}

                      <div>
                        <span className="text-[7px] font-mono uppercase text-[var(--text-muted)]">Methodology</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {view.why_this_insight?.methodology && (
                            <>
                              <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[6.5px] font-mono text-[var(--text-secondary)] uppercase">
                                {view.why_this_insight.methodology.ml_status}
                              </span>
                              <span className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[6.5px] font-mono text-[var(--text-secondary)] uppercase">
                                {view.why_this_insight.methodology.model_name} v{view.why_this_insight.methodology.model_version}
                              </span>
                              {Object.entries(view.why_this_insight.methodology.analytics_available || {}).map(([k, v]) => (
                                <span key={k} className="px-1.5 py-0.5 rounded border border-[var(--border-primary)] text-[6.5px] font-mono text-[var(--text-muted)] uppercase">
                                  {k}: {v.toLowerCase()}
                                </span>
                              ))}
                            </>
                          )}
                        </div>
                      </div>

                      <div>
                        <span className="text-[7px] font-mono uppercase text-[var(--text-muted)]">Data sources</span>
                        <ul className="mt-1 space-y-0.5">
                          {(view.why_this_insight?.data_sources || []).map((d, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-[7.5px] text-[var(--text-secondary)]">
                              <span className="mt-1 shrink-0 w-1 h-1 rounded-full bg-[#D4820A]" />
                              {d}
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <span className="text-[7px] font-mono uppercase text-[var(--text-muted)]">Limitations</span>
                        <ul className="mt-1 space-y-0.5">
                          {(view.why_this_insight?.limitations || []).map((d, i) => (
                            <li key={i} className="flex items-start gap-1.5 text-[7.5px] text-[var(--text-secondary)]">
                              <span className="mt-1 shrink-0 w-1 h-1 rounded-full bg-[var(--text-muted)]" />
                              {d}
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="flex items-start gap-2 p-2 rounded border border-amber-500/40 bg-amber-500/5">
                        <AlertTriangle className="w-3 h-3 text-amber-400 shrink-0 mt-0.5" />
                        <p className="text-[7.5px] text-amber-200/90 leading-relaxed">
                          {view.why_this_insight?.safety_note}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer: summary + safety ─────────────────────────────── */}
        {view && !loading && !error && (
          <div className="shrink-0 border-t border-[var(--border-primary)] bg-[var(--bg-elevated)]/40 px-3 py-2 flex flex-col lg:flex-row items-start lg:items-center gap-2">
            <div className="flex flex-wrap items-center gap-1.5">
              {Object.entries(view.verification_summary || {}).map(([state, count]) => (
                <span key={state} className="inline-flex items-center gap-1 text-[6.5px] font-mono text-[var(--text-muted)] uppercase">
                  <VerificationBadge state={state} />
                  {String(count)}
                </span>
              ))}
            </div>
            <span className="lg:ml-auto flex items-center gap-1 text-[6.5px] font-mono text-[var(--text-muted)]">
              <Siren className="w-2.5 h-2.5 text-amber-400" />
              Analytical relationships are investigative leads, not confirmed guilt or evidence.
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default IntelligenceInvestigationDrawer;