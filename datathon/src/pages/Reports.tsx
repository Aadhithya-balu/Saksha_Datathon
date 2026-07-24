import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { apiRequest } from '../services/api';
import {
  ExportButton,
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
        apiRequest<Record<string, number>>('/reports/statistics/summary'),
        apiRequest<ReportPreviewData>(`/reports/${filters.reportType}?${query}`),
      ]);
      setStats(statsResponse);
      setPreview(previewResponse);
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

  const download = async (format: 'pdf' | 'csv') => {
    setExporting(format);
    setError(null);
    try {
      await apiRequest(`/reports/${filters.reportType}/generate?export_format=${format}&${query}`, { method: 'POST' });
      const { accessToken, API_BASE_URL } = await import('../services/api').then(m => ({ 
        accessToken: m.getStoredTokens().accessToken, 
        API_BASE_URL: m.API_BASE_URL 
      }));
      const response = await fetch(`${API_BASE_URL}/reports/${filters.reportType}/export/${format}?${query}`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined
      });
      if (!response.ok) throw new Error('Failed to download report');
      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') ?? '';
      const match = disposition.match(/filename="([^"]+)"/);
      const filename = match?.[1] ?? `saksha_${filters.reportType}_report.${format}`;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
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
          <ExportButton label={exporting === 'pdf' ? 'Preparing PDF' : 'Download PDF'} disabled={!!exporting} onClick={() => void download('pdf')} />
          <ExportButton label={exporting === 'csv' ? 'Preparing CSV' : 'Download CSV'} disabled={!!exporting} onClick={() => void download('csv')} />
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
