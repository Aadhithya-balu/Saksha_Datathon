import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { downloadSecureDossier } from '../utils/downloader';
import { listReports, type ReportRecord } from '../services/api';
import { Search, Download, FileText, Shield } from 'lucide-react';

const getReportClassification = (report: ReportRecord) => {
  if (report.status === 'failed') return 'RESTRICTED';
  if (report.template.toLowerCase().includes('anomaly')) return 'SECRET';
  if (report.template.toLowerCase().includes('network')) return 'CLASSIFIED';
  return 'CONFIDENTIAL';
};

export const Reports: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [reports, setReports] = useState<ReportRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    void listReports()
      .then((response) => {
        if (!isMounted) return;
        setReports(response.results);
        setLoadError(null);
      })
      .catch((error) => {
        if (!isMounted) return;
        setReports([]);
        setLoadError(error instanceof Error ? error.message : 'Failed to load reports');
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const filteredReports = reports.filter((report) => {
    const query = searchQuery.toLowerCase();
    return (
      report.template.toLowerCase().includes(query) ||
      report.status.toLowerCase().includes(query) ||
      report.format.toLowerCase().includes(query) ||
      (report.district ?? '').toLowerCase().includes(query)
    );
  });

  const handleDownload = (report: ReportRecord) => {
    setDownloadingId(report.id);
    const badgeId = user?.badgeId || 'STATE POLICE';
    const officerName = user?.name || 'Authenticated Officer';

    addLog(officerName, badgeId, 'EXPORT', `Downloaded backend report: ${report.template}`);

    downloadSecureDossier(
      report.template,
      {
        reportId: report.id,
        template: report.template,
        district: report.district ?? 'Statewide',
        status: report.status,
        format: report.format,
        fileUrl: report.file_url ?? 'Backend file URL not yet generated',
        createdAt: report.created_at,
      },
      `${getReportClassification(report)} - ID: ${badgeId}`
    );

    setDownloadingId(null);
  };

  const getStampColor = (stamp: string) => {
    switch (stamp) {
      case 'SECRET': return 'text-red-400 bg-red-950/20 border-red-900/30';
      case 'CLASSIFIED': return 'text-purple-400 bg-purple-950/20 border-purple-900/30';
      case 'CONFIDENTIAL': return 'text-blue-400 bg-blue-950/20 border-blue-900/30';
      case 'RESTRICTED': return 'text-amber-400 bg-amber-950/20 border-amber-900/30';
      default: return 'text-slate-400 bg-slate-900/20 border-slate-800/30';
    }
  };

  return (
    <div className="h-[84vh] flex flex-col gap-5 p-1 md:p-3 select-none bg-[#060b13] font-mono">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-md font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#1E6FD9] animate-pulse" />
            Reports & Intelligence Dossiers
          </h2>
          <p className="text-[9.5px] font-mono text-[#6A7A96] mt-0.5">
            CLASSIFIED DOCUMENT EXPORT CONSOLE - BACKEND REPORT RECORDS
          </p>
          {loadError && <p className="mt-1 text-[9px] text-amber-400 uppercase tracking-wider">{loadError}</p>}
        </div>

        <div className="w-64 flex items-center relative text-xs">
          <input
            type="text"
            placeholder="Search report database..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-[#111D35]/50 border border-border-color rounded text-white outline-none focus:border-[#1E6FD9] text-[10.5px]"
          />
          <Search className="absolute left-2.5 w-3.5 h-3.5 text-[#6A7A96]" />
        </div>
      </div>

      <div className="flex-grow w-full bg-[#111D35]/25 border border-border-color rounded-xl overflow-hidden flex flex-col justify-between">
        <div className="overflow-y-auto flex-grow custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-900 bg-[#0a1220]/75 text-[9px] uppercase tracking-wider text-[#6A7A96] font-bold">
                <th className="py-3 px-4">Classification</th>
                <th className="py-3 px-4">Document Title</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center">Format</th>
                <th className="py-3 px-4">Generated Date</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-[10px]">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 uppercase tracking-widest text-[9px]">
                    Loading backend report catalog
                  </td>
                </tr>
              )}

              {!isLoading && filteredReports.map((report) => {
                const stamp = getReportClassification(report);
                return (
                  <tr key={report.id} className="hover:bg-slate-900/20 text-[#A8B4CC] hover:text-white transition-colors">
                    <td className="py-3.5 px-4 shrink-0">
                      <span className={`px-2 py-0.5 border rounded text-[7.5px] font-bold uppercase tracking-wider ${getStampColor(stamp)}`}>
                        {stamp}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-bold text-white uppercase tracking-wide">
                      {report.template}{report.district ? ` - ${report.district}` : ''}
                    </td>
                    <td className="py-3.5 px-4 text-[#A8B4CC] uppercase">{report.status}</td>
                    <td className="py-3.5 px-4 text-center text-slate-400 font-bold uppercase">{report.format}</td>
                    <td className="py-3.5 px-4 text-slate-500">
                      {new Date(report.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleDownload(report)}
                        disabled={downloadingId !== null}
                        className="py-1 px-3 bg-[#1E6FD9]/15 hover:bg-[#1E6FD9]/30 border border-[#1e6fd9]/25 hover:border-[#1E6FD9]/50 text-white font-bold uppercase rounded text-[8.5px] tracking-wider transition-all flex items-center justify-center gap-1.5 ml-auto cursor-pointer disabled:opacity-40"
                      >
                        {downloadingId === report.id ? (
                          <>
                            <div className="w-2.5 h-2.5 border-t-2 border-white rounded-full animate-spin" />
                            <span>Decrypting</span>
                          </>
                        ) : (
                          <>
                            <Download className="w-3 h-3 text-[#1E6FD9]" />
                            <span>Download</span>
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                );
              })}

              {!isLoading && filteredReports.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 uppercase tracking-widest text-[9px]">
                    No corresponding reports found in backend catalog
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="p-3 bg-slate-950/40 border-t border-border-color text-[8px] text-slate-500 flex items-center justify-between">
          <span className="flex items-center gap-1">
            <Shield className="w-3 h-3 text-[#0e9e78]" />
            Report records are loaded from the authenticated backend reports API.
          </span>
          <span>SYSTEM TIME HORIZON COMPLIANCE: 2026.01</span>
        </div>
      </div>
    </div>
  );
};

export default Reports;