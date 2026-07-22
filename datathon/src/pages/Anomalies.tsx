import React, { useEffect, useState } from 'react';
import type { CrimeAlert } from '../store/alertStore';
import { getAnomalies } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Eye, ShieldAlert, CheckCircle, Search, Filter, Calendar, MapPin, HardDrive } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const Anomalies: React.FC = () => {
  const [alerts, setAlerts] = useState<CrimeAlert[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { user } = useAuthStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState<'ALL' | 'HIGH' | 'WATCH'>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<'ALL' | 'PENDING' | 'REVIEWED' | 'ESCALATED'>('ALL');
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    void getAnomalies()
      .then((response) => {
        if (!isMounted) return;
        const mappedAlerts = response.anomalies.map<CrimeAlert>((item, index) => ({
          id: item.case_id,
          firNumber: item.case_id,
          district: 'Backend',
          station: 'Saksha Analytics',
          crimeType: item.label,
          offenceDetails: item.reason,
          anomalyScore: Math.round(item.score * 100),
          deviationPercent: Math.round(item.score * 100),
          severity: item.score >= 0.8 ? 'HIGH' : 'WATCH',
          timestamp: new Date(Date.now() - index * 3600000).toISOString(),
          status: 'PENDING',
          featureBreakdown: {
            'Anomaly Score': Math.round(item.score * 100),
            'Backend Evidence': Math.max(40, Math.round(item.score * 90)),
          },
        }));
        setAlerts(mappedAlerts);
        setSelectedAlertId(mappedAlerts[0]?.id ?? null);
        setLoadError(null);
      })
      .catch((error) => {
        if (!isMounted) return;
        setAlerts([]);
        setSelectedAlertId(null);
        setLoadError(error instanceof Error ? error.message : 'Failed to load anomalies');
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const reviewAlert = (id: string, reviewer: string) => setAlerts((current) => current.map((alert) => alert.id === id ? { ...alert, status: 'REVIEWED', assignedOfficer: reviewer } : alert));
  const escalateAlert = (id: string, reviewer: string) => setAlerts((current) => current.map((alert) => alert.id === id ? { ...alert, status: 'ESCALATED', severity: 'HIGH', assignedOfficer: reviewer } : alert));

  // Filter logic
  const filteredAlerts = alerts.filter(alert => {
    const matchesSearch = alert.firNumber.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          alert.crimeType.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          alert.district.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesSeverity = selectedSeverity === 'ALL' || alert.severity === selectedSeverity;
    const matchesStatus = selectedStatus === 'ALL' || alert.status === selectedStatus;

    return matchesSearch && matchesSeverity && matchesStatus;
  });

  const activeAlert = alerts.find(a => a.id === selectedAlertId) || filteredAlerts[0] || null;

  return (
    <div className="h-[84vh] flex flex-col gap-4 p-1 md:p-3 select-none">
      
      {/* Search Filter Top HUD */}
      {loadError && <div className="text-[9px] font-mono text-amber-400 uppercase">{loadError}</div>}
      <div className="bg-secondary-bg/50 border border-border-color p-4 rounded-card flex flex-col md:flex-row items-center gap-4 text-xs font-mono justify-between">
        
        {/* Search input */}
        <div className="w-full md:w-1/3 flex items-center relative">
          <input
            type="text"
            placeholder="Search FIR id, category, district..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950/70 text-white border border-border-color focus:border-[#1E6FD9] rounded-btn outline-none transition-colors"
          />
          <Search className="absolute left-3 w-4 h-4 text-[#6A7A96]" />
        </div>

        {/* Filters */}
        <div className="w-full md:w-auto flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-[#6A7A96] text-[10px] uppercase">SEVERITY:</span>
            <div className="flex bg-slate-950 rounded border border-border-color p-0.5">
              {(['ALL', 'HIGH', 'WATCH'] as const).map(sev => (
                <button
                  key={sev}
                  onClick={() => setSelectedSeverity(sev)}
                  className={`px-2.5 py-1 text-[9px] font-bold rounded transition-colors cursor-pointer ${
                    selectedSeverity === sev 
                      ? 'bg-[#1E6FD9] text-white' 
                      : 'text-[#A8B4CC] hover:text-white'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#6A7A96] text-[10px] uppercase">INVESTIGATION:</span>
            <div className="flex bg-slate-950 rounded border border-border-color p-0.5">
              {(['ALL', 'PENDING', 'REVIEWED', 'ESCALATED'] as const).map(stat => (
                <button
                  key={stat}
                  onClick={() => setSelectedStatus(stat)}
                  className={`px-2 py-1 text-[9px] font-bold rounded transition-colors cursor-pointer ${
                    selectedStatus === stat 
                      ? 'bg-[#1E6FD9] text-white' 
                      : 'text-[#A8B4CC] hover:text-white'
                  }`}
                >
                  {stat}
                </button>
              ))}
            </div>
          </div>
        </div>

      </div>

      {/* Main Split Grid layout */}
      <div className="flex-1 w-full grid grid-cols-1 lg:grid-cols-12 gap-5 overflow-hidden">
        
        {/* Left Side: Filtered incident listings list (5 cols on lg) */}
        <div className="lg:col-span-5 h-full overflow-y-auto pr-1.5 custom-scrollbar flex flex-col gap-2.5">
          {filteredAlerts.map(alert => {
            const isHigh = alert.severity === 'HIGH';
            const isWatch = alert.severity === 'WATCH';
            const isSelected = selectedAlertId === alert.id;

            return (
              <div
                key={alert.id}
                onClick={() => setSelectedAlertId(alert.id)}
                className={`p-4 bg-slate-950/45 border transition-all duration-300 rounded-card cursor-pointer flex flex-col gap-2 ${
                  isSelected 
                    ? 'border-[#1E6FD9] bg-[#1E6FD9]/5 shadow-glow-blue' 
                    : 'border-border-color hover:border-slate-700/60'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold text-white font-mono">{alert.firNumber}</span>
                    <span className="text-[8.5px] font-mono text-[#6A7A96] uppercase mt-0.5">{alert.station}</span>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[8px] font-bold font-mono ${
                    isHigh ? 'bg-[#C94A2A]/10 text-[#C94A2A] border border-[#C94A2A]/20' : 'bg-[#D4820A]/10 text-[#D4820A] border border-[#D4820A]/20'
                  }`}>
                    {alert.anomalyScore}%
                  </span>
                </div>
                <p className="text-[10px] text-[#A8B4CC] leading-relaxed line-clamp-2">{alert.offenceDetails}</p>
                
                <div className="flex justify-between items-center mt-1 border-t border-slate-900/60 pt-2 text-[8px] font-mono">
                  <span className={alert.status === 'PENDING' ? 'text-red-400' : alert.status === 'REVIEWED' ? 'text-[#0E9E78]' : 'text-purple-400'}>
                    STATUS: {alert.status}
                  </span>
                  <span className="text-[#6A7A96]">
                    {new Date(alert.timestamp).toLocaleDateString()} IST
                  </span>
                </div>
              </div>
            );
          })}

          {filteredAlerts.length === 0 && (
            <div className="p-8 text-center text-xs font-mono text-[#6A7A96] uppercase border border-dashed border-slate-800/40 rounded-card">
              No matching anomalies found
            </div>
          )}
        </div>

        {/* Right Side: High-fidelity details card workbench (7 cols on lg) */}
        <div className="lg:col-span-7 h-full bg-secondary-bg/25 border border-border-color rounded-card overflow-hidden">
          {activeAlert ? (
            <div className="h-full p-6 flex flex-col justify-between overflow-y-auto select-none">
              
              {/* Card Meta details */}
              <div className="space-y-4">
                <div className="flex justify-between items-start border-b border-white/5 pb-3">
                  <div>
                    <span className="px-2 py-0.5 bg-[#1E6FD9]/15 border border-[#1E6FD9]/30 text-[#1E6FD9] rounded text-[8.5px] font-mono font-bold tracking-wider uppercase">
                      CRIMINAL INCIDENT DETECTED
                    </span>
                    <h3 className="text-sm font-mono font-extrabold text-white mt-1.5">{activeAlert.firNumber}</h3>
                  </div>
                  
                  {/* Status Tag */}
                  <div className={`px-3 py-1 font-mono text-[9px] font-bold rounded uppercase ${
                    activeAlert.status === 'PENDING' ? 'bg-[#C94A2A]/10 border border-[#C94A2A]/30 text-[#C94A2A]' : 
                    activeAlert.status === 'REVIEWED' ? 'bg-[#0E9E78]/10 border border-[#0E9E78]/30 text-[#0E9E78]' :
                    'bg-[#6C43CC]/10 border border-[#6C43CC]/30 text-[#6C43CC]'
                  }`}>
                    {activeAlert.status}
                  </div>
                </div>

                {/* Geography details */}
                <div className="grid grid-cols-2 gap-3 text-[10px] font-mono">
                  <div className="p-2 border border-slate-900 bg-slate-950/20 rounded">
                    <span className="text-[#6A7A96] block uppercase text-[8px]">TOWN DISTRICT</span>
                    <span className="text-white font-bold mt-0.5 flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-[#1e6fd9]" />
                      {activeAlert.district}
                    </span>
                  </div>
                  <div className="p-2 border border-slate-900 bg-slate-950/20 rounded">
                    <span className="text-[#6A7A96] block uppercase text-[8px]">POLICE BEAT TARGET</span>
                    <span className="text-white font-bold mt-0.5 truncate">{activeAlert.station}</span>
                  </div>
                </div>

                {/* Core description text box */}
                <div>
                  <span className="text-[8.5px] font-bold text-slate-500 uppercase tracking-widest block mb-1">
                    Offence description
                  </span>
                  <p className="text-[11px] text-[#A8B4CC] leading-relaxed bg-[#0b1425] p-3 rounded border border-slate-900">
                    {activeAlert.offenceDetails}
                  </p>
                </div>

                {/* Scoring factors checklist */}
                <div>
                  <span className="text-[8.5px] font-bold text-slate-500 uppercase tracking-widest block mb-2.5">
                    AI Feature Explanations
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-[9.5px] font-mono">
                    {Object.entries(activeAlert.featureBreakdown).map(([feat, score]) => (
                      <div key={feat} className="p-2 bg-slate-950/30 border border-slate-900/60 rounded flex justify-between items-center">
                        <span className="text-[#A8B4CC] truncate max-w-[120px]">{feat}</span>
                        <span className="text-red-400 font-bold font-mono">{score}% weight</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Case files assignments details */}
                {activeAlert.assignedOfficer && (
                  <div className="p-2.5 bg-[#0E9E78]/5 border border-[#0E9E78]/20 text-[10px] font-mono text-[#0E9E78] rounded flex justify-between">
                    <span>POLICE OFFICER ASSIGNED:</span>
                    <span className="font-bold uppercase tracking-wider">{activeAlert.assignedOfficer}</span>
                  </div>
                )}

              </div>

              {/* ACTION BUTTON WORKBENCH */}
              <div className="pt-5 border-t border-white/5 flex gap-3 text-[9.5px] font-mono uppercase">
                {activeAlert.status === 'PENDING' && (
                  <button
                    onClick={() => reviewAlert(activeAlert.id, user?.name || 'Inspector System')}
                    className="flex-1 py-2.5 bg-[#0E9E78] hover:bg-[#0E9E78]/80 text-white rounded-btn tracking-wider font-semibold cursor-pointer text-center select-none flex items-center justify-center gap-1.5"
                  >
                    <CheckCircle className="w-3.5 h-3.5" />
                    Mark Under Investigation
                  </button>
                )}
                {activeAlert.status !== 'ESCALATED' && (
                  <button
                    onClick={() => escalateAlert(activeAlert.id, user?.name || 'Inspector System')}
                    className="py-2.5 px-4 bg-[#C94A2A] hover:bg-[#C94A2A]/80 text-white rounded-btn tracking-wider font-semibold cursor-pointer text-center select-none flex items-center justify-center gap-1.5"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Escalate to SP
                  </button>
                )}
              </div>

            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-6 text-center text-xs font-mono text-[#6A7A96] uppercase border border-dashed border-slate-800/40 rounded-card select-none">
              <HardDrive className="w-8 h-8 text-slate-800 mb-2" />
              <span>Select case from feed to check and review anomalies logs</span>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
export default Anomalies;


