import { useEffect, useState } from 'react';
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
  const [interventions, setInterventions] = useState<InterventionRecord[]>([]);
  const [effectiveness, setEffectiveness] = useState<Record<string, InterventionEffectiveness>>({});
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
      setInterventions(response.interventions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load interventions');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const analyze = async (id: string) => {
    setBusyId(id);
    setError(null);
    try {
      const result = await getInterventionEffectiveness(id);
      setEffectiveness((current) => ({ ...current, [id]: result }));
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
      <div className="flex items-center justify-between">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
            <ShieldCheck className="w-4 h-4 text-[var(--accent-teal)]" />
            Prevention Interventions &amp; Evidence of Effectiveness
          </h3>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Compare crime volume in equal windows before vs after each intervention.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => void load()} className="px-3 py-2 rounded-lg border border-border-color text-xs text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition flex items-center gap-1.5">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button onClick={() => setShowForm((v) => !v)} className="px-3 py-2 rounded-lg bg-[var(--accent-teal)]/15 border border-[var(--accent-teal)]/35 text-xs font-medium text-[var(--text-primary)] transition flex items-center gap-1.5">
            <Plus className="w-3.5 h-3.5" /> Record Intervention
          </button>
        </div>
      </div>

      {error && <div className="rounded-lg border border-amber-500/30 px-3 py-2 text-xs text-amber-300">{error}</div>}

      {showForm && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 p-4 bg-[var(--bg-secondary)] rounded-xl border border-border-color">
          <input placeholder="District *" value={draft.district} onChange={(e) => setDraft({ ...draft, district: e.target.value })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]" />
          <select value={draft.intervention_type} onChange={(e) => setDraft({ ...draft, intervention_type: e.target.value })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]">
            {['patrol_surge', 'checkpoint_blitz', 'cctv_deployment', 'awareness_campaign', 'lighting_upgrade', 'special_drive', 'other'].map((t) => (
              <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
            ))}
          </select>
          <input placeholder="Title *" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]" />
          <input type="date" placeholder="Started *" value={draft.started_at.slice(0, 10)} onChange={(e) => setDraft({ ...draft, started_at: e.target.value ? `${e.target.value}T00:00:00Z` : '' })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]" />
          <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value as InterventionCreateInput['status'] })}
            className="rounded bg-[var(--bg-primary)] border border-border-color px-3 py-2 text-xs text-[var(--text-primary)]">
            {['planned', 'active', 'completed', 'suspended'].map((st) => <option key={st} value={st}>{st}</option>)}
          </select>
          <button onClick={() => void submit()} disabled={saving}
            className="rounded bg-[#0E9E78]/20 border border-[#0E9E78]/40 px-3 py-2 text-xs font-bold uppercase text-[var(--text-primary)] disabled:opacity-50">
            {saving ? 'Saving…' : 'Save Intervention'}
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 className="w-6 h-6 animate-spin text-[var(--accent-blue)]" />
        </div>
      ) : interventions.length === 0 ? (
        <div className="p-8 text-center text-xs uppercase tracking-widest text-[var(--text-muted)] border border-dashed border-[var(--border-primary)] rounded-xl">
          No interventions recorded yet — log one to start measuring impact.
        </div>
      ) : (
        <div className="space-y-3">
          {interventions.map((item) => {
            const eff = effectiveness[item.id];
            return (
              <div key={item.id} className="p-4 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-primary)] space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="text-sm font-semibold text-[var(--text-primary)]">{item.title}</h4>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${STATUS_STYLES[item.status] ?? ''}`}>{item.status}</span>
                    </div>
                    <p className="text-xs text-[var(--text-muted)] mt-0.5">
                      {item.district} · {item.intervention_type.replace(/_/g, ' ')} · from {new Date(item.started_at).toLocaleDateString()}
                      {item.ended_at ? ` to ${new Date(item.ended_at).toLocaleDateString()}` : ''}
                    </p>
                  </div>
                  <button
                    onClick={() => void analyze(item.id)}
                    disabled={busyId === item.id}
                    className="px-3 py-1.5 bg-[var(--accent-teal)]/10 hover:bg-[var(--accent-teal)]/20 border border-[var(--accent-teal)]/30 text-[var(--accent-teal)] text-xs font-mono font-bold rounded-btn transition-colors disabled:opacity-50"
                  >
                    {busyId === item.id ? 'Analyzing…' : eff ? 'Re-analyze' : 'Analyze Effectiveness'}
                  </button>
                </div>

                {eff && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    <div className="p-2 bg-[var(--bg-primary)] rounded border border-border-color">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)]">Pre (90d)</span>
                      <span className="font-bold text-[var(--text-primary)]">{eff.pre_window.crime_count} crimes</span>
                    </div>
                    <div className="p-2 bg-[var(--bg-primary)] rounded border border-border-color">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)]">Post</span>
                      <span className="font-bold text-[var(--text-primary)]">{eff.post_window.crime_count} crimes</span>
                    </div>
                    <div className="p-2 bg-[var(--bg-primary)] rounded border border-border-color">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)]">Change</span>
                      <span className={`font-bold ${eff.change_percentage === null ? '' : eff.change_percentage < 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {eff.change_percentage === null ? '—' : `${eff.change_percentage > 0 ? '+' : ''}${eff.change_percentage}%`}
                      </span>
                    </div>
                    <div className="p-2 bg-[var(--bg-primary)] rounded border border-border-color">
                      <span className="block text-[9px] uppercase text-[var(--text-muted)]">Verdict</span>
                      <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold uppercase ${VERDICT_STYLES[eff.verdict] ?? ''}`}>{eff.verdict.replace(/_/g, ' ')}</span>
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
