import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { API_BASE_URL, getStoredTokens } from '../services/api';
import {
  ExportButton,
  ExportMenu,
  ReportCards,
  ReportFilters,
  ReportPreview,
  ReportTable,
  StatisticsCards,
  type ReportFiltersValue,
  type ReportPreviewData,
  type ReportType,
} from '../components/reports';

const buildQuery = (filters: ReportFiltersValue) => {
  const params = new URLSearchParams();
  if (filters.search) params.set('search', filters.search);
  if (filters.status) params.set('status', filters.status);
  if (filters.district) params.set('district', filters.district);
  params.set('sort_by', filters.sortBy);
  params.set('sort_order', filters.sortOrder);
  params.set('page_size', '50');
  return params.toString();
};

const authedFetch = async (path: string, options: RequestInit = {}) => {
  const { accessToken } = getStoredTokens();
  const headers = new Headers(options.headers ?? {});
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = await response.json();
      message = body?.error?.message ?? body?.detail ?? message;
    } catch {
      message = await response.text();
    }
    throw new Error(message || 'Request failed');
  }
  return response;
};

export const Reports: React.FC = () => {
  const [filters, setFilters] = useState<ReportFiltersValue>({
    reportType: 'cases',
    search: '',
    status: '',
    district: '',
    sortBy: 'created_at',
    sortOrder: 'desc',
  });
  const [stats, setStats] = useState<Record<string, number>>({});
  const [preview, setPreview] = useState<ReportPreviewData | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => buildQuery(filters), [filters]);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsResponse, previewResponse] = await Promise.all([
        authedFetch('/reports/statistics/summary'),
        authedFetch(`/reports/${filters.reportType}?${query}`),
      ]);
      setStats(await statsResponse.json());
      setPreview(await previewResponse.json());
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : 'Failed to load report');
    } finally {
      setLoading(false);
    }
  }, [filters.reportType, query]);

  useEffect(() => {
    void loadPreview();
  }, [loadPreview]);

  const selectReportType = (reportType: ReportType) => {
    setFilters((current) => ({ ...current, reportType, status: '', sortBy: 'created_at' }));
  };

  const download = async (format: 'pdf' | 'csv' | 'docx' | 'txt') => {
    setExporting(format);
    setError(null);
    try {
      await authedFetch(`/reports/${filters.reportType}/generate?export_format=${format}&${query}`, { method: 'POST' });
      const response = await authedFetch(`/reports/${filters.reportType}/export/${format}?${query}`);
      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') ?? '';
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match?.[1] ?? `saksha_${filters.reportType}_report.${format}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      setTimeout(() => {
        document.body.removeChild(anchor);
        URL.revokeObjectURL(url);
      }, 300);
      await loadPreview();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to export ${format.toUpperCase()}`);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="min-h-[84vh] space-y-4 p-1 md:p-3 bg-[#060b13] font-mono">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-3 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-md font-bold text-white uppercase tracking-wider">Administrative Reporting</h2>
          <p className="mt-1 text-[9.5px] uppercase tracking-[0.2em] text-[#6A7A96]">Live case, officer, criminal, and evidence exports</p>
        </div>
        <div className="flex gap-2">
          <ExportMenu disabled={!!exporting} exportingFormat={exporting} onExport={(fmt) => void download(fmt)} />
        </div>
      </div>

      <StatisticsCards stats={stats} />
      <ReportCards active={filters.reportType} onSelect={selectReportType} />
      <ReportFilters value={filters} onChange={setFilters} onRefresh={() => void loadPreview()} />
      <ReportPreview data={preview} />
      <ReportTable data={preview} loading={loading} error={error} />
    </div>
  );
};

export default Reports;
