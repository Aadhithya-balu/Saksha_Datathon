import React, { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { downloadSecureDossier } from '../utils/downloader';
import { Search, Download, FileText, CheckCircle, Shield, AlertTriangle } from 'lucide-react';

interface ReportItem {
  id: string;
  name: string;
  category: 'TELEMETRY' | 'GEOSPATIAL' | 'NETWORK' | 'OFFENDER' | 'ANOMALY';
  securityStamp: 'CONFIDENTIAL' | 'CLASSIFIED' | 'SECRET' | 'RESTRICTED';
  fileSize: string;
  generatedDate: string;
  payload: any;
}

const REPORT_DATABASE: ReportItem[] = [
  {
    id: 'rep-101',
    name: 'KSP General Dashboard Telemetry Briefing',
    category: 'TELEMETRY',
    securityStamp: 'CONFIDENTIAL',
    fileSize: '4.8 KB',
    generatedDate: '2026-07-06 18:30:12',
    payload: {
      reportType: 'General Dashboard Telemetry Summary',
      totalCrimesTracked: '12,543',
      solvedCrimesTracked: '7,892',
      solvedRatio: '62.9%',
      activeHotspots: '32 Active Beat Nodes',
      highRiskDistricts: '17 Monitored Sectors',
      repeatOffendersSurveillance: '153 Registered'
    }
  },
  {
    id: 'rep-102',
    name: 'Statewide Incident Hotspots GeoJSON Overlay',
    category: 'GEOSPATIAL',
    securityStamp: 'CLASSIFIED',
    fileSize: '12.4 KB',
    generatedDate: '2026-07-06 17:15:44',
    payload: {
      type: 'FeatureCollection',
      dataset: 'Statewide coordinate nodes',
      features: [
        { type: 'Feature', geometry: { type: 'Point', coordinates: [77.5946, 12.9716] }, properties: { name: 'Bengaluru Urban', threat: '91%' } },
        { type: 'Feature', geometry: { type: 'Point', coordinates: [76.6394, 12.2958] }, properties: { name: 'Mysuru', threat: '54%' } },
        { type: 'Feature', geometry: { type: 'Point', coordinates: [76.8343, 17.3297] }, properties: { name: 'Kalaburagi', threat: '72%' } }
      ]
    }
  },
  {
    id: 'rep-103',
    name: 'Suspect Relationship & Association Matrix',
    category: 'NETWORK',
    securityStamp: 'SECRET',
    fileSize: '8.2 KB',
    generatedDate: '2026-07-06 16:45:00',
    payload: {
      subject: 'Interstate Gang Alliance network mapping',
      nodesCount: 10,
      centerFocusNode: 'Gang Leader Ramu Swamy',
      links: [
        { accomplice: 'Vikram Yadav', channel: 'Virtual ledger money transfer' },
        { accomplice: 'Sayed Ibrahim', channel: 'Port corridor logistics' },
        { accomplice: 'Karthik Gowda', channel: 'Safehouse supply line' }
      ]
    }
  },
  {
    id: 'rep-104',
    name: 'Biometric Offender Profile - Ramu Swamy',
    category: 'OFFENDER',
    securityStamp: 'CONFIDENTIAL',
    fileSize: '3.1 KB',
    generatedDate: '2026-07-06 15:20:10',
    payload: {
      offenderId: 'off-501',
      name: 'Ramu Swamy',
      alias: 'Kodaikanal Ramu',
      age: 44,
      status: 'ACTIVE',
      classification: 'A-CATEGORY',
      districtsActive: ['Mysuru', 'Bengaluru Urban', 'Hassan'],
      gangSyndicate: 'Interstate Decoit Gang B'
    }
  },
  {
    id: 'rep-105',
    name: 'Cyber Fraud Financial Laundering Anomalies Log',
    category: 'ANOMALY',
    securityStamp: 'SECRET',
    fileSize: '15.6 KB',
    generatedDate: '2026-07-06 14:02:11',
    payload: {
      incidentsType: 'Multiple ATM spoofed transactions',
      trackedLocations: ['Indiranagar Main St', 'Whitefield Sector C'],
      totalDivergenceRatio: '+310% Standard Deviation',
      riskEscalationLevel: 'CRITICAL CR1'
    }
  }
];

export const Reports: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const filteredReports = REPORT_DATABASE.filter(r => 
    r.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDownload = (report: ReportItem) => {
    setDownloadingId(report.id);
    const badgeId = user?.badgeId || 'SCRB-7740';
    const officerName = user?.name || 'Inspector System';

    // Log to secure audit trail hook
    addLog(
      officerName,
      badgeId,
      'EXPORT',
      `Downloaded dossier report: ${report.name}`
    );

    // Simulate 350ms cryptographic download lock before triggering browser download
    setTimeout(() => {
      downloadSecureDossier(
        report.name,
        report.payload,
        `${report.securityStamp} - ID: ${badgeId}`
      );
      setDownloadingId(null);
    }, 350);
  };

  const getStampColor = (stamp: ReportItem['securityStamp']) => {
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
      
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-white/5 pb-4">
        <div>
          <h2 className="text-md font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#1E6FD9] animate-pulse" />
            Reports & Intelligence Dossiers
          </h2>
          <p className="text-[9.5px] font-mono text-[#6A7A96] mt-0.5">
            CLASSIFIED DOCUMENT EXPORT CONSOLE — SECURE CRYPTO-SIGNED POLICE RECORD FILES
          </p>
        </div>

        {/* Search controls */}
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

      {/* Main Reports Index Table */}
      <div className="flex-grow w-full bg-[#111D35]/25 border border-border-color rounded-xl overflow-hidden flex flex-col justify-between">
        
        <div className="overflow-y-auto flex-grow custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-900 bg-[#0a1220]/75 text-[9px] uppercase tracking-wider text-[#6A7A96] font-bold">
                <th className="py-3 px-4">Classification</th>
                <th className="py-3 px-4">Document Title</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-center">File Size</th>
                <th className="py-3 px-4">Generated Date</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-[10px]">
              {filteredReports.map((report) => (
                <tr key={report.id} className="hover:bg-slate-900/20 text-[#A8B4CC] hover:text-white transition-colors">
                  
                  {/* Security stamp badge */}
                  <td className="py-3.5 px-4 shrink-0">
                    <span className={`px-2 py-0.5 border rounded text-[7.5px] font-bold uppercase tracking-wider ${getStampColor(report.securityStamp)}`}>
                      {report.securityStamp}
                    </span>
                  </td>

                  {/* Report Name */}
                  <td className="py-3.5 px-4 font-bold text-white uppercase tracking-wide">
                    {report.name}
                  </td>

                  {/* Category */}
                  <td className="py-3.5 px-4 text-[#A8B4CC]">
                    {report.category}
                  </td>

                  {/* Size */}
                  <td className="py-3.5 px-4 text-center text-slate-400 font-bold">
                    {report.fileSize}
                  </td>

                  {/* Date */}
                  <td className="py-3.5 px-4 text-slate-500">
                    {report.generatedDate}
                  </td>

                  {/* Download Action button */}
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
              ))}

              {filteredReports.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 uppercase tracking-widest text-[9px]">
                    No corresponding reports found in catalog
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Footer legal disclosure */}
        <div className="p-3 bg-slate-950/40 border-t border-border-color text-[8px] text-slate-500 flex items-center justify-between">
          <span className="flex items-center gap-1">
            <Shield className="w-3 h-3 text-[#0e9e78]" />
            All telemetry documents are encrypted on disk and embedded with the requesting officer's badge watermarks.
          </span>
          <span>SYSTEM TIME HORIZON COMPLIANCE: 2026.01</span>
        </div>

      </div>

    </div>
  );
};

export default Reports;
