import React, { useCallback, useEffect, useRef, useState } from 'react';
import { FileUp, ListChecks, UploadCloud } from 'lucide-react';
import {
  analyzeImportFile,
  commitImportFile,
  getImportEntities,
  listImportJobs,
  type ImportAnalysis,
  type ImportCommitResult,
  type ImportEntitySpec,
  type ImportJobSummary,
} from '../../services/api';

const humanizeEntityType = (value: string) =>
  value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export const DataImportPanel: React.FC = () => {
  const [entities, setEntities] = useState<ImportEntitySpec[]>([]);
  const [profiles, setProfiles] = useState<string[]>(['standard']);
  const [maxRows, setMaxRows] = useState(5000);
  const [entityType, setEntityType] = useState('victims');
  const [profile, setProfile] = useState('standard');
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<ImportAnalysis | null>(null);
  const [result, setResult] = useState<ImportCommitResult | null>(null);
  const [jobs, setJobs] = useState<ImportJobSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const refreshJobs = useCallback(() => {
    void listImportJobs(10)
      .then((response) => setJobs(response.results ?? []))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    getImportEntities()
      .then((response) => {
        setEntities(response.entities ?? []);
        setProfiles((response.profiles ?? []).map((p) => p.profile));
        if (typeof response.max_rows === 'number') setMaxRows(response.max_rows);
        if ((response.entities ?? []).length > 0) {
          setEntityType(response.entities[0].entity_type);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load import entities'));
    refreshJobs();
  }, [refreshJobs]);

  const selectedEntity = entities.find((e) => e.entity_type === entityType);
  const requiredColumns = selectedEntity?.columns.filter((c) => c.required).map((c) => c.name) ?? [];
  const optionalColumns = selectedEntity?.columns.filter((c) => !c.required).map((c) => c.name) ?? [];

  const runAnalysis = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setAnalysis(null);
    setResult(null);
    try {
      setAnalysis(await analyzeImportFile(file, entityType, profile));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyse file');
    } finally {
      setBusy(false);
    }
  };

  const runCommit = async (dryRun: boolean) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await commitImportFile(file, entityType, profile, dryRun);
      if (dryRun) {
        // Dry-run responses carry the same shape as /preview.
        setAnalysis(response as unknown as ImportAnalysis);
      } else {
        setResult(response);
      }
      refreshJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to commit import');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border-color bg-[var(--bg-tertiary)]/35 p-4 space-y-3">
        <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)]">
          <UploadCloud className="h-4 w-4 text-[#4DA3FF]" /> Bulk legacy data ingestion
        </p>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <label className="text-[10px] uppercase text-[var(--text-muted)]">
            Entity
            <select
              value={entityType}
              onChange={(e) => { setEntityType(e.target.value); setAnalysis(null); setResult(null); }}
              className="mt-1 w-full rounded bg-[var(--bg-primary)] border border-border-color px-2 py-2 text-xs text-[var(--text-primary)]"
            >
              {entities.map((e) => (
                <option key={e.entity_type} value={e.entity_type}>{humanizeEntityType(e.entity_type)}</option>
              ))}
            </select>
          </label>
          <label className="text-[10px] uppercase text-[var(--text-muted)]">
            Column profile
            <select
              value={profile}
              onChange={(e) => { setProfile(e.target.value); setAnalysis(null); }}
              className="mt-1 w-full rounded bg-[var(--bg-primary)] border border-border-color px-2 py-2 text-xs text-[var(--text-primary)]"
            >
              {profiles.map((p) => (
                <option key={p} value={p}>{p === 'cctns' ? 'CCTNS / ICJS' : p}</option>
              ))}
            </select>
          </label>
          <label className="text-[10px] uppercase text-[var(--text-muted)] md:col-span-2">
            CSV or XLSX file (max {maxRows.toLocaleString()} rows)
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => { setFile(e.target.files?.[0] ?? null); setAnalysis(null); setResult(null); }}
              className="mt-1 w-full rounded bg-[var(--bg-primary)] border border-border-color px-2 py-1.5 text-xs text-[var(--text-secondary)] file:mr-2 file:rounded file:border-0 file:bg-[#1E6FD9]/20 file:px-2 file:py-1 file:text-[10px] file:uppercase file:text-[var(--text-primary)]"
            />
          </label>
        </div>

        {selectedEntity && (
          <p className="text-[9px] text-[var(--text-muted)] leading-relaxed">
            <span className="font-bold uppercase">Required:</span> {requiredColumns.join(', ') || '—'}
            {' · '}
            <span className="font-bold uppercase">Optional:</span> {optionalColumns.slice(0, 8).join(', ') || '—'}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => void runAnalysis()}
            disabled={!file || busy}
            className="inline-flex items-center gap-2 rounded border border-[#1E6FD9]/35 bg-[#1E6FD9]/15 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)] disabled:opacity-40"
          >
            <ListChecks className="h-3.5 w-3.5" /> Validate &amp; Preview Mapping
          </button>
          <button
            onClick={() => void runCommit(true)}
            disabled={!file || busy}
            className="inline-flex items-center gap-2 rounded border border-border-color bg-[var(--bg-secondary)] px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-secondary)] disabled:opacity-40"
          >
            Dry Run
          </button>
          <button
            onClick={() => void runCommit(false)}
            disabled={!file || busy || (analysis !== null && analysis.missing_required_columns.length > 0)}
            title={analysis && analysis.missing_required_columns.length > 0 ? 'Resolve missing required columns first' : undefined}
            className="inline-flex items-center gap-2 rounded border border-[#0E9E78]/35 bg-[#0E9E78]/15 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)] disabled:opacity-40"
          >
            <FileUp className="h-3.5 w-3.5" /> Commit Import
          </button>
        </div>
      </div>

      {error && <div className="rounded border border-amber-500/30 px-3 py-2 text-[10px] uppercase tracking-wider text-amber-300">{error}</div>}

      {analysis && (
        <div className="rounded-lg border border-border-color bg-[var(--bg-secondary)]/60 p-4 space-y-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)]">
            Validation report · {analysis.filename} · {analysis.total_rows} rows · profile {analysis.profile}
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px] font-mono">
            <div className="rounded border border-border-color p-2"><span className="block text-[var(--text-muted)] uppercase">Valid rows</span><span className="text-[#0E9E78] font-bold">{analysis.estimated_valid_rows}</span></div>
            <div className="rounded border border-border-color p-2"><span className="block text-[var(--text-muted)] uppercase">Invalid rows</span><span className="text-amber-400 font-bold">{analysis.estimated_invalid_rows}</span></div>
            <div className="rounded border border-border-color p-2"><span className="block text-[var(--text-muted)] uppercase">Mapped columns</span><span className="font-bold">{Object.keys(analysis.column_mapping ?? {}).length}</span></div>
            <div className="rounded border border-border-color p-2"><span className="block text-[var(--text-muted)] uppercase">Missing required</span><span className={analysis.missing_required_columns?.length ? 'text-red-400 font-bold' : 'font-bold'}>{analysis.missing_required_columns?.length ?? 0}</span></div>
          </div>
          {(analysis.missing_required_columns?.length ?? 0) > 0 && (
            <p className="text-[9px] text-red-400 uppercase">Missing required columns: {analysis.missing_required_columns.join(', ')}</p>
          )}
          {(analysis.unmapped_headers?.length ?? 0) > 0 && (
            <p className="text-[9px] text-amber-300 break-all">
              <span className="uppercase font-bold">Unmapped headers:</span> {analysis.unmapped_headers.join(' · ')}
            </p>
          )}
          {Object.keys(analysis.column_mapping ?? {}).length > 0 && (
            <p className="text-[9px] text-[var(--text-muted)] break-all">
              <span className="uppercase font-bold">Auto-mapped:</span>{' '}
              {Object.entries(analysis.column_mapping).map(([src, dst]) => `${src}→${dst}`).join(' · ')}
            </p>
          )}
          {(analysis.validation_report ?? []).slice(0, 8).map((item) => (
            <div key={item.row_number} className="rounded border border-border-color px-2 py-1.5 text-[9px]">
              <span className="font-bold uppercase text-[var(--text-muted)]">Row {item.row_number}</span>
              {(item.errors ?? []).map((err, i) => <span key={`e${i}`} className="ml-2 text-red-400">{err}</span>)}
              {(item.warnings ?? []).map((warning, i) => <span key={`w${i}`} className="ml-2 text-amber-300">{warning}</span>)}
            </div>
          ))}
          {analysis.truncated_report && <p className="text-[9px] text-amber-300 uppercase">Report truncated — remaining rows not shown.</p>}
        </div>
      )}

      {result && (
        <div className="rounded-lg border border-[#0E9E78]/30 bg-[#0E9E78]/5 p-4 space-y-2">
          <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)]">
            Job {result.job_id.slice(0, 8)} · {result.status.toUpperCase()} · imported {result.imported_rows}, failed {result.failed_rows} of {result.total_rows}
          </p>
          {(result.validation_report ?? []).slice(0, 8).map((item) => (
            <div key={item.row_number} className="text-[9px]">
              <span className="font-bold uppercase text-[var(--text-muted)]">Row {item.row_number}</span>
              {(item.errors ?? []).map((err, i) => <span key={`e${i}`} className="ml-2 text-red-400">{err}</span>)}
            </div>
          ))}
        </div>
      )}

      <div className="rounded-lg border border-border-color bg-[var(--bg-tertiary)]/25 p-4">
        <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-primary)] mb-2">Recent import jobs</p>
        {jobs.length === 0 ? (
          <p className="text-[9px] uppercase text-[var(--text-muted)]">No imports recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full text-left text-[9px] whitespace-nowrap">
            <thead className="text-[var(--text-muted)] uppercase">
              <tr><th className="py-1 pr-3">When</th><th className="py-1 pr-3">Entity</th><th className="py-1 pr-3">File</th><th className="py-1 pr-3">Status</th><th className="py-1 pr-3">OK</th><th className="py-1">Failed</th></tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-primary)] text-[var(--text-secondary)]">
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td className="py-1.5 pr-3">{job.created_at ? new Date(job.created_at).toLocaleString() : '—'}</td>
                  <td className="py-1.5 pr-3 uppercase">{job.entity_type}</td>
                  <td className="py-1.5 pr-3 truncate max-w-[180px]">{job.filename}</td>
                  <td className={`py-1.5 pr-3 uppercase ${job.status === 'completed' ? 'text-[#0E9E78]' : job.status === 'failed' ? 'text-red-400' : 'text-amber-300'}`}>{job.status}</td>
                  <td className="py-1.5 pr-3">{job.imported_rows}</td>
                  <td className="py-1.5">{job.failed_rows}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default DataImportPanel;
