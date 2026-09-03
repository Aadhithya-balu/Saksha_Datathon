import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Fingerprint,
  FileWarning,
  Network,
  RefreshCcw,
  Loader2,
  Search,
  ShieldCheck,
  ShieldAlert,
  Link2,
  Eye,
  Check,
  X,
  Flag,
  Info,
} from 'lucide-react';
import { PageSkeleton } from '../../components/ui/Skeleton';
import { useRBAC } from '../../hooks/useRBAC';
import {
  getIdentityDashboard,
  getIdentityGraph,
  listIdentityRelationships,
  listIdentityAlerts,
  listProxyPatterns,
  reviewIdentityRelationship,
  reviewIdentityAlert,
  reviewProxyPattern,
  runIdentityResolution,
  runProxyDetection,
  searchIdentity,
  type IdentityDashboardResponse,
  type IdentityRelationship,
  type IntegrityAlertRecord,
  type ProxyPatternRecord,
  type IdentityGraphResponse,
  type IdentitySearchResponse,
} from '../../services/api';

type Tab = 'review' | 'proxy' | 'alerts' | 'graph' | 'search';

const ASSESSMENT_META: Record<string, { label: string; cls: string }> = {
  PROBABLE_IDENTITY_MATCH: { label: 'Probable Duplicate', cls: 'text-[var(--accent-coral)] border-[var(--accent-coral)]/40 bg-[var(--accent-coral)]/10' },
  POSSIBLE_IDENTITY_MATCH: { label: 'Possible Duplicate', cls: 'text-[var(--accent-amber)] border-[var(--accent-amber)]/40 bg-[var(--accent-amber)]/10' },
  POSSIBLE_ASSOCIATED: { label: 'Association', cls: 'text-[var(--text-secondary)] border-[var(--border-secondary)] bg-[var(--bg-tertiary)]' },
  POSSIBLE_PROXY: { label: 'Proxy Pattern', cls: 'text-[var(--accent-purple)] border-[var(--accent-purple)]/40 bg-[var(--accent-purple)]/10' },
};

const SEVERITY_CLS: Record<string, string> = {
  critical: 'text-[var(--accent-coral)] border-[var(--accent-coral)]/40 bg-[var(--accent-coral)]/10',
  high: 'text-[var(--accent-amber)] border-[var(--accent-amber)]/40 bg-[var(--accent-amber)]/10',
  medium: 'text-[var(--accent-blue)] border-[var(--accent-blue)]/40 bg-[var(--accent-blue)]/10',
  low: 'text-[var(--text-secondary)] border-[var(--border-secondary)] bg-[var(--bg-tertiary)]',
};

function StatCard({ label, value, tone = 'blue', icon }: { label: string; value: number | string; tone?: 'blue' | 'coral' | 'amber' | 'purple' | 'teal'; icon: React.ReactNode }) {
  const tones: Record<string, string> = {
    blue: 'text-[var(--accent-blue)]',
    coral: 'text-[var(--accent-coral)]',
    amber: 'text-[var(--accent-amber)]',
    purple: 'text-[var(--accent-purple)]',
    teal: 'text-[var(--accent-teal)]',
  };
  return (
    <div className="sk-card p-4 flex items-center gap-3">
      <div className={`w-10 h-10 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-primary)] flex items-center justify-center shrink-0 ${tones[tone]}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)] truncate">{label}</div>
        <div className="text-xl font-bold text-[var(--text-primary)] font-mono leading-tight">{value}</div>
      </div>
    </div>
  );
}

function Badge({ text, cls }: { text: string; cls: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono uppercase tracking-wide border ${cls}`}>
      {text}
    </span>
  );
}

export const IdentityResolution: React.FC = () => {
  const [tab, setTab] = useState<Tab>('review');
  const [dash, setDash] = useState<IdentityDashboardResponse | null>(null);
  const [relationships, setRelationships] = useState<IdentityRelationship[]>([]);
  const [alerts, setAlerts] = useState<IntegrityAlertRecord[]>([]);
  const [proxies, setProxies] = useState<ProxyPatternRecord[]>([]);
  const [graph, setGraph] = useState<IdentityGraphResponse | null>(null);
  const [search, setSearch] = useState<IdentitySearchResponse | null>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [audibleMsg, setAudibleMsg] = useState<string | null>(null);
  const { isAdmin, isSCRB, isIO, isInspector } = useRBAC();

  const canReview = isAdmin || isSCRB || isIO || isInspector;

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const results = await Promise.all([
        getIdentityDashboard(),
        listIdentityRelationships({ limit: 100 }).catch(() => ({ total: null, results: [] as IdentityRelationship[] })),
        listIdentityAlerts({ limit: 100 }).catch(() => ({ total: null, results: [] as IntegrityAlertRecord[] })),
        listProxyPatterns({ limit: 100 }).catch(() => ({ total: null, results: [] as ProxyPatternRecord[] })),
        getIdentityGraph().catch(() => ({ nodes: [], edges: [] })),
      ]);
      const [d, rels, al, prx, gr] = results;
      setDash(d);
      setRelationships(rels.results);
      setAlerts(al.results);
      setProxies(prx.results);
      setGraph(gr);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Failed to load identity data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  const doRun = async () => {
    setBusy(true);
    setAudibleMsg(null);
    try {
      const summary = await runIdentityResolution();
      setAudibleMsg(`Resolution complete: ${summary.relationships_proposed} proposed, ${summary.proxy_patterns_detected} proxy pattern(s), ${summary.identifier_reuse_alerts} reuse alert(s).`);
    } catch (error) {
      setAudibleMsg(error instanceof Error ? error.message : 'Resolution run failed');
    } finally {
      setBusy(false);
      void fetchAll();
    }
  };

  const doRunProxy = async () => {
    setBusy(true);
    setAudibleMsg(null);
    try {
      const result = await runProxyDetection();
      setAudibleMsg(`Proxy scan complete: ${result.patterns_detected} pattern(s) detected.`);
    } catch (error) {
      setAudibleMsg(error instanceof Error ? error.message : 'Proxy scan failed');
    } finally {
      setBusy(false);
      void fetchAll();
    }
  };

  const doReview = async (fn: () => Promise<unknown>, msg: string) => {
    setBusy(true);
    setAudibleMsg(null);
    try {
      await fn();
      setAudibleMsg(msg);
    } catch (error) {
      setAudibleMsg(error instanceof Error ? error.message : 'Review failed');
    } finally {
      setBusy(false);
      void fetchAll();
    }
  };

  const doSearch = async () => {
    if (!query.trim()) return;
    setBusy(true);
    setAudibleMsg(null);
    try {
      const result = await searchIdentity(query.trim());
      setSearch(result);
    } catch (error) {
      setAudibleMsg(error instanceof Error ? error.message : 'Search failed');
    } finally {
      setBusy(false);
    }
  };

  const topAssociations = useMemo(
    () => relationships.filter((r) => r.assessment === 'POSSIBLE_ASSOCIATED'),
    [relationships],
  );
  const identityLeads = useMemo(
    () => relationships.filter((r) => r.assessment === 'PROBABLE_IDENTITY_MATCH' || r.assessment === 'POSSIBLE_IDENTITY_MATCH'),
    [relationships],
  );

  const tabs: { id: Tab; label: string; badge?: number }[] = [
    { id: 'review', label: 'Review Center', badge: identityLeads.length },
    { id: 'proxy', label: 'Proxy Patterns', badge: proxies.length },
    { id: 'alerts', label: 'Integrity Alerts', badge: alerts.filter((a) => a.status === 'open').length },
    { id: 'graph', label: 'Identity Graph' },
    { id: 'search', label: 'Person Search' },
  ];

  if (loading) return <PageSkeleton />;

  return (
    <div className="space-y-4 sk-page-enter">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-[var(--text-primary)] tracking-wide flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-[var(--accent-purple)]" />
            Identity Resolution &amp; Data Integrity
          </h1>
          <p className="text-[11px] text-[var(--text-muted)] font-mono mt-0.5">
            Fake / duplicate record detection across stations — never auto-confirms identity, never auto-accuses. All findings require human review.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {canReview && (
            <>
              <button
                onClick={doRun}
                disabled={busy}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--accent-purple)]/40 bg-[var(--accent-purple)]/10 text-[var(--accent-purple)] text-[12px] font-semibold hover:bg-[var(--accent-purple)]/20 transition-colors cursor-pointer disabled:opacity-50"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCcw className="w-4 h-4" />}
                Run Full Scan
              </button>
              <button
                onClick={doRunProxy}
                disabled={busy}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-tertiary)] text-[var(--text-secondary)] text-[12px] font-semibold hover:text-[var(--text-primary)] transition-colors cursor-pointer disabled:opacity-50"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldAlert className="w-4 h-4" />}
                Proxy Only
              </button>
            </>
          )}
        </div>
      </div>

      {audibleMsg && (
        <div className="sk-card px-4 py-3 border-l-4 border-[var(--accent-purple)] text-[13px] text-[var(--text-secondary)] flex items-center gap-2">
          <Info className="w-4 h-4 text-[var(--accent-purple)] shrink-0" />
          {audibleMsg}
        </div>
      )}

      {loadError && (
        <div className="sk-card px-4 py-3 border-l-4 border-[var(--accent-coral)] text-[13px] text-[var(--accent-coral)] flex items-center gap-2">
          <FileWarning className="w-4 h-4 shrink-0" />
          {loadError}
        </div>
      )}

      {dash && dash.records_analyzed === 0 && (
        <div className="sk-card px-4 py-4 border-l-4 border-[var(--accent-amber)] text-[13px] text-[var(--text-secondary)]">
          <div className="font-semibold text-[var(--text-primary)]">No identity data is loaded yet.</div>
          <p className="mt-1 text-[12px] text-[var(--text-muted)]">
            Run the backend seed once to add the demo users, criminal/victim records, and linked FIRs. Then return here and run a full scan.
          </p>
          {canReview && (
            <button
              onClick={doRun}
              disabled={busy}
              className="mt-3 inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--accent-purple)]/40 bg-[var(--accent-purple)]/10 text-[var(--accent-purple)] text-[12px] font-semibold disabled:opacity-50"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCcw className="w-4 h-4" />}
              Run Full Scan
            </button>
          )}
        </div>
      )}

      {/* KPI row */}
      {dash && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard label="Records Scanned" value={dash.records_analyzed ?? '-'} icon={<Link2 className="w-5 h-5" />} tone="blue" />
          <StatCard label="Possible Duplicates" value={dash.possible_duplicates ?? 0} icon={<FileWarning className="w-5 h-5" />} tone="coral" />
          <StatCard label="Proxy Leads" value={dash.possible_proxy_relationships ?? 0} icon={<ShieldAlert className="w-5 h-5" />} tone="purple" />
          <StatCard label="Identifier Reuse" value={dash.identifier_reuse_alerts ?? 0} icon={<RefreshCcw className="w-5 h-5" />} tone="amber" />
          <StatCard label="Critical Reviews" value={dash.critical_reviews ?? 0} icon={<Flag className="w-5 h-5" />} tone="coral" />
          <StatCard label="Open Reviews" value={dash.open_reviews ?? 0} icon={<Eye className="w-5 h-5" />} tone="teal" />
        </div>
      )}

      {identityLeads.length > 0 && (
        <div className="sk-card p-4 border border-[var(--accent-coral)]/30">
          <div className="flex items-center gap-2 mb-3 text-[13px] font-bold text-[var(--accent-coral)] uppercase tracking-wider">
            <ShieldAlert className="w-4 h-4" />
            Requires Review — Duplicate Identity Leads
          </div>
          <div className="space-y-2">
            {identityLeads.map((r) => (
              <div key={r.id} className="flex flex-wrap items-center gap-2 text-[13px]">
                <span className="font-semibold text-[var(--text-primary)]">{r.source_name ?? 'Unknown'}</span>
                <span className="text-[var(--text-muted)]">↔</span>
                <span className="font-semibold text-[var(--text-primary)]">{r.target_name ?? 'Unknown'}</span>
                <Badge text={ASSESSMENT_META[r.assessment]?.label ?? r.assessment} cls={ASSESSMENT_META[r.assessment]?.cls ?? SEVERITY_CLS.low} />
                <span className="font-mono text-[var(--text-secondary)]">{r.confidence.toFixed(0)}% confidence</span>
                <span className="text-[11px] text-[var(--text-muted)]">{r.evidence_summary?.supporting_count ?? 0} evidence signal(s)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-[var(--border-primary)]">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`inline-flex items-center gap-1.5 px-3 py-2 text-[12px] font-semibold rounded-t-lg border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
              tab === t.id
                ? 'border-[var(--accent-blue)] text-[var(--text-primary)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
          >
            {t.label}
            {!!t.badge && (
              <span className="px-1.5 py-0.5 rounded-full bg-[var(--accent-purple)]/20 border border-[var(--accent-purple)]/40 text-[var(--accent-purple)] text-[10px] font-mono">
                {t.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {tab === 'review' && (
        <div className="space-y-3">
          {identityLeads.length === 0 && (
            <p className="text-[12px] text-[var(--text-muted)] py-4 text-center">No duplicate-identity leads currently pending review. Associations below are surfacing context only.</p>
          )}
          {canReview && reviewsTable(identityLeads, (id, decision, note) => doReview(() => reviewIdentityRelationship(id, decision, note), `Relationship ${decision} recorded.`))}
          <details className="sk-card p-3">
            <summary className="text-[12px] font-semibold text-[var(--text-secondary)] cursor-pointer">
              Co-occurrence / Association pairs ({topAssociations.length}) — display-only context, not a match finding
            </summary>
            <div className="mt-3 max-h-[420px] overflow-y-auto">
              <AssociationsTable rows={topAssociations} />
            </div>
          </details>
        </div>
      )}

      {tab === 'proxy' && (
        <div className="space-y-3">
          {proxies.length === 0 ? (
            <p className="text-[12px] text-[var(--text-muted)] py-4 text-center">No proxy patterns detected.</p>
          ) : (
            <div className="max-h-[560px] overflow-y-auto space-y-2">
              {proxies.map((p) => (
                <div key={p.id} className="sk-card p-3">
                  <div className="flex flex-wrap items-center gap-2 mb-1.5">
                    <Badge text={p.rule_id} cls={SEVERITY_CLS[p.severity] ?? SEVERITY_CLS.low} />
                    <Badge text={p.severity} cls={SEVERITY_CLS[p.severity] ?? SEVERITY_CLS.low} />
                    <span className="font-mono text-[12px] text-[var(--text-secondary)]">{p.confidence ? `${(p.confidence * 100).toFixed(0)}%` : ''}</span>
                    <span className="text-[12px] text-[var(--text-secondary)]">{p.entities.map((e) => e.name).join(' ↔ ')}</span>
                  </div>
                  <p className="text-[12px] text-[var(--text-secondary)] mb-1.5">{p.explanation}</p>
                  {(p.possible_explanations?.length > 0 || p.evidence?.length > 0) && (
                    <div className="text-[11px] text-[var(--text-muted)] space-y-0.5">
                      {p.evidence?.map((e, i) => (
                        <div key={i} className="flex items-start gap-1.5">
                          <ShieldCheck className="w-3 h-3 mt-0.5 text-[var(--accent-teal)] shrink-0" />
                          <span>{e.description || e.rule_id}</span>
                        </div>
                      ))}
                      {p.possible_explanations?.map((x, i) => (
                        <div key={`x${i}`} className="flex items-start gap-1.5">
                          <Info className="w-3 h-3 mt-0.5 text-[var(--accent-amber)] shrink-0" />
                          <span>Possible innocent cause: {x}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {p.status && <div className="mt-1.5"><Badge text={p.status} cls={SEVERITY_CLS.low} /></div>}
                  {canReview && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {(['confirm', 'proxy', 'same_person', 'dismiss', 'investigate'] as const).map((d) => (
                        <button
                          key={d}
                          disabled={busy}
                          onClick={() => doReview(() => reviewProxyPattern(p.id, d), `Proxy pattern marked ${d}.`)}
                          className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-[var(--border-primary)] text-[10px] font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent-blue)]/40 transition-colors cursor-pointer disabled:opacity-50"
                        >
                          {d === 'confirm' || d === 'proxy' ? <Check className="w-3 h-3" /> : d === 'dismiss' ? <X className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                          {d.replace('_', ' ')}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'alerts' && (
        <div className="space-y-2">
          {alerts.length === 0 ? (
            <p className="text-[12px] text-[var(--text-muted)] py-4 text-center">No integrity alerts present.</p>
          ) : (
            alerts.map((a) => (
              <div key={a.id} className="sk-card p-3">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <Badge text={a.alert_type.replace(/_/g, ' ')} cls={SEVERITY_CLS[a.severity] ?? SEVERITY_CLS.low} />
                  <Badge text={a.severity} cls={SEVERITY_CLS[a.severity] ?? SEVERITY_CLS.low} />
                  <span className="text-[12px] text-[var(--text-secondary)]">{a.description}</span>
                </div>
                {(a.display_value || a.observation_count != null) && (
                  <div className="text-[11px] font-mono text-[var(--text-muted)]">
                    {a.display_value && <>Identifier: <span className="text-[var(--text-secondary)]">{a.display_value}</span> · </>}
                    {a.observation_count != null && <>observed on {a.observation_count} record(s)</>}
                  </div>
                )}
                <div className="mt-1.5"><Badge text={a.status} cls={SEVERITY_CLS.low} /></div>
                {canReview && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {(['confirm', 'dismiss', 'investigate'] as const).map((d) => (
                      <button
                        key={d}
                        disabled={busy}
                        onClick={() => doReview(() => reviewIdentityAlert(a.id, d), `Alert marked ${d}.`)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded-md border border-[var(--border-primary)] text-[10px] font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent-blue)]/40 transition-colors cursor-pointer disabled:opacity-50"
                      >
                        {d === 'confirm' ? <Check className="w-3 h-3" /> : d === 'dismiss' ? <X className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                        {d}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'graph' && graph && (
        <div className="sk-card p-3">
          <p className="text-[12px] text-[var(--text-muted)] mb-2">
            Entity ↔ identity graph. Thicker/coloured links are higher-confidence duplicate-identity leads. Showing {graph.nodes.length} record(s) and {graph.edges.length} proposed link(s).
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {graph.nodes.map((n) => {
              const out = graph.edges.filter(
                (e) => e.source === n.id || e.target === n.id,
              );
              const isLead = out.some((e) => e.assessment === 'PROBABLE_IDENTITY_MATCH' || e.assessment === 'POSSIBLE_IDENTITY_MATCH');
              return (
                <div key={n.id} className={`rounded-lg border p-3 ${isLead ? 'border-[var(--accent-coral)]/40 bg-[var(--accent-coral)]/5' : 'border-[var(--border-primary)] bg-[var(--bg-tertiary)]/60'}`}>
                  <div className="flex items-center gap-2">
                    <Network className={`w-4 h-4 ${isLead ? 'text-[var(--accent-coral)]' : 'text-[var(--accent-blue)]'}`} />
                    <span className="font-semibold text-[13px] text-[var(--text-primary)] truncate">{n.name}</span>
                  </div>
                  <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                    <span className="uppercase font-mono">{n.entity_type}</span>
                    {n.aliases?.length > 0 && <> · aliases: {n.aliases.join(', ')}</>}
                  </div>
                  <div className="mt-2 border-t border-[var(--border-primary)] pt-2 space-y-1">
                    {out.map((e) => (
                      <div key={e.relationship_id} className="text-[11px] font-mono text-[var(--text-secondary)] flex items-center gap-1.5">
                        <Link2 className="w-3 h-3 text-[var(--text-muted)] shrink-0" />
                        <span className="truncate">confidence {e.confidence ? `${e.confidence.toFixed(0)}%` : 'n/a'} · {e.assessment.replace(/_/g, ' ')}</span>
                      </div>
                    ))}
                    {out.length === 0 && <div className="text-[11px] text-[var(--text-muted)]">No proposed links</div>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {tab === 'search' && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <div className="flex-1 flex items-center gap-2 sk-card px-3 py-2">
              <Search className="w-4 h-4 text-[var(--text-muted)]" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && doSearch()}
                placeholder="Search person by name or alias (e.g. 'Ramu Kumar')..."
                className="flex-1 bg-transparent text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] outline-none"
              />
            </div>
            <button
              onClick={doSearch}
              disabled={busy || !query.trim()}
              className="px-3 py-2 rounded-lg border border-[var(--accent-blue)]/40 bg-[var(--accent-blue)]/10 text-[var(--accent-blue)] text-[12px] font-semibold hover:bg-[var(--accent-blue)]/20 transition-colors cursor-pointer disabled:opacity-50 inline-flex items-center gap-1.5"
            >
              {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Search
            </button>
          </div>
          {search && renderSearch(search)}
        </div>
      )}

      <div className="sk-card p-3 border-t border-[var(--border-primary)]">
        <p className="text-[10px] font-mono text-[var(--text-muted)] leading-relaxed">
          POLICY NOTE · All findings are {canReview ? '' : 'read-only for your role'} proposed leads for a human reviewer — the system never automatically merges identities and never labels any person as a duplicate or a proxy. Review decisions are logged to the audit trail. Raw contact/identifier values are stored hashed and masked server-side.
        </p>
      </div>
    </div>
  );
};

function renderSearch(search: IdentitySearchResponse) {
  const sections = [
    { label: 'Exact matches', items: search.exact },
    { label: 'Probable matches', items: search.probable },
    { label: 'Possible matches', items: search.possible },
  ];
  if (!search.exact.length && !search.probable.length && !search.possible.length) {
    return <p className="text-[12px] text-[var(--text-muted)] py-4 text-center">No matching persons found.</p>;
  }
  return (
    <div className="space-y-3">
      {sections.map((s) =>
        s.items.length === 0 ? null : (
          <div key={s.label} className="sk-card p-3">
            <div className="text-[11px] font-mono uppercase tracking-wider text-[var(--text-muted)] mb-2">{s.label}</div>
            {s.items.map((item) => (
              <div key={`${item.entity_type}:${item.entity_id}`} className="flex items-center gap-2 py-1 text-[13px]">
                <span className="font-semibold text-[var(--text-primary)]">{item.name}</span>
                <span className="text-[11px] font-mono text-[var(--text-muted)] uppercase">{item.entity_type}</span>
                {item.aliases?.length > 0 && <span className="text-[11px] text-[var(--text-muted)]">aliases: {item.aliases.join(', ')}</span>}
                {/* eslint-disable-next-line no-constant-condition */}
                {typeof item.match_type === 'string' && <span className="text-[11px] text-[var(--text-muted)]">({item.match_type})</span>}
              </div>
            ))}
          </div>
        ),
      )}
    </div>
  );
}

function reviewsTable(
  leads: IdentityRelationship[],
  onReview: (id: string, decision: string, note?: string) => void,
) {
  if (leads.length === 0) {
    return (
      <div className="sk-card p-4 flex flex-col items-center justify-center gap-2 text-center">
        <ShieldCheck className="w-8 h-8 text-[var(--accent-teal)]" />
        <p className="text-[13px] text-[var(--text-secondary)]">No duplicate-identity proposals awaiting action.</p>
      </div>
    );
  }
  return (
    <div className="sk-card p-0 overflow-hidden">
      <table className="w-full text-left text-[12px]">
        <thead className="bg-[var(--bg-tertiary)]/60 text-[var(--text-muted)] text-[10px] font-mono uppercase tracking-wider">
          <tr>
            <th className="p-2.5">Record A</th>
            <th className="p-2.5">Record B</th>
            <th className="p-2.5">Assessment</th>
            <th className="p-2.5 text-right">Confidence</th>
            <th className="p-2.5">Evidence</th>
            <th className="p-2.5">Review</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border-primary)]">
          {leads.map((r) => (
            <tr key={r.id} className="hover:bg-[var(--bg-tertiary)]/40">
              <td className="p-2.5 font-semibold text-[var(--text-primary)]">{r.source_name ?? 'Unknown'}</td>
              <td className="p-2.5 font-semibold text-[var(--text-primary)]">{r.target_name ?? 'Unknown'}</td>
              <td className="p-2.5">
                <Badge text={ASSESSMENT_META[r.assessment]?.label ?? r.assessment} cls={ASSESSMENT_META[r.assessment]?.cls ?? SEVERITY_CLS.low} />
              </td>
              <td className="p-2.5 text-right font-mono text-[var(--text-secondary)]">{r.confidence.toFixed(0)}%</td>
              <td className="p-2.5 text-[var(--text-muted)]">{r.evidence_summary?.supporting_count ?? 0} signal(s)</td>
              <td className="p-2.5">
                <div className="flex gap-1.5">
                  {[{ d: 'confirm_same', l: 'Confirm' }, { d: 'reject', l: 'Reject' }, { d: 'investigate', l: 'Investigate' }].map(({ d, l }) => (
                    <button
                      key={d}
                      onClick={() => onReview(r.id, d)}
                      className="px-2 py-1 rounded-md border border-[var(--border-primary)] text-[10px] font-mono text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--accent-blue)]/40 transition-colors cursor-pointer"
                    >
                      {l}
                    </button>
                  ))}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AssociationsTable({ rows }: { rows: IdentityRelationship[] }) {
  if (rows.length === 0) return <p className="text-[12px] text-[var(--text-muted)] text-center py-3">No association pairs.</p>;
  return (
    <table className="w-full text-left text-[12px]">
      <thead className="bg-[var(--bg-tertiary)]/60 text-[var(--text-muted)] text-[10px] font-mono uppercase tracking-wider">
        <tr>
          <th className="p-2">Record A</th>
          <th className="p-2">Record B</th>
          <th className="p-2 text-right">Confidence</th>
          <th className="p-2">Evidence</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-[var(--border-primary)]">
        {rows.slice(0, 150).map((r) => (
          <tr key={r.id} className="hover:bg-[var(--bg-tertiary)]/40">
            <td className="p-2 text-[var(--text-secondary)]">{r.source_name ?? 'Unknown'}</td>
            <td className="p-2 text-[var(--text-secondary)]">{r.target_name ?? 'Unknown'}</td>
            <td className="p-2 text-right font-mono text-[var(--text-muted)]">{r.confidence.toFixed(0)}%</td>
            <td className="p-2 text-[var(--text-muted)]">{r.evidence_summary?.supporting_count ?? 0} signal(s)</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default IdentityResolution;
