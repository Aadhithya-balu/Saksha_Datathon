import { useEffect, useState } from 'react';
import { useRBAC } from '../../hooks/useRBAC';
import { Loader2, Plus, RefreshCw, ShieldCheck } from 'lucide-react';
import {
  createIntervention,
  getInterventionEffectiveness,
  listInterventions,
  type InterventionCreateInput,
  type InterventionEffectiveness,
  type InterventionRecord,
} from '../../services/api';

const VERDICT_STYLES: Record<string, string> = {
  effective: 'bg-green-500/20 text-green-400',
  partially_effective: 'bg-amber-500/20 text-amber-400',
  no_measurable_effect: 'bg-red-500/20 text-red-400',
  insufficient_data: 'bg-blue-500/20 text-blue-400',
};

const STATUS_STYLES: Record<string, string> = {
  planned: 'bg-blue-500/20 text-blue-400',
  active: 'bg-green-500/20 text-green-400',
  completed: 'bg-[var(--text-muted)]/20 text-[var(--text-secondary)]',
  suspended: 'bg-amber-500/20 text-amber-400',
};

export default function InterventionsPanel() {
  const { isAdmin, isIO, isInspector, isSP } = useRBAC();
  const canWrite = isAdmin || isIO || isInspector || isSP;
  const [interventions, setInterventions] = useState<InterventionRecord[]>([]);
  const [effectiveness, setEffectiveness] = useState<Record<string, InterventionEffectiveness>>({});
  const [selectedWindows, setSelectedWindows] = useState<Record<string, number>>({});
  const [lastAnalyzedTimes, setLastAnalyzedTimes] = useState<Record<string, string>>({});
  const [globalWindow, setGlobalWindow] = useState<number>(30);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<InterventionCreateInput>({
    district: '',
    intervention_type: 'patrol_surge',
    title: '',
    started_at: '',
    status: 'completed',
  });
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const response = await listInterventions();
      const items: InterventionRecord[] = Array.isArray(response)
        ? response
        : (response?.interventions || response?.results || []);
      setInterventions(items);

      if (items.length > 0) {
        const effResults: Record<string, InterventionEffectiveness> = {};
        const timeResults: Record<string, string> = {};
        const nowStr = new Date().toLocaleTimeString();

        await Promise.allSettled(
          items.map(async (item) => {
            try {
              const win = selectedWindows[item.id] ?? globalWindow;
              const res = await getInterventionEffectiveness(item.id, win);
              effResults[item.id] = res;
              timeResults[item.id] = nowStr;
            } catch (e) {
              console.warn(`Could not compute effectiveness for ${item.id}`, e);
            }
          })
        );
        setEffectiveness(effResults);
        setLastAnalyzedTimes(timeResults);
      }
    } catch (err) {
      console.error('Failed to load interventions', err);
      setError(err instanceof Error ? err.message : 'Failed to load interventions');
      setInterventions([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [globalWindow]);

  const analyze = async (id: string, windowDays?: number) => {
    setBusyId(id);
    setError(null);
    const win = windowDays ?? selectedWindows[id] ?? globalWindow;
    setSelectedWindows((prev) => ({ ...prev, [id]: win }));
    try {
      const result = await getInterventionEffectiveness(id, win);
      setEffectiveness((current) => ({ ...current, [id]: result }));
      setLastAnalyzedTimes((prev) => ({ ...prev, [id]: new Date().toLocaleTimeString() }));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to compute effectiveness');
    } finally {
      setBusyId(null);
    }
  };

  const submit = async () => {
    if (!draft.district || !draft.title || !draft.started_at) return;
    setSaving(true);
    setError(null);
    try {
      await createIntervention(draft);
      setShowForm(false);
      setDraft({ district: '', intervention_type: 'patrol_surge', title: '', started_at: '', status: 'completed' });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to record intervention');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
            <ShieldCheck className="w-4 h-4 text-[var(--accent-teal)]" />
            Prevention Interventions &amp; Evidence of Effectiveness
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Compare crime volume in equal observation windows before vs after each intervention across Karnataka districts.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1 bg-[var(--bg-primary)] px-2.5 py-1 rounded-lg border border-border-color text-xs">
            <span className="text-[var(--text-muted)] text-[10px] font-mono uppercase mr-1">Global Window:</span>
            {[14, 30, 60, 90].map((w) => (
              <button
                key={w}
                onClick={() => setGlobalWindow(w)}
                className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-colors ${
                  globalWindow === w
                    ? 'bg-[var(--accent-blue)] text-white shadow-sm'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                }`}
              >
                {w}d
              </button>
            ))}
          </div>

          <button onClick={() => void load()} className="px-3 py-1.5 rounded-lg border border-border-color text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition flex items-center gap-1.5 cursor-pointer">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          {canWrite && (
          <button onClick={() => setShowForm((v) => !v)} className="px-3 py-1.5 rounded-lg bg-[var(--accent-teal)]/15 border border-[var(--accent-teal)]/35 text-xs font-medium text-[var(--text-primary)] transition flex items-center gap-1.5 cursor-pointer hover:bg-[var(--accent-teal)]/25">
            <Plus className="w-3.5 h-3.5" /> Record Intervention
          </button>
          )}
        </div>
      </div>

      {error && <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">{error}</div>}

      {showForm && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 bg-[var(--bg-secondary)] rounded-xl border border-border-color">
          <input placeholder="District (e.g. Bengaluru Urban) *" value={draft.district} onChange={(e) => setDraft({ ...draft, district: e.target.value })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]" />
          <select value={draft.intervention_type} onChange={(e) => setDraft({ ...draft, intervention_type: e.target.value })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]">
            {['patrol_surge', 'checkpoint_blitz', 'cctv_deployment', 'awareness_campaign', 'lighting_upgrade', 'special_drive', 'other'].map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, ' ').toUpperCase()}</option>
            ))}
          </select>
          <input placeholder="Intervention Title *" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]" />
          <input type="date" placeholder="Started *" value={draft.started_at.slice(0, 10)} onChange={(e) => setDraft({ ...draft, started_at: e.target.value ? `${e.target.value}T00:00:00Z` : '' })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]" />
          <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value as InterventionCreateInput['status'] })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]">
            {['planned', 'active', 'completed', 'suspended'].map((st) => <option key={st} value={st}>{st.toUpperCase()}</option>)}
          </select>
          <button onClick={() => void submit()} disabled={saving || !draft.district || !draft.title || !draft.started_at}
            className="rounded bg-[#0E9E78]/25 hover:bg-[#0E9E78]/40 border border-[#0E9E78]/50 px-3 py-2 text-xs font-bold uppercase text-[var(--text-primary)] disabled:opacity-50 cursor-pointer">
            {saving ? 'Saving…' : 'Save Intervention'}
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-[var(--accent-blue)]" />
          <span className="ml-2 text-xs text-[var(--text-muted)]">Loading strategic interventions...</span>
        </div>
      ) : !interventions || interventions.length === 0 ? (
        <div className="p-8 text-center text-xs uppercase tracking-widest text-[var(--text-muted)] border border-dashed border-[var(--border-primary)] rounded-xl space-y-3">
          <p>No interventions recorded yet — log one to start measuring impact.</p>
          {canWrite && (
          <button onClick={() => setShowForm(true)} className="px-3 py-1.5 bg-[var(--accent-teal)]/20 border border-[var(--accent-teal)]/40 text-[var(--accent-teal)] text-xs font-mono font-bold rounded-btn transition-colors cursor-pointer">
            + Record New Action
          </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {interventions.map((item) => {
            const eff = effectiveness[item.id];
            const changeVal = eff ? (eff.change_percentage ?? (eff as any).change_pct) : null;
            const currentItemWin = selectedWindows[item.id] ?? globalWindow;
            const isAnalyzing = busyId === item.id;
            const lastUpdated = lastAnalyzedTimes[item.id];

            return (
              <div key={item.id} className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] space-y-3 transition-all hover:border-[var(--border-secondary)]">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-sm font-semibold text-[var(--text-primary)]">{item.title}</h4>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${STATUS_STYLES[item.status] ?? 'bg-blue-500/20 text-blue-400'}`}>{item.status}</span>
                      {lastUpdated && (
                        <span className="text-[10px] font-mono text-[var(--text-muted)]">
                          · Evaluated at {lastUpdated}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--text-muted)]">
                      {item.district} · {(item.intervention_type || 'patrol_surge').replace(/_/g, ' ')} · from {item.started_at ? new Date(item.started_at).toLocaleDateString() : 'N/A'}
                      {item.ended_at ? ` to ${new Date(item.ended_at).toLocaleDateString()}` : ''}
                    </p>
                    {item.description && (
                      <p className="text-xs text-[var(--text-secondary)] font-sans">
                        {item.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2 self-start sm:self-center shrink-0 flex-wrap">
                    {/* Window Pill Buttons */}
                    <div className="flex items-center gap-1 bg-[var(--bg-primary)] px-2 py-1 rounded-lg border border-border-color">
                      <span className="text-[9px] font-mono uppercase text-[var(--text-muted)] mr-0.5">Win:</span>
                      {[14, 30, 60, 90].map((w) => (
                        <button
                          key={w}
                          onClick={() => void analyze(item.id, w)}
                          disabled={isAnalyzing}
                          className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold cursor-pointer transition-colors ${
                            currentItemWin === w
                              ? 'bg-[var(--accent-teal)] text-black font-extrabold shadow-sm'
                              : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                          }`}
                          title={`Evaluate ${w}-day pre/post window`}
                        >
                          {w}d
                        </button>
                      ))}
                    </div>

                    <button
                      onClick={() => void analyze(item.id, currentItemWin)}
                      disabled={isAnalyzing}
                      className="px-3 py-1.5 bg-[var(--accent-teal)]/10 hover:bg-[var(--accent-teal)]/20 border border-[var(--accent-teal)]/30 text-[var(--accent-teal)] text-xs font-mono font-bold rounded-btn transition-colors disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                    >
                      {isAnalyzing ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          <span>Re-analyzing…</span>
                        </>
                      ) : (
                        <>
                          <RefreshCw className="w-3 h-3" />
                          <span>Re-analyze</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {eff && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs pt-2 border-t border-[var(--border-primary)]/40">
                    <div className="p-2.5 bg-[var(--bg-primary)] rounded-lg border border-border-color flex flex-col justify-between">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)] font-mono">Pre-Intervention ({eff.window_days || currentItemWin}d)</span>
                      <div className="flex items-baseline gap-1 mt-1">
                        <span className="font-bold text-base text-[var(--text-primary)] font-mono">{eff.pre_window?.crime_count ?? 0}</span>
                        <span className="text-[10px] font-normal text-[var(--text-muted)]">crimes</span>
                      </div>
                    </div>

                    <div className="p-2.5 bg-[var(--bg-primary)] rounded-lg border border-border-color flex flex-col justify-between">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)] font-mono">Post-Intervention ({eff.window_days || currentItemWin}d)</span>
                      <div className="flex items-baseline gap-1 mt-1">
                        <span className="font-bold text-base text-[var(--text-primary)] font-mono">{eff.post_window?.crime_count ?? 0}</span>
                        <span className="text-[10px] font-normal text-[var(--text-muted)]">crimes</span>
                      </div>
                    </div>

                    <div className="p-2.5 bg-[var(--bg-primary)] rounded-lg border border-border-color flex flex-col justify-between">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)] font-mono">Impact Delta</span>
                      <div className="mt-1">
                        <span className={`font-bold text-base font-mono ${
                          changeVal === null || changeVal === undefined ? 'text-[var(--text-muted)]' :
                          changeVal <= -20 ? 'text-green-400' :
                          changeVal < 0 ? 'text-emerald-400' :
                          changeVal === 0 ? 'text-blue-400' : 'text-amber-400'
                        }`}>
                          {changeVal === null || changeVal === undefined ? '—' : `${changeVal > 0 ? '+' : ''}${changeVal}%`}
                        </span>
                      </div>
                    </div>

                    <div className="p-2.5 bg-[var(--bg-primary)] rounded-lg border border-border-color flex flex-col justify-between">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)] font-mono">Effectiveness Verdict</span>
                      <div className="mt-1">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase ${VERDICT_STYLES[eff.verdict] ?? 'bg-blue-500/20 text-blue-400'}`}>
                          {(eff.verdict || 'insufficient_data').replace(/_/g, ' ')}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
