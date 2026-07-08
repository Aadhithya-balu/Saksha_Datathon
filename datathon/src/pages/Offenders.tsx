import React, { useState } from 'react';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { ShieldAlert, Download, Terminal, Search, UserCheck, ShieldCheck, UserMinus, Plus } from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';

interface OffenderDossier {
  id: string;
  name: string;
  alias: string;
  age: number;
  gender: string;
  classification: 'A-CATEGORY' | 'B-CATEGORY' | 'WATCHLIST';
  activeDistricts: string[];
  status: 'ACTIVE' | 'INCARCERATED' | 'UNDER_SURVEILLANCE';
  riskScore: number;
  gangAffiliation: string;
  mugshotDesc: string; // text outline to draft D3 image
}

const OFFENDERS_DECK: OffenderDossier[] = [
  {
    id: 'off-501',
    name: 'Ramu Swamy',
    alias: 'Kodaikanal Ramu',
    age: 44,
    gender: 'Male',
    classification: 'A-CATEGORY',
    activeDistricts: ['Mysuru', 'Bengaluru Urban', 'Hassan'],
    status: 'ACTIVE',
    riskScore: 92,
    gangAffiliation: 'Interstate Decoit Gang B',
    mugshotDesc: 'Dark complexion, scar near left eyebrow, stubble beard.'
  },
  {
    id: 'off-502',
    name: 'Vikram Yadav',
    alias: 'Vicky',
    age: 36,
    gender: 'Male',
    classification: 'A-CATEGORY',
    activeDistricts: ['Bengaluru Urban', 'Tumkuru'],
    status: 'UNDER_SURVEILLANCE',
    riskScore: 88,
    gangAffiliation: 'Virtual Ledger Syndicate',
    mugshotDesc: 'Clean shaven, gold ring, spectacles.'
  },
  {
    id: 'off-503',
    name: 'Sayed Ibrahim',
    alias: 'Sayed',
    age: 41,
    gender: 'Male',
    classification: 'B-CATEGORY',
    activeDistricts: ['Mangaluru', 'Dharwad'],
    status: 'ACTIVE',
    riskScore: 84,
    gangAffiliation: 'Port Corridor Drug Ring',
    mugshotDesc: 'Tall, curly hair, tattoo on right wrist.'
  },
  {
    id: 'off-504',
    name: 'Karthik Gowda',
    alias: 'Gowda',
    age: 38,
    gender: 'Male',
    classification: 'WATCHLIST',
    activeDistricts: ['Mysuru', 'Tumkuru'],
    status: 'INCARCERATED',
    riskScore: 71,
    gangAffiliation: 'Independent Property Frauds',
    mugshotDesc: 'Short, thick moustache, tribal tattoo left arm.'
  }
];

export const Offenders: React.FC = () => {
  const { logs, addLog, clearLogs } = useAuditStore();
  const { user } = useAuthStore();

  const [selectedOffenderId, setSelectedOffenderId] = useState<string>(OFFENDERS_DECK[0]?.id || '');
  const [selectedWatermark, setSelectedWatermark] = useState<string>('CONFIDENTIAL - SCRB BEATS');
  const [searchQuery, setSearchQuery] = useState('');

  const activeOffender = OFFENDERS_DECK.find(o => o.id === selectedOffenderId) || OFFENDERS_DECK[0] || null;

  // Filter list
  const filteredOffenders = OFFENDERS_DECK.filter(o => 
    o.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    o.alias.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleExportPDF = () => {
    if (!activeOffender || !user) return;
    
    // Log the event in the audit store
    addLog(
      user.name,
      user.badgeId,
      'EXPORT',
      `Exported dossier for ${activeOffender.name} watermarked: [${selectedWatermark}]`
    );

    downloadSecureDossier(
      `Offender Dossier - ${activeOffender.name}`, 
      activeOffender, 
      selectedWatermark
    );
  };

  return (
    <div className="h-[84vh] flex flex-col gap-5 p-1 md:p-3 select-none">
      
      {/* Platform Title */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-white/5 pb-3">
        <div>
          <h2 className="text-md font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#C94A2A] animate-pulse" />
            Registry & System Security Logs
          </h2>
          <p className="text-[9.5px] font-mono text-[#6A7A96] mt-0.5">
            LAW ENFORCEMENT BIO-REGISTRY — CRYPTOGRAPHIC TERMINAL AUDITS & CLASSIFIED WATERMARK EXPORTS
          </p>
        </div>
      </div>

      {/* Main Double Grid layout splitting dossiers and audits */}
      <div className="flex-grow w-full grid grid-cols-1 lg:grid-cols-12 gap-5 overflow-hidden">
        
        {/* LEFT COLUMN: Dossier workbench selector (7 cols on lg) */}
        <div className="lg:col-span-7 bg-[#111D35]/30 border border-border-color p-5 rounded-card flex flex-col justify-between overflow-hidden">
          
          <div className="flex flex-col gap-4 overflow-hidden flex-1">
            <div className="flex justify-between items-center select-none border-b border-slate-900 pb-2">
              <span className="text-[10px] font-mono font-bold text-[#E8EDF5] uppercase tracking-wider">
                Offender Dossier Database
              </span>
              <div className="w-48 flex items-center relative text-xs">
                <input
                  type="text"
                  placeholder="Search alias..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-7 pr-3 py-1 bg-slate-950/70 border border-border-color rounded text-white outline-none focus:border-[#C94A2A]"
                />
                <Search className="absolute left-2 w-3.5 h-3.5 text-[#6A7A96]" />
              </div>
            </div>

            {/* Selector Grid listing */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4 flex-grow overflow-hidden">
              
              {/* Left names list (4 cols) */}
              <div className="md:col-span-4 overflow-y-auto pr-1 flex flex-col gap-2 custom-scrollbar max-h-[300px]">
                {filteredOffenders.map(o => (
                  <button
                    key={o.id}
                    onClick={() => setSelectedOffenderId(o.id)}
                    className={`p-2.5 rounded text-left font-mono text-[10.5px] transition-colors border cursor-pointer ${
                      selectedOffenderId === o.id
                        ? 'bg-[#C94A2A]/10 border-[#C94A2A]/40 text-[#C94A2A] font-bold'
                        : 'bg-[#111D35]/50 border-slate-800 text-[#A8B4CC] hover:bg-slate-800/30'
                    }`}
                  >
                    <span className="block truncate">{o.alias}</span>
                    <span className="text-[8px] text-[#6A7A96] block mt-0.5">{o.name}</span>
                  </button>
                ))}
              </div>

              {/* Right profile info (8 cols) */}
              <div className="md:col-span-8 overflow-y-auto pr-1 flex flex-col gap-3 custom-scrollbar text-xs font-mono max-h-[300px]">
                {activeOffender ? (
                  <div className="space-y-4">
                    {/* Identification Banner block */}
                    <div className="p-3 bg-slate-950/50 border border-slate-950 rounded flex gap-4">
                      {/* Biometric portrait mock image representation */}
                      <div className="w-16 h-20 bg-slate-900 border border-[#C94A2A]/30 rounded flex items-center justify-center text-[#C94A2A] relative shrink-0 overflow-hidden select-none">
                        <UserMinus className="w-8 h-8" />
                        <div className="absolute inset-0 border border-dashed border-[#C94A2A]/30 animate-pulse pointer-events-none" />
                        {/* Horizontal scanline overlays inside photo */}
                        <div className="absolute top-1/2 left-0 right-0 h-[0.5px] bg-[#C94A2A]/60 animate-[vscan_2s_infinite]" />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <span className="text-[8.5px] font-bold text-red-500 bg-red-950/20 px-1.5 py-0.5 rounded border border-red-900/30 uppercase">
                          {activeOffender.classification}
                        </span>
                        <h4 className="text-[13px] font-extrabold text-white mt-1.5 truncate">
                          {activeOffender.name}
                        </h4>
                        <span className="text-[9.5px] text-[#A8B4CC] block mt-0.5 uppercase tracking-wide">
                          ALIAS: {activeOffender.alias}
                        </span>
                      </div>
                    </div>

                    {/* Metadata listings */}
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <div className="p-2 border border-slate-900 rounded">
                        <span className="text-slate-500 uppercase text-[8px] block">Threat index</span>
                        <span className="text-white font-bold block mt-0.5">{activeOffender.riskScore}% severity</span>
                      </div>
                      <div className="p-2 border border-slate-900 rounded">
                        <span className="text-slate-500 uppercase text-[8px] block">Operational state</span>
                        <span className="text-emerald-400 font-bold block mt-0.5 uppercase">{activeOffender.status}</span>
                      </div>
                      <div className="p-2 border border-slate-900 rounded">
                        <span className="text-slate-500 uppercase text-[8px] block">Gang Syndicate</span>
                        <span className="text-white font-bold block mt-0.5 truncate">{activeOffender.gangAffiliation}</span>
                      </div>
                      <div className="p-2 border border-slate-900 rounded">
                        <span className="text-slate-500 uppercase text-[8px] block">Key sectors</span>
                        <span className="text-white font-bold block mt-0.5 truncate">{activeOffender.activeDistricts.join(', ')}</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 text-center text-[#6A7A96] uppercase">No Profile Highlighted</div>
                )}
              </div>

            </div>
          </div>

          {/* Secure Export Watermark Block */}
          {activeOffender && (
            <div className="pt-4 border-t border-border-color mt-4 flex flex-col sm:flex-row gap-3 items-end">
              <div className="flex-1 w-full flex flex-col gap-1 text-[10px] font-mono text-left">
                <span className="text-[#6A7A96] uppercase font-bold">Select Security Watermark String</span>
                <select
                  value={selectedWatermark}
                  onChange={(e) => setSelectedWatermark(e.target.value)}
                  className="w-full p-2 bg-slate-950 border border-slate-800 text-white rounded outline-none text-xs focus:border-[#C94A2A]"
                >
                  <option value={`CONFIDENTIAL - BADGE: ${user?.badgeId || 'SYSTEM'}`}>CONFIDENTIAL • Officer Badge ID</option>
                  <option value="STRICT LAW ENFORCEMENT ONLY">RESTRICTED • Law Enforcement Only</option>
                  <option value="CLASSIFIED INTERNAL SCRB INTELLIGENCE">CLASSIFIED • SCRB Internal Intel</option>
                </select>
              </div>

              <button
                onClick={handleExportPDF}
                className="w-full sm:w-auto py-2 px-5 bg-[#C94A2A] hover:bg-[#C94A2A]/85 text-white font-mono text-[10px] uppercase rounded-btn font-semibold tracking-wider flex items-center justify-center gap-1.5 shadow-glow-coral cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                Generate Secure Dossier PDF
              </button>
            </div>
          )}

        </div>

        {/* RIGHT COLUMN: Terminal style active system audit trail (5 cols on lg) */}
        <div className="lg:col-span-5 bg-slate-950 border border-border-color p-4 rounded-card flex flex-col justify-between overflow-hidden">
          
          <div className="flex flex-col gap-3 overflow-hidden flex-1 select-none">
            {/* Terminal Header */}
            <div className="flex justify-between items-center border-b border-slate-900 pb-2">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-[#0E9E78] animate-pulse" />
                <span className="text-[10px] font-mono font-bold text-[#E8EDF5] uppercase tracking-wider">
                  Cryptographic System Audits
                </span>
              </div>
              <button
                onClick={clearLogs}
                className="text-[8px] font-mono bg-slate-900 hover:bg-slate-800 border border-slate-800 px-2 py-0.5 rounded text-amber-500 cursor-pointer"
              >
                Clear Screen
              </button>
            </div>

            {/* Logs scrolling panel */}
            <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-2 custom-scrollbar max-h-[360px]">
              {logs.map((log) => {
                let color = 'text-[#A8B4CC]';
                if (log.actionType === 'EXPORT') color = 'text-red-400';
                else if (log.actionType === 'AUTH') color = 'text-emerald-400';
                else if (log.actionType === 'REVIEW') color = 'text-sky-400';
                else if (log.actionType === 'ESCALATION') color = 'text-purple-400';

                return (
                  <div key={log.id} className="text-[8.5px] font-mono leading-relaxed border-b border-white/5 pb-1 flex flex-col gap-0.5 text-left">
                    <div className="flex justify-between text-slate-500 select-none">
                      <span>{new Date(log.timestamp).toLocaleTimeString()} • IP: {log.ipAddress}</span>
                      <span className="font-bold uppercase tracking-wider">{log.actionType}</span>
                    </div>
                    <div className={`${color}`}>
                      <span className="text-white font-semibold">[{log.badgeId}]</span> {log.details}
                    </div>
                  </div>
                );
              })}

              {logs.length === 0 && (
                <div className="h-full flex items-center justify-center p-6 text-center text-[8.5px] font-mono text-slate-600 uppercase">
                  Audits queue empty - awaiting security triggers
                </div>
              )}
            </div>

          </div>

          <div className="pt-2 text-[8px] font-mono text-slate-600 text-left border-t border-slate-900/60 mt-3 select-none">
            TELEMETRY SECURITY KEY OVERLAY ON EXPORTED PDF DOCUMENT MATCHES LEGAL STAMP COMPLIANCE 2026.
          </div>

        </div>

      </div>

    </div>
  );
};
export default Offenders;
