import { useState, useEffect, useCallback } from 'react';
import {
  Cpu, CheckCircle, XCircle, AlertTriangle, RefreshCw, RotateCcw,
  Clock, Activity, ChevronDown, ChevronUp, Loader2,
} from 'lucide-react';
import {
  getModelHealth, getAllModelsStatus, retrainModelDomain,
  getModelRetrainJobs,
  type ModelHealthReport, type AllModelsStatus, type ModelDomainFullStatus,
  type ModelRetrainJob,
} from '../../services/api';

function StatusBadge({ status }: { status: string }) {
  const color = status === 'VALID' ? 'var(--accent-teal)' : status === 'DEGRADED' ? 'var(--accent-amber)' : 'var(--accent-coral)';
  const Icon = status === 'VALID' ? CheckCircle : status === 'DEGRADED' ? AlertTriangle : XCircle;
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold" style={{ backgroundColor: `${color}20`, color, border: `1px solid ${color}40` }}>
      <Icon className="w-3 h-3" /> {status}
    </span>
  );
}

function JobStatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; label: string }> = {
    queued: { color: 'var(--text-secondary)', label: 'QUEUED' },
    training: { color: 'var(--accent-blue)', label: 'TRAINING' },
    evaluating: { color: 'var(--accent-amber)', label: 'EVALUATING' },
    deployed: { color: 'var(--accent-teal)', label: 'DEPLOYED' },
    rejected: { color: 'var(--accent-amber)', label: 'REJECTED' },
    failed: { color: 'var(--accent-coral)', label: 'FAILED' },
  };
  const { color, label } = map[status] || { color: 'var(--text-secondary)', label: status.toUpperCase() };
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold uppercase" style={{ backgroundColor: `${color}15`, color }}>
      {status === 'training' && <Loader2 className="w-2.5 h-2.5 animate-spin" />}
      {label}
    </span>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded border border-[var(--border-color)] bg-[var(--bg-primary)] px-3 py-2">
      <div className="text-[9px] uppercase tracking-wider text-[var(--text-secondary)]">{label}</div>
      <div className={`mt-1 font-semibold text-[var(--text-primary)] normal-case tracking-normal text-[11px] ${mono ? 'font-mono' : ''}`}>{value}</div>
    </div>
  );
}

function DomainModelCard({
  domain,
  label,
  data,
  onRetrain,
  retrainBusy,
}: {
  domain: string;
  label: string;
  data: ModelDomainFullStatus;
  onRetrain: (domain: string) => void;
  retrainBusy: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const current = data.current;
  const hasArtifacts = current.artifacts_present;
  const metrics = current.metrics || {};
  const versions = data.versions || [];

  const metricsDisplay = domain === 'hotspot'
    ? `RMSE ${metrics.rmse ?? metrics.RMSE ?? '-'} | MAE ${metrics.mae ?? metrics.MAE ?? '-'} | R2 ${metrics.r2 ?? metrics.R2 ?? '-'}`
    : domain === 'risk'
    ? `Risk RMSE ${metrics.risk?.rmse ?? '-'} | Forecast RMSE ${metrics.forecast?.rmse ?? '-'}`
    : domain === 'criminal'
    ? `${metrics.n_criminals ?? metrics.training_rows ?? '-'} criminals | ${metrics.n_features ?? '-'} features`
    : '-';

  return (
    <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] overflow-hidden">
      {/* Header */}
      <div
        className="px-4 py-3 border-b border-[var(--border-color)] flex items-center justify-between cursor-pointer hover:bg-[var(--bg-primary)] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <Cpu className="w-4 h-4 text-[var(--accent-purple)]" />
          <span className="text-xs font-semibold text-[var(--text-primary)]">{label}</span>
          <StatusBadge status={hasArtifacts ? (data.is_stale ? 'DEGRADED' : 'VALID') : 'CRITICAL'} />
          {data.is_stale && (
            <span className="text-[9px] font-mono text-[var(--accent-amber)]">STALE</span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-mono text-[var(--text-secondary)]">
            {current.model_version ?? 'untrained'}
          </span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5 text-[var(--text-secondary)]" /> : <ChevronDown className="w-3.5 h-3.5 text-[var(--text-secondary)]" />}
        </div>
      </div>

      {/* Collapsed summary */}
      {!expanded && (
        <div className="px-4 py-2 flex items-center gap-4 text-[10px] text-[var(--text-secondary)]">
          <span>{current.algorithm}</span>
          <span>{current.training_rows} rows</span>
          <span>{versions.length} versions</span>
          {current.trained_at && <span>Trained {new Date(current.trained_at).toLocaleDateString()}</span>}
        </div>
      )}

      {/* Expanded detail */}
      {expanded && (
        <div className="px-4 py-3 space-y-3">
          {/* Key metrics grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <Stat label="Version" value={current.model_version ?? 'untrained'} mono />
            <Stat label="Algorithm" value={current.algorithm} />
            <Stat label="Last Trained" value={current.trained_at ? new Date(current.trained_at).toLocaleString() : 'never'} />
            <Stat label="Training Rows" value={String(current.training_rows ?? 0)} mono />
            <Stat label="Previous Version" value={current.previous_version ?? '-'} mono />
            <Stat label="Dataset Version" value={current.dataset_version ?? '-'} mono />
            <Stat label="Deployment" value={current.deployment_status ?? current.status} />
            <Stat label="Trainer" value={data.trainer_available ? 'Available' : 'Missing deps'} />
          </div>

          {/* Metrics */}
          <div className="text-[10px] font-mono text-[var(--text-secondary)] px-1">
            Metrics: {metricsDisplay}
          </div>

          {/* Retrain policy */}
          <div className="text-[9px] text-[var(--text-muted)] px-1">
            Policy: min {data.retrain_policy.min_new_records} new records | min {data.retrain_policy.min_dataset_change_pct}% change | min {data.retrain_policy.min_improvement_pct}% improvement
          </div>

          {/* Retrain button */}
          <div className="flex items-center gap-3">
            <button
              onClick={(e) => { e.stopPropagation(); onRetrain(domain); }}
              disabled={retrainBusy}
              className="inline-flex items-center gap-2 rounded border border-[#1E6FD9]/35 bg-[#1E6FD9]/15 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)] disabled:opacity-60 hover:bg-[#1E6FD9]/25 transition-colors"
            >
              <RotateCcw className={`h-3 w-3 ${retrainBusy ? 'animate-spin' : ''}`} />
              {retrainBusy ? 'Retraining...' : 'Retrain Model'}
            </button>
          </div>

          {/* Version history */}
          {versions.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-semibold text-[var(--text-primary)] uppercase tracking-wider">Version History</div>
              <div className="max-h-32 overflow-y-auto custom-scrollbar space-y-1">
                {[...versions].reverse().slice(0, 10).map((v, i) => (
                  <div key={i} className="flex items-center gap-3 text-[9px] font-mono px-2 py-1 rounded bg-[var(--bg-primary)] border border-[var(--border-color)]">
                    <span className="font-bold text-[var(--text-primary)]">{v.model_version}</span>
                    <JobStatusBadge status={v.status} />
                    <span className="text-[var(--text-secondary)]">{v.training_records} rows</span>
                    <span className="text-[var(--text-secondary)]">{new Date(v.trained_at).toLocaleDateString()}</span>
                    {v.improvement_pct != null && (
                      <span className={v.improvement_pct >= 0 ? 'text-[var(--accent-teal)]' : 'text-[var(--accent-coral)]'}>
                        {v.improvement_pct >= 0 ? '+' : ''}{v.improvement_pct.toFixed(1)}%
                      </span>
                    )}
                    {v.previous_version && <span className="text-[var(--text-muted)]">from {v.previous_version}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function JobsList({ jobs }: { jobs: ModelRetrainJob[] }) {
  if (jobs.length === 0) return null;
  return (
    <div className="rounded-lg border border-[var(--border-color)] bg-[var(--bg-secondary)] p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Clock className="w-4 h-4 text-[var(--accent-amber)]" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">Recent Retrain Jobs</span>
      </div>
      <div className="max-h-48 overflow-y-auto custom-scrollbar space-y-1">
        {jobs.map((job) => (
          <div key={job.id} className="flex items-center gap-3 text-[10px] font-mono px-2 py-1.5 rounded bg-[var(--bg-primary)] border border-[var(--border-color)]">
            <JobStatusBadge status={job.status} />
            <span className="font-bold text-[var(--text-primary)] uppercase">{job.model_name}</span>
            <span className="text-[var(--text-secondary)]">{job.trigger_type}</span>
            {job.previous_version && <span className="text-[var(--text-muted)]">{job.previous_version} → {job.new_version ?? '?'}</span>}
            {job.created_at && <span className="text-[var(--text-secondary)]">{new Date(job.created_at).toLocaleString()}</span>}
            {job.error_message && <span className="text-[var(--accent-coral)] truncate max-w-[200px]">{job.error_message}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ModelHealthPanel() {
  const [healthReport, setHealthReport] = useState<ModelHealthReport | null>(null);
  const [allModels, setAllModels] = useState<AllModelsStatus | null>(null);
  const [jobs, setJobs] = useState<ModelRetrainJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retrainBusy, setRetrainBusy] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [health, models, jobData] = await Promise.all([
        getModelHealth(),
        getAllModelsStatus(),
        getModelRetrainJobs(10),
      ]);
      setHealthReport(health);
      setAllModels(models);
      setJobs(jobData.jobs || []);
    } catch (e: any) {
      setError(e?.message || 'Failed to load model health');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRetrain = useCallback(async (domain: string) => {
    if (!confirm(`Retrain the ${domain} model? The current active model will remain in place if the candidate is not accepted.`)) return;
    setRetrainBusy((prev) => ({ ...prev, [domain]: true }));
    try {
      await retrainModelDomain(domain, `admin-manual-${domain}`);
      // Poll briefly to let the job start, then reload
      await new Promise((r) => setTimeout(r, 2000));
      await load();
    } catch (e: any) {
      alert(`Retrain failed: ${e?.message || 'Unknown error'}`);
    } finally {
      setRetrainBusy((prev) => ({ ...prev, [domain]: false }));
    }
  }, [load]);

  if (loading) return (
    <div className="flex items-center gap-2 text-[var(--text-secondary)] text-xs py-8 justify-center">
      <RefreshCw className="w-4 h-4 animate-spin" /> Loading model health...
    </div>
  );
  if (error) return <div className="text-[var(--accent-coral)] text-xs py-8 text-center">{error}</div>;

  const domains = allModels?.models || {};
  const domainLabels: Record<string, string> = {
    hotspot: 'Crime Hotspot Predictor',
    risk: 'District Risk & Forecast',
    criminal: 'Criminal Intelligence',
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-[var(--accent-purple)]" />
          <span className="text-sm font-semibold text-[var(--text-primary)]">ML Model Health</span>
          {healthReport && <StatusBadge status={healthReport.overall_status} />}
          {allModels && (
            <span className="text-[10px] font-mono text-[var(--text-muted)]">
              Auto-retrain: {allModels.auto_retrain_enabled ? 'ON' : 'OFF'}
            </span>
          )}
        </div>
        <button onClick={load} className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Health check cards (existing) */}
      {healthReport && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ModelHealthCard
            title="Hotspot Predictor"
            status={healthReport.hotspot.overall_status}
            loaded={healthReport.hotspot.model_loaded}
            checks={healthReport.hotspot.checks}
            validCount={healthReport.hotspot.valid_count}
            invalidCount={healthReport.hotspot.invalid_count}
          />
          <ModelHealthCard
            title="Risk & Forecast"
            status={healthReport.risk.overall_status}
            loaded={healthReport.risk.risk_model_loaded && healthReport.risk.forecast_model_loaded}
            checks={healthReport.risk.checks}
            validCount={healthReport.risk.valid_count}
            invalidCount={healthReport.risk.invalid_count}
            extraInfo={[
              { label: 'Risk Model', loaded: healthReport.risk.risk_model_loaded },
              { label: 'Forecast Model', loaded: healthReport.risk.forecast_model_loaded },
            ]}
          />
        </div>
      )}

      {/* Unified model management */}
      {Object.keys(domains).length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-[var(--accent-blue)]" />
            <span className="text-sm font-semibold text-[var(--text-primary)]">Model Management</span>
          </div>
          <div className="space-y-3">
            {Object.entries(domains).map(([key, data]) => (
              <DomainModelCard
                key={key}
                domain={key}
                label={domainLabels[key] || key}
                data={data}
                onRetrain={handleRetrain}
                retrainBusy={!!retrainBusy[key]}
              />
            ))}
          </div>
        </div>
      )}

      {/* Retrain jobs history */}
      <JobsList jobs={jobs} />
    </div>
  );
}

function ModelHealthCard({ title, status, loaded, checks, validCount, invalidCount, extraInfo }: {
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
