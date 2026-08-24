import React, { useEffect, useState } from 'react';
import { RefreshCw, ShieldQuestion } from 'lucide-react';
import {
  getRepeatVictims,
  getVictimologyOverview,
  getVulnerabilityIndex,
  type RepeatVictim,
  type VictimologyOverview,
  type VulnerabilityEntry,
} from '../../services/api';

const severityColor = (index: number) =>
  index >= 70 ? 'text-red-400' : index >= 45 ? 'text-amber-400' : 'text-[#0E9E78]';

export const VictimologyPanel: React.FC = () => {
  const [overview, setOverview] = useState<VictimologyOverview | null>(null);
  const [repeatVictims, setRepeatVictims] = useState<RepeatVictim[]>([]);
  const [vulnerability, setVulnerability] = useState<VulnerabilityEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([getVictimologyOverview(), getRepeatVictims(2), getVulnerabilityIndex()])
      .then(([overviewRes, repeatRes, vulnerabilityRes]) => {
        setOverview(overviewRes);
        setRepeatVictims(repeatRes.repeat_victims ?? []);
        setVulnerability(vulnerabilityRes.entries ?? []);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load victimology analytics'))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="space-y-4 font-mono">
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] border-b border-[var(--border-muted)] flex-1 pb-2">
          Victimology Analytics · Repeat Victimization & Vulnerability
        </span>
        <button onClick={load} disabled={loading} className="ml-3 inline-flex items-center gap-1.5 rounded border border-[#1E6FD9]/35 bg-[#1E6FD9]/15 px-2.5 py-1.5 text-[9px] font-bold uppercase text-[var(--text-primary)] disabled:opacity-40">
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {loading && <p className="text-[10px] uppercase text-[var(--text-muted)]">Loading victimology intelligence…</p>}
      {error && <div className="rounded border border-amber-500/30 px-3 py-2 text-[10px] uppercase tracking-wider text-amber-300">{error}</div>}

      {!loading && !error && overview && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="rounded border border-border-color bg-[var(--bg-tertiary)]/40 p-3">
              <span className="block text-[7.5px] uppercase text-[var(--text-muted)]">Total victims</span>
              <span className="text-lg font-bold text-[var(--text-primary)]">{overview.total_victims}</span>
            </div>
            <div className="rounded border border-border-color bg-[var(--bg-tertiary)]/40 p-3">
              <span className="block text-[7.5px] uppercase text-[var(--text-muted)]">Linked to FIRs</span>
              <span className="text-lg font-bold text-[var(--text-primary)]">{overview.victims_with_firs}</span>
            </div>
            <div className="rounded border border-border-color bg-[var(--bg-tertiary)]/40 p-3">
              <span className="block text-[7.5px] uppercase text-[var(--text-muted)]">Repeat victims</span>
              <span className="text-lg font-bold text-amber-400">{overview.repeat_victim_count}</span>
            </div>
            <div className="rounded border border-border-color bg-[var(--bg-tertiary)]/40 p-3">
              <span className="block text-[7.5px] uppercase text-[var(--text-muted)]">Revictimization rate</span>
              <span className="text-lg font-bold text-[var(--text-primary)]">
                {overview.repeat_victimization_rate === null ? '—' : `${Math.round(overview.repeat_victimization_rate)}%`}
              </span>
            </div>
          </div>

          <div className="rounded border border-border-color bg-[var(--bg-secondary)]/50 p-4">
            <p className="mb-2 text-[10px] font-bold uppercase tracking-wider text-[#0E9E78]">Repeat victims (≥2 FIRs)</p>
            {repeatVictims.length === 0 ? (
              <p className="py-3 text-center text-[9px] uppercase text-[var(--text-muted)] border border-dashed border-[var(--border-primary)] rounded">
                No repeat-victimization patterns detected in recorded FIR links.
              </p>
            ) : (
              <table className="w-full text-left text-[9px]">
                <thead className="text-[var(--text-muted)] uppercase">
                  <tr><th className="py-1 pr-3">Victim</th><th className="py-1 pr-3">FIRs</th><th className="py-1 pr-3">Districts</th><th className="py-1 pr-3">Categories</th><th className="py-1">Vulnerability</th></tr>
                </thead>
                <tbody className="divide-y divide-[var(--border-primary)] text-[var(--text-secondary)]">
                  {repeatVictims.map((victim) => (
                    <tr key={victim.id}>
                      <td className="py-1.5 pr-3 font-bold text-[var(--text-primary)]">{victim.name}</td>
                      <td className="py-1.5 pr-3 text-amber-400 font-bold">{victim.fir_count}</td>
                      <td className="py-1.5 pr-3 truncate max-w-[140px]">{victim.districts.join(', ') || '—'}</td>
                      <td className="py-1.5 pr-3 truncate max-w-[160px]">{victim.categories.join(', ') || '—'}</td>
                      <td className={`py-1.5 font-bold ${victim.vulnerability_index === null ? 'text-[var(--text-muted)]' : severityColor(victim.vulnerability_index)}`}>
                        {victim.vulnerability_index === null ? '—' : victim.vulnerability_index}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="rounded border border-border-color bg-[var(--bg-secondary)]/50 p-4">
            <p className="mb-2 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-[#0E9E78]">
              <ShieldQuestion className="h-3.5 w-3.5" /> Vulnerability index (top 25)
            </p>
            <div className="flex flex-col gap-1.5">
              {vulnerability.length === 0 ? (
                <p className="py-3 text-center text-[9px] uppercase text-[var(--text-muted)] border border-dashed border-[var(--border-primary)] rounded">
                  No vulnerability assessments available yet.
                </p>
              ) : (
                vulnerability.map((entry) => (
                  <div key={entry.id} className="flex items-center gap-2 rounded border border-[var(--border-primary)] px-2 py-1.5 text-[9px]">
                    <span className="w-28 truncate font-bold text-[var(--text-primary)]">{entry.name}</span>
                    <span className="w-32 truncate text-[var(--text-muted)]">{entry.district ?? 'Unknown district'}</span>
                    <div className="flex-1 h-1.5 rounded-full bg-black/30 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${entry.vulnerability_index >= 70 ? 'bg-red-500/70' : entry.vulnerability_index >= 45 ? 'bg-amber-500/70' : 'bg-[#0E9E78]/70'}`}
                        style={{ width: `${entry.vulnerability_index}%` }}
                      />
                    </div>
                    <span className={`w-8 text-right font-bold ${severityColor(entry.vulnerability_index)}`}>{entry.vulnerability_index}</span>
                    <span className="hidden md:inline w-56 truncate text-[7.5px] uppercase text-[var(--text-muted)]">{entry.risk_factors.join(' · ')}</span>
                  </div>
                ))
              )}
            </div>
            <p className="mt-2 text-[7.5px] uppercase italic text-[var(--text-muted)] leading-relaxed">
              Composite of age, gender, district exposure, prior-FIR count, and case recency. Screening aid only — not a determination of individual risk.
            </p>
          </div>
        </>
      )}
    </div>
  );
};

export default VictimologyPanel;
