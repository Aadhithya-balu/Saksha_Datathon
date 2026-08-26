import { useState, useEffect } from 'react';
import { Shield, AlertTriangle, Database, RefreshCw } from 'lucide-react';
import { getAdminDataQuality, type DataQualityReport } from '../../services/api';

const PROVENANCE_COLORS: Record<string, string> = {
  live: 'var(--accent-teal)',
  demo: 'var(--accent-amber)',
  migrated: 'var(--accent-blue)',
  unknown: 'var(--accent-coral)',
};

const SEVERITY_COLORS: Record<string, string> = {
  high: 'var(--accent-coral)',
  medium: 'var(--accent-amber)',
  low: 'var(--accent-blue)',
};

export default function DataQualityPanel() {
  const [report, setReport] = useState<DataQualityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getAdminDataQuality();
      setReport(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to load data quality report');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="flex items-center gap-2 text-[var(--text-secondary)] text-xs py-8 justify-center"><RefreshCw className="w-4 h-4 animate-spin" /> Loading data quality report...</div>;
  if (error) return <div className="text-[var(--accent-coral)] text-xs py-8 text-center">{error}</div>;
  if (!report) return null;

  const { summary, entity_breakdown, warnings } = report;

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-[var(--accent-blue)]" />
          <span className="text-sm font-semibold text-[var(--text-primary)]">Dataset Provenance Report</span>
        </div>
        <button onClick={load} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-3 text-center">
          <div className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1">Total Records</div>
          <div className="text-lg font-bold text-[var(--text-primary)] font-mono">{summary.total_records}</div>
        </div>
        {report.provenance_values.map((pv) => (
          <div key={pv} className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-3 text-center">
            <div className="text-[10px] uppercase tracking-wider text-[var(--text-secondary)] mb-1">{pv}</div>
            <div className="text-lg font-bold font-mono" style={{ color: PROVENANCE_COLORS[pv] || 'var(--text-primary)' }}>
              {summary.by_provenance[pv] ?? 0}
            </div>
          </div>
        ))}
      </div>

      {/* Entity Breakdown Table */}
      <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] overflow-hidden">
        <div className="px-4 py-2.5 border-b border-[var(--border-color)] flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
          <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">Entity Breakdown</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-[var(--border-color)]">
                <th className="px-4 py-2 text-left text-[var(--text-secondary)] uppercase tracking-wider font-semibold">Entity</th>
                {report.provenance_values.map((pv) => (
                  <th key={pv} className="px-4 py-2 text-right uppercase tracking-wider font-semibold" style={{ color: PROVENANCE_COLORS[pv] }}>{pv}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(entity_breakdown).map(([entity, counts]) => (
                <tr key={entity} className="border-b border-[var(--border-color)] last:border-0 hover:bg-[var(--bg-primary)]/30 transition-colors">
                  <td className="px-4 py-2 font-mono text-[var(--text-primary)]">{entity}</td>
                  {report.provenance_values.map((pv) => (
                    <td key={pv} className="px-4 py-2 text-right font-mono text-[var(--text-primary)]">
                      {counts[pv] ?? 0}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] overflow-hidden">
          <div className="px-4 py-2.5 border-b border-[var(--border-color)] flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-[var(--accent-amber)]" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-secondary)]">Data Quality Warnings ({warnings.length})</span>
          </div>
          <div className="divide-y divide-[var(--border-color)]">
            {warnings.map((w, i) => (
              <div key={i} className="px-4 py-2.5 flex items-start gap-3">
                <span
                  className="mt-0.5 inline-block w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: SEVERITY_COLORS[w.severity] || 'var(--text-secondary)' }}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-[var(--text-primary)]">{w.message}</div>
                  <div className="text-[9px] text-[var(--text-secondary)] mt-0.5 font-mono">{w.table} &middot; {w.severity}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {warnings.length === 0 && (
        <div className="text-center text-[11px] text-[var(--accent-teal)] py-3 rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)]">
          No data quality warnings detected
        </div>
      )}
    </div>
  );
}
