import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Search,
  Users,
  FileText,
  Briefcase,
  Heart,
  X,
  ArrowLeft,
  Brain,
  Fingerprint,
  Sparkles,
  ChevronRight,
  ShieldAlert,
  Boxes,
  History,
  Trash2,
  Link2,
  Network,
  Clock,
  Radar,
} from 'lucide-react';
import { usePolling } from '../../hooks/usePolling';
import { searchIntelligenceEntities, getIntelligenceHistory, deleteIntelligenceHistory } from '../../services/api';
import type { IntelligenceHistoryItem } from '../../services/api';
import { IntelligenceWorkspace } from '../../components/intelligence/IntelligenceWorkspace';
import { useTranslation } from '../../i18n';

type EntitySearchResult = {
  id: string;
  type: string;
  name: string;
  subtitle: string;
};

type FilterType = 'all' | 'fir' | 'case' | 'criminal' | 'victim';

const FILTERS: Array<{ key: FilterType; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'fir', label: 'FIR' },
  { key: 'case', label: 'Case' },
  { key: 'criminal', label: 'Criminal' },
  { key: 'victim', label: 'Victim' },
];

const typeAccent: Record<string, string> = {
  fir: '#1E6FD9',
  case: '#a855f7',
  criminal: '#C94A2A',
  victim: '#0E9E78',
};

const typeIcon: Record<string, React.ReactNode> = {
  fir: <FileText className="w-3.5 h-3.5" />,
  case: <Briefcase className="w-3.5 h-3.5" />,
  criminal: <Users className="w-3.5 h-3.5" />,
  victim: <Heart className="w-3.5 h-3.5" />,
};

const typeDefault = (type: string) => typeIcon[type] || <Boxes className="w-3.5 h-3.5" />;

const InvestigationIntelligence: React.FC = () => {
  const t = useTranslation();
  const [query, setQuery] = useState('');
  const [debounced, setDebounced] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [results, setResults] = useState<EntitySearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const [selected, setSelected] = useState<EntitySearchResult | null>(null);

  const [history, setHistory] = useState<IntelligenceHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);

  const inputRef = useRef<HTMLInputElement>(null);

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const raw = await getIntelligenceHistory(30);
      const seen = new Map<string, IntelligenceHistoryItem>();
      for (const h of raw) {
        const key = `${h.entity_type}:${h.entity_id}`;
        const existing = seen.get(key);
        if (!existing || (h.created_at && existing.created_at && new Date(h.created_at) > new Date(existing.created_at))) {
          seen.set(key, h);
        }
      }
      setHistory(Array.from(seen.values()).sort((a, b) =>
        (b.created_at || '').localeCompare(a.created_at || '')
      ).slice(0, 20));
    } catch {
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  // Background polling: silently refresh intelligence history every 30s
  usePolling(loadHistory, 30000);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 350);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    if (debounced.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    runSearch(debounced, filter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced, filter]);

  // Deep-link support: an incoming navigate-tab event for the Intelligence Engine
  // with a targetId (and optional targetType) opens the workspace immediately.
  useEffect(() => {
    const onNav = (e: Event) => {
      const detail = (e as CustomEvent)?.detail || {};
      if (detail.tab !== 'investigation_intelligence' || !detail.targetId) return;
      setSelected({
        id: detail.targetId,
        type: detail.targetType || 'case',
        name: detail.targetLabel || detail.targetId.slice(0, 8),
        subtitle: '',
      });
    };
    window.addEventListener('navigate-tab', onNav);
    return () => window.removeEventListener('navigate-tab', onNav);
  }, []);

  const runSearch = async (term: string, f: FilterType) => {
    setLoading(true);
    setSearchError(null);
    try {
      const type = f === 'all' ? undefined : f;
      const res = await searchIntelligenceEntities(term, type);
      setResults(res || []);
      setSearched(true);
    } catch (err: any) {
      setSearchError(err?.message || 'Search failed');
      setResults([]);
      setSearched(true);
    } finally {
      setLoading(false);
    }
  };

  const openEntity = (r: EntitySearchResult) => {
    setSelected(r);
  };

  const reset = () => {
    setSelected(null);
    setQuery('');
    setDebounced('');
    setResults([]);
    setSearched(false);
    loadHistory();
  };

  const handleDeleteHistory = async (runId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deleteIntelligenceHistory(runId);
      setHistory((prev) => prev.filter((h) => h.id !== runId));
    } catch {
      /* ignore */
    }
  };

  const openHistory = (h: IntelligenceHistoryItem) => {
    setSelected({
      id: h.entity_id,
      type: h.entity_type,
      name: h.entity_label || h.entity_id.slice(0, 8),
      subtitle: new Date(h.created_at || '').toLocaleString(),
    });
  };

  const pickFilter = (k: FilterType) => {
    setFilter(k);
    if (inputRef.current) inputRef.current.focus();
  };

  const statusMeta = useMemo(() => {
    if (!selected) return null;
    return [
      { key: 'fir', label: 'FIR' },
      { key: 'case', label: 'Case' },
      { key: 'criminal', label: 'Criminal' },
      { key: 'victim', label: 'Victim' },
    ].find((m) => m.key === selected.type);
  }, [selected]);

  if (selected) {
    return (
      <div className="min-h-[84vh] pb-10 select-none">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3 mb-4">
          <div>
            <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
              <Fingerprint className="w-5 h-5 text-[#a855f7]" />
              {t.intel_title}
            </h2>
            <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
              CONNECTIONS → COMMON THREADS → CRIME DNA → LEADS → TIMELINE → NETWORK → PATTERN BREAKS
            </p>
          </div>
          <button
            onClick={reset}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-primary)] text-[9px] font-mono uppercase tracking-wider text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)] transition-colors cursor-pointer shrink-0"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> {t.intel_new_analysis}
          </button>
        </div>

        <div className="max-w-6xl mx-auto">
          <IntelligenceWorkspace
            entityType={selected.type as 'fir' | 'criminal' | 'case' | 'victim'}
            entityId={selected.id}
            entityLabel={selected.name}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[84vh] pb-10 select-none">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3 mb-4">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-[#a855f7]" />
            {t.intel_title}
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            START FROM ANY FIR, CASE, CRIMINAL OR VICTIM — BUILD A UNIFIED INTELLIGENCE REPORT
          </p>
        </div>
      </div>

      {!selected && (
        <div className="mb-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1 flex items-center rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/70 focus-within:border-[#a855f7] transition-colors">
              <Search className="w-4 h-4 text-[var(--text-muted)] mx-3 shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t.intel_search_placeholder}
                className="flex-1 bg-transparent text-[var(--text-primary)] outline-none placeholder:text-[var(--text-muted)] min-w-0 text-sm py-2.5"
              />
              {query && (
                <button onClick={() => setQuery('')} className="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer shrink-0" aria-label="Clear">
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  onClick={() => pickFilter(f.key)}
                  className={`px-3 py-2 rounded-lg border text-[9px] font-mono uppercase tracking-wider transition-colors cursor-pointer ${
                    filter === f.key
                      ? 'border-[#a855f7]/50 bg-[#a855f7]/10 text-[#a855f7]'
                      : 'border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          <p className="text-[8.5px] font-mono text-[var(--text-muted)] mt-2 flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-[#a855f7]" />
            Every report is derived from authorized records with source citations and confidence levels —
            the engine never invents facts.
          </p>
        </div>
      )}

      {/* Landing state: capabilities + user history when idle */}
      {!selected && !query && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Capabilities overview */}
          <div className="lg:col-span-5 rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 p-4">
            <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[#a855f7] flex items-center gap-1.5 mb-3">
              <Radar className="w-3.5 h-3.5" /> {t.intel_capabilities}
            </span>
            <ul className="space-y-2.5">
              {[
                { icon: <Boxes className="w-3.5 h-3.5" />, label: t.intel_connections, desc: 'people, locations, officers, NER entities' },
                { icon: <Link2 className="w-3.5 h-3.5" />, label: t.intel_common_threads, desc: 'shared attributes across linked cases' },
                { icon: <Fingerprint className="w-3.5 h-3.5" />, label: t.intel_crime_dna, desc: 'MO profiling + semantic similarity' },
                { icon: <Network className="w-3.5 h-3.5" />, label: t.intel_network, desc: 'focused relationship graph' },
                { icon: <Clock className="w-3.5 h-3.5" />, label: t.intel_timeline, desc: 'chronology + escalation analysis' },
              ].map((c) => (
                <li key={c.label} className="flex items-start gap-2.5">
                  <span className="w-7 h-7 rounded-md flex items-center justify-center shrink-0 border text-[#a855f7] bg-[#a855f7]/5"
                    style={{ borderColor: '#a855f7/30' }}>
                    {c.icon}
                  </span>
                  <div>
                    <div className="text-[10.5px] font-semibold text-[var(--text-primary)]">{c.label}</div>
                    <div className="text-[8.5px] text-[var(--text-muted)]">{c.desc}</div>
                  </div>
                </li>
              ))}
            </ul>
            <p className="text-[8.5px] font-mono text-[var(--text-muted)] mt-3 pt-3 border-t border-[var(--border-primary)]/50">
              {t.intel_start_any}
            </p>
          </div>

          {/* User history */}
          <div className="lg:col-span-7 rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-elevated)]/40">
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)] flex items-center gap-1.5">
                <History className="w-3.5 h-3.5 text-[#a855f7]" /> {t.intel_recent_analyses}
              </span>
              <span className="text-[8px] font-mono text-[var(--text-muted)]">{history.length}</span>
            </div>

            {historyLoading ? (
              <div className="p-6 text-center">
                <div className="w-5 h-5 mx-auto mb-2 border-2 border-[#a855f7]/20 border-t-[#a855f7] rounded-full animate-spin" />
                <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase">{t.intel_loading_history}</span>
              </div>
            ) : history.length === 0 ? (
              <div className="p-6 text-center">
                <History className="w-6 h-6 text-[var(--text-muted)] mx-auto mb-2" />
                <p className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">{t.intel_no_history}</p>
                <p className="text-[8.5px] text-[var(--text-muted)] mt-1">{t.intel_no_history_hint}</p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--border-primary)/50] max-h-[360px] overflow-y-auto custom-scrollbar">
                {history.map((h) => {
                  const accent = typeAccent[h.entity_type] || '#D4820A';
                  return (
                    <button
                      key={h.id}
                      onClick={() => openHistory(h)}
                      className="w-full flex items-center gap-3 px-3 py-2 hover:bg-[var(--bg-elevated)]/40 transition-colors cursor-pointer text-left group"
                    >
                      <span className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 border text-[8px] font-mono uppercase"
                        style={{ background: `${accent}15`, color: accent, borderColor: `${accent}40` }}>
                        {h.entity_type.slice(0, 3)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-[10.5px] font-semibold text-[var(--text-primary)] truncate">{h.entity_label}</div>
                        {h.summary && <div className="text-[8.5px] font-mono text-[var(--text-muted)] truncate mt-0.5">{h.summary}</div>}
                        <div className="flex items-center gap-2 mt-1 text-[7.5px] font-mono text-[var(--text-muted)] uppercase">
                          <span>{h.connections} conn</span>
                          <span>·</span>
                          <span>{h.leads} leads</span>
                          <span>·</span>
                          <span>{h.timeline_events} events</span>
                          {h.created_at && (
                            <>
                              <span>·</span>
                              <span>{new Date(h.created_at).toLocaleDateString()}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <span
                        onClick={(e) => handleDeleteHistory(h.id, e)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded text-[var(--text-muted)] hover:text-[#C94A2A] hover:bg-[#C94A2A]/10 transition-all cursor-pointer shrink-0"
                        title={t.intel_remove_history}
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="space-y-3">
        {loading && (
          <div className="p-8 text-center border border-dashed border-[var(--border-primary)] rounded-xl">
            <div className="w-6 h-6 mx-auto mb-2 border-2 border-[#a855f7]/20 border-t-[#a855f7] rounded-full animate-spin" />
            <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase tracking-wider">{t.intel_searching}</span>
          </div>
        )}

        {searchError && (
          <div className="p-6 text-center border border-dashed border-[var(--border-primary)] rounded-xl">
            <ShieldAlert className="w-6 h-6 text-amber-400 mx-auto mb-2" />
            <p className="text-[10px] font-mono text-[var(--text-secondary)]">{searchError}</p>
          </div>
        )}

        {!loading && searched && results.length === 0 && !searchError && (
          <div className="p-8 text-center border border-dashed border-[var(--border-primary)] rounded-xl">
            <Search className="w-6 h-6 text-[var(--text-muted)] mx-auto mb-2" />
            <p className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wider">
              {t.intel_no_results} "{debounced}"
            </p>
            <p className="text-[9px] text-[var(--text-muted)] mt-2">
              {t.intel_no_results_hint}
            </p>
          </div>
        )}

        {results.length > 0 && (
          <div className="rounded-xl border border-[var(--border-primary)] bg-[var(--bg-secondary)]/40 overflow-hidden">
            <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-primary)] bg-[var(--bg-elevated)]/40">
              <span className="text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--text-primary)]">
                <Brain className="w-3.5 h-3.5 text-[#a855f7] inline mr-1.5" />
                {t.intel_entities}
              </span>
              <span className="text-[8px] font-mono text-[var(--text-muted)]">{results.length}</span>
            </div>
            <div className="divide-y divide-[var(--border-primary)/50]">
              {results.map((r) => {
                const accent = typeAccent[r.type] || '#D4820A';
                return (
                  <button
                    key={`${r.type}-${r.id}`}
                    onClick={() => openEntity(r)}
                    className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-[var(--bg-elevated)]/40 transition-colors cursor-pointer text-left"
                  >
                    <span
                      className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 border"
                      style={{ background: `${accent}15`, color: accent, borderColor: `${accent}40` }}
                    >
                      {typeDefault(r.type)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold text-[var(--text-primary)] truncate">{r.name}</span>
                        <span className="px-1.5 py-0.5 rounded text-[7px] font-mono uppercase border shrink-0"
                          style={{ color: accent, borderColor: `${accent}40` }}
                        >
                          {r.type}
                        </span>
                      </div>
                      {r.subtitle && <div className="text-[8.5px] font-mono text-[var(--text-muted)] truncate mt-0.5">{r.subtitle}</div>}
                    </div>
                    <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {statusMeta && (
          <div className="text-[9px] font-mono text-[var(--text-muted)]">
            Selected: <span style={{ color: typeAccent[statusMeta.key] || '#D4820A' }}>{statusMeta.label}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default InvestigationIntelligence;