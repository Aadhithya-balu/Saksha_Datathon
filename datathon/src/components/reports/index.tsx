import React from 'react';
import { Download, FileText, RefreshCw, Search } from 'lucide-react';

export type ReportType = 'cases' | 'officers' | 'criminals' | 'evidence';

export interface ReportFiltersValue {
  reportType: ReportType;
  search: string;
  status: string;
  district: string;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
}

export interface ReportPreviewData {
  report_type: ReportType;
  headers: string[];
  filters: Record<string, string>;
  total: number;
  page: number;
  page_size: number;
  results: Array<Record<string, string | number | null>>;
}

const reportLabels: Record<ReportType, string> = {
  cases: 'Case Report',
  officers: 'Officer Report',
  criminals: 'Criminal Report',
  evidence: 'Evidence Report',
};

export const StatisticsCards: React.FC<{ stats: Record<string, number> }> = ({ stats }) => (
  <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
    {Object.entries(reportLabels).map(([key, label]) => (
      <div key={key} className="rounded-lg border border-border-color bg-[#111D35]/55 p-4">
        <p className="text-[9px] uppercase tracking-[0.24em] text-[#6A7A96]">{label}</p>
        <p className="mt-2 text-2xl font-bold text-white">{stats[key] ?? 0}</p>
      </div>
    ))}
  </div>
);

export const ReportCards: React.FC<{ active: ReportType; onSelect: (type: ReportType) => void }> = ({ active, onSelect }) => (
  <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
    {(Object.keys(reportLabels) as ReportType[]).map((type) => (
      <button
        key={type}
        onClick={() => onSelect(type)}
        className={`rounded-lg border p-3 text-left transition-colors ${active === type ? 'border-[#1E6FD9] bg-[#1E6FD9]/15 text-white' : 'border-border-color bg-[#0A1220]/70 text-[#A8B4CC] hover:border-[#1E6FD9]/50'}`}
      >
        <FileText className="h-4 w-4 text-[#4DA3FF]" />
        <span className="mt-3 block text-[10px] font-bold uppercase tracking-wider">{reportLabels[type]}</span>
      </button>
    ))}
  </div>
);

export const ReportFilters: React.FC<{
  value: ReportFiltersValue;
  onChange: (value: ReportFiltersValue) => void;
  onRefresh: () => void;
}> = ({ value, onChange, onRefresh }) => (
  <div className="grid grid-cols-1 md:grid-cols-5 gap-2 rounded-lg border border-border-color bg-[#111D35]/35 p-3">
    <label className="relative md:col-span-2">
      <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-[#6A7A96]" />
      <input value={value.search} onChange={(e) => onChange({ ...value, search: e.target.value })} placeholder="Search records" className="w-full rounded bg-[#060B13] border border-border-color py-2 pl-9 pr-3 text-xs text-white outline-none focus:border-[#1E6FD9]" />
    </label>
    <input value={value.status} onChange={(e) => onChange({ ...value, status: e.target.value })} placeholder="Status filter" className="rounded bg-[#060B13] border border-border-color px-3 py-2 text-xs text-white outline-none focus:border-[#1E6FD9]" />
    <input value={value.district} onChange={(e) => onChange({ ...value, district: e.target.value })} placeholder="District filter" className="rounded bg-[#060B13] border border-border-color px-3 py-2 text-xs text-white outline-none focus:border-[#1E6FD9]" />
    <button onClick={onRefresh} className="inline-flex items-center justify-center gap-2 rounded bg-[#1E6FD9]/15 border border-[#1E6FD9]/35 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white">
      <RefreshCw className="h-3.5 w-3.5" /> Refresh
    </button>
  </div>
);

export const ExportButton: React.FC<{ label: string; onClick: () => void; disabled?: boolean }> = ({ label, onClick, disabled }) => (
  <button onClick={onClick} disabled={disabled} className="inline-flex items-center justify-center gap-2 rounded bg-[#0E9E78]/15 border border-[#0E9E78]/35 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-white disabled:opacity-40">
    <Download className="h-3.5 w-3.5 text-[#0E9E78]" /> {label}
  </button>
);

export const ReportTable: React.FC<{ data: ReportPreviewData | null; loading: boolean; error: string | null }> = ({ data, loading, error }) => (
  <div className="min-h-[260px] overflow-auto rounded-lg border border-border-color bg-[#111D35]/25 custom-scrollbar">
    {loading && <div className="p-10 text-center text-[10px] uppercase tracking-widest text-[#6A7A96]">Loading live backend report</div>}
    {error && !loading && <div className="p-10 text-center text-[10px] uppercase tracking-widest text-amber-400">{error}</div>}
    {!loading && !error && data && data.results.length === 0 && <div className="p-10 text-center text-[10px] uppercase tracking-widest text-[#6A7A96]">No records match the current filters</div>}
    {!loading && !error && data && data.results.length > 0 && (
      <table className="w-full border-collapse text-left text-[10px]">
        <thead className="bg-[#060B13] text-[#6A7A96] uppercase tracking-wider">
          <tr>{data.headers.map((header) => <th key={header} className="px-3 py-3 whitespace-nowrap">{header.replace(/_/g, ' ')}</th>)}</tr>
        </thead>
        <tbody className="divide-y divide-white/5 text-[#A8B4CC]">
          {data.results.map((row, index) => (
            <tr key={index} className="hover:bg-white/[0.03]">
              {data.headers.map((header) => <td key={header} className="px-3 py-3 max-w-[280px] truncate">{row[header] ?? ''}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);

export const ReportPreview: React.FC<{ data: ReportPreviewData | null }> = ({ data }) => (
  <div className="rounded-lg border border-border-color bg-[#0A1220]/70 p-4">
    <p className="text-[9px] uppercase tracking-[0.24em] text-[#6A7A96]">Preview</p>
    <p className="mt-2 text-sm font-bold text-white">{data ? `${reportLabels[data.report_type]} - ${data.total} matching records` : 'Select filters to preview a report'}</p>
    <p className="mt-1 text-[10px] text-[#6A7A96]">Generated from authenticated backend APIs with the current filter set.</p>
  </div>
);
