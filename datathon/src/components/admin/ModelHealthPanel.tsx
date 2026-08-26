import { useState, useEffect } from 'react';
import { Cpu, CheckCircle, XCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { getModelHealth, type ModelHealthReport } from '../../services/api';

function StatusBadge({ status }: { status: string }) {
  const color = status === 'VALID' ? 'var(--accent-teal)' : status === 'DEGRADED' ? 'var(--accent-amber)' : 'var(--accent-coral)';
  const Icon = status === 'VALID' ? CheckCircle : status === 'DEGRADED' ? AlertTriangle : XCircle;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold" style={{ backgroundColor: `${color}20`, color, border: `1px solid ${color}40` }}>
      <Icon className="w-3 h-3" /> {status}
    </span>
  );
}

export default function ModelHealthPanel() {
  const [report, setReport] = useState<ModelHealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getModelHealth();
      setReport(data);
    } catch (e: any) {
      setError(e?.message || 'Failed to load model health');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="flex items-center gap-2 text-[var(--text-secondary)] text-xs py-8 justify-center"><RefreshCw className="w-4 h-4 animate-spin" /> Loading model health...</div>;
  if (error) return <div className="text-[var(--accent-coral)] text-xs py-8 text-center">{error}</div>;
  if (!report) return null;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[var(--accent-purple)]" />
          <span className="text-sm font-semibold text-[var(--text-primary)]">ML Model Health</span>
          <StatusBadge status={report.overall_status} />
        </div>
        <button onClick={load} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Hotspot Model */}
        <ModelCard
          title="Hotspot Predictor"
          status={report.hotspot.overall_status}
          loaded={report.hotspot.model_loaded}
          checks={report.hotspot.checks}
          validCount={report.hotspot.valid_count}
          invalidCount={report.hotspot.invalid_count}
        />
        {/* Risk Model */}
        <ModelCard
          title="Risk & Forecast"
          status={report.risk.overall_status}
          loaded={report.risk.risk_model_loaded && report.risk.forecast_model_loaded}
          checks={report.risk.checks}
          validCount={report.risk.valid_count}
          invalidCount={report.risk.invalid_count}
          extraInfo={[
            { label: 'Risk Model', loaded: report.risk.risk_model_loaded },
            { label: 'Forecast Model', loaded: report.risk.forecast_model_loaded },
          ]}
        />
      </div>
    </div>
  );
}

function ModelCard({ title, status, loaded, checks, validCount, invalidCount, extraInfo }: {
  title: string;
  status: string;
  loaded: boolean;
  checks: { valid: boolean; artifact: string; error?: string }[];
  validCount: number;
  invalidCount: number;
  extraInfo?: { label: string; loaded: boolean }[];
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--border-color)] flex items-center justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--text-primary)]">{title}</span>
          <StatusBadge status={status} />
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-[var(--text-secondary)]">{validCount} ok / {invalidCount} fail</span>
          <span className="text-[var(--text-secondary)] text-[10px]">{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div className="px-4 py-3 space-y-2">
          <div className="flex items-center gap-2 text-[11px]">
            <span className="text-[var(--text-secondary)]">Trained:</span>
            <span className={loaded ? 'text-[var(--accent-teal)]' : 'text-[var(--accent-amber)]'}>
              {loaded ? 'Yes' : 'No (fallback mode)'}
            </span>
          </div>
          {extraInfo?.map((ei) => (
            <div key={ei.label} className="flex items-center gap-2 text-[11px]">
              <span className="text-[var(--text-secondary)]">{ei.label}:</span>
              <span className={ei.loaded ? 'text-[var(--accent-teal)]' : 'text-[var(--accent-coral)]'}>
                {ei.loaded ? 'Loaded' : 'Missing'}
              </span>
            </div>
          ))}
          <div className="mt-2 space-y-1">
            {checks.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                {c.valid ? (
                  <CheckCircle className="w-3 h-3 text-[var(--accent-teal)] shrink-0" />
                ) : (
                  <XCircle className="w-3 h-3 text-[var(--accent-coral)] shrink-0" />
                )}
                <span className="text-[var(--text-secondary)]">{c.artifact}</span>
                {c.error && <span className="text-[var(--accent-coral)] truncate">{c.error}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
