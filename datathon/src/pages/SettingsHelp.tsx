import React, { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { Settings, Info, Search, Phone, Save, LifeBuoy } from 'lucide-react';

interface IPCSect {
  section: string;
  offence: string;
  classification: string;
  maxPenalty: string;
}

const IPC_DATABASE: IPCSect[] = [
  { section: '302', offence: 'Murder / Homicide offences', classification: 'Cognizable & Non-Bailable', maxPenalty: 'Death Penalty or Life Imprisonment' },
  { section: '379', offence: 'Theft / Robbery (Property seizures)', classification: 'Cognizable & Non-Bailable', maxPenalty: 'Imprisonment up to 3 years' },
  { section: '420', offence: 'Cheating / Cyber Fraud & Ledger spoofing', classification: 'Cognizable & Bailable', maxPenalty: 'Imprisonment up to 7 years' },
  { section: '363', offence: 'Kidnapping & Abduction protocols', classification: 'Cognizable & Non-Bailable', maxPenalty: 'Imprisonment up to 7 years' },
  { section: '506', offence: 'Criminal Intimidation / Threats', classification: 'Non-Cognizable & Bailable', maxPenalty: 'Imprisonment up to 2 years' }
];

export const SettingsHelp: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog, clearLogs } = useAuditStore();

  // Settings State variables
  const [sessionTimeout, setSessionTimeout] = useState('30m');
  const [mapPulseSpeed, setMapPulseSpeed] = useState('medium');
  const [realtimeAuditLogs, setRealtimeAuditLogs] = useState(true);

  // Help search states
  const [ipcSearch, setIpcSearch] = useState('');
  const [settingsSaved, setSettingsSaved] = useState(false);

  const matchedIPC = IPC_DATABASE.find(item => item.section === ipcSearch.trim()) || null;

  const handleSaveSettings = () => {
    const badgeId = user?.badgeId || 'SCRB-7740';
    const officerName = user?.name || 'Inspector System';

    // Log setting adjustment to audit store
    addLog(
      officerName,
      badgeId,
      'AUTH',
      `Configured Settings: SessionTimeout=${sessionTimeout}, MapPulse=${mapPulseSpeed}`
    );

    setSettingsSaved(true);
    setTimeout(() => setSettingsSaved(false), 2000);
  };

  const handleClearLogs = () => {
    const confirm = window.confirm("Are you sure you want to purge local audit log traces? This action is irreversible.");
    if (confirm) {
      clearLogs();
      const badgeId = user?.badgeId || 'SCRB-7740';
      const officerName = user?.name || 'Inspector System';
      addLog(officerName, badgeId, 'AUTH', 'Purged cryptographic session audits traces');
    }
  };

  return (
    <div className="h-[84vh] flex flex-col gap-5 p-1 md:p-3 select-none bg-[var(--bg-primary)] font-mono">
      
      {/* Title Header */}
      <div className="flex justify-between items-center border-b border-[var(--border-muted)] pb-4">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <Settings className="w-5 h-5 text-[#0E9E78] animate-spin-slow" />
            System Settings & Operator Help
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            CALIBRATE SECURITY PERIPHERALS — IPC LEGISLATIVE LOOKUPS & HOTLINE COMMUNICATIONS
          </p>
        </div>
      </div>

      {/* Combined Left-Right Grid panels */}
      <div className="flex-grow w-full grid grid-cols-1 lg:grid-cols-12 gap-5 overflow-hidden text-xs">
        
        {/* LEFT COLUMN: System configuration settings (6 cols) */}
        <div className="lg:col-span-6 bg-[var(--bg-tertiary)]/25 border border-border-color p-5 rounded-xl flex flex-col justify-between overflow-y-auto custom-scrollbar">
          
          <div className="space-y-5">
            <div className="flex items-center gap-2 border-b border-[var(--border-muted)] pb-2 text-[var(--text-primary)] font-bold uppercase tracking-wider text-[10px]">
              <Settings className="w-4 h-4 text-[#0E9E78]" />
              <span>Operational Tuning</span>
            </div>

            {/* Session Timeout dropdown selector */}
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Operator Session Timeout</span>
              <select
                value={sessionTimeout}
                onChange={(e) => setSessionTimeout(e.target.value)}
                className="bg-[var(--bg-tertiary)] border border-border-color text-[var(--text-primary)] rounded px-2 py-1 outline-none focus:border-emerald-500 text-[10px]"
              >
                <option value="5m">5 Minutes</option>
                <option value="15m">15 Minutes</option>
                <option value="30m">30 Minutes</option>
                <option value="1h">1 Hour</option>
                <option value="never">Infinite (Override lock)</option>
              </select>
            </div>

            {/* Map pulse frequency */}
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Map Radar Pulse Speed</span>
              <select
                value={mapPulseSpeed}
                onChange={(e) => setMapPulseSpeed(e.target.value)}
                className="bg-[var(--bg-tertiary)] border border-border-color text-[var(--text-primary)] rounded px-2 py-1 outline-none focus:border-emerald-500 text-[10px]"
              >
                <option value="slow">Slow (Low energy)</option>
                <option value="medium">Medium (Standard)</option>
                <option value="fast">Fast (Real-time tracking)</option>
              </select>
            </div>

            {/* Checkbox triggers */}
            <div className="flex items-start gap-2.5">
              <input
                type="checkbox"
                id="realtimeAudit"
                checked={realtimeAuditLogs}
                onChange={(e) => setRealtimeAuditLogs(e.target.checked)}
                className="mt-0.5 accent-emerald-500"
              />
              <label htmlFor="realtimeAudit" className="text-[var(--text-secondary)] cursor-pointer">
                <span className="block text-[var(--text-primary)] font-semibold">Enable Realtime Audit Streams</span>
                <span className="text-[8.5px] text-[var(--text-muted)] block">Writes page telemetry navigations directly into the ledger window.</span>
              </label>
            </div>

            {/* Audit log clearer */}
            <div className="pt-4 border-t border-[var(--border-muted)] flex items-center justify-between">
              <span className="text-[var(--text-muted)] uppercase text-[9px] font-bold">Audit Traces Database</span>
              <button
                onClick={handleClearLogs}
                className="px-3 py-1 bg-red-950/20 hover:bg-red-950/40 border border-red-900/30 text-red-400 font-bold rounded uppercase text-[8.5px] cursor-pointer"
              >
                Clear Audit Trail Logs
              </button>
            </div>

          </div>

          {/* Action button */}
          <div className="pt-5 border-t border-[var(--border-muted)] mt-5">
            <button
              onClick={handleSaveSettings}
              className="w-full py-2 bg-[#0E9E78] hover:bg-[#0E9E78]/80 text-[var(--text-primary)] font-bold uppercase rounded-btn text-[10px] tracking-wider flex items-center justify-center gap-1.5 cursor-pointer transition-colors"
            >
              {settingsSaved ? (
                <>
                  <CheckCircleIcon />
                  <span>Config Saved to Station</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Configuration</span>
                </>
              )}
            </button>
          </div>

        </div>

        {/* RIGHT COLUMN: Operator Help, IPC Search & Hotline directory (6 cols) */}
        <div className="lg:col-span-6 bg-[var(--bg-tertiary)]/25 border border-border-color p-5 rounded-xl flex flex-col justify-between overflow-y-auto custom-scrollbar">
          
          <div className="space-y-5">
            <div className="flex items-center gap-2 border-b border-[var(--border-muted)] pb-2 text-[var(--text-primary)] font-bold uppercase tracking-wider text-[10px]">
              <LifeBuoy className="w-4 h-4 text-[#1E6FD9]" />
              <span>Operator Helpdesk & References</span>
            </div>

            {/* IPC Search Look-up Panel */}
            <div className="p-3 bg-[var(--bg-secondary)]/60 rounded border border-[var(--border-primary)] space-y-3">
              <span className="text-[var(--text-primary)] font-bold uppercase tracking-wider text-[9px] block">
                Legislative IPC Code Look-Up
              </span>
              <div className="flex gap-2">
                <div className="flex-1 relative flex items-center text-xs">
                  <input
                    type="text"
                    maxLength={3}
                    placeholder="Enter section code (e.g., 379, 420, 302)..."
                    value={ipcSearch}
                    onChange={(e) => setIpcSearch(e.target.value)}
                    className="w-full pl-8 pr-3 py-1 bg-[var(--bg-secondary)] border border-[var(--border-primary)] text-[var(--text-primary)] outline-none rounded focus:border-[#1E6FD9] text-[10px]"
                  />
                  <Search className="absolute left-2.5 w-3.5 h-3.5 text-[var(--text-muted)]" />
                </div>
              </div>

              {/* Render Search Results details */}
              {matchedIPC ? (
                <div className="p-2.5 bg-emerald-950/10 border border-emerald-900/30 rounded text-[9.5px] leading-relaxed text-[var(--text-secondary)] animate-[fadeIn_0.3s_ease-out]">
                  <div className="flex justify-between font-bold text-[var(--text-primary)] uppercase text-[8px] mb-1">
                    <span>IPC SECTION {matchedIPC.section}</span>
                    <span className="text-emerald-400">{matchedIPC.classification}</span>
                  </div>
                  <p className="font-semibold text-[var(--text-primary)] uppercase tracking-wide text-[10px]">{matchedIPC.offence}</p>
                  <p className="text-[8.5px] text-[var(--text-muted)] mt-1 uppercase">MAX PENALTY: <span className="text-[var(--text-primary)] font-bold">{matchedIPC.maxPenalty}</span></p>
                </div>
              ) : ipcSearch.trim() ? (
                <div className="p-2 text-[9px] text-red-400 font-semibold uppercase">No section mathcing code "{ipcSearch}" found in IPC reference database.</div>
              ) : (
                <div className="p-2 text-[9px] text-[var(--text-muted)] uppercase">Type in an IPC section number to verify crime classifications instantly.</div>
              )}
            </div>

            {/* Direct hotline contacts */}
            <div className="space-y-2">
              <span className="text-[var(--text-primary)] font-bold uppercase tracking-wider text-[9px] block">
                Direct Communications Hotlines
              </span>
              
              <div className="space-y-1.5 text-[9.5px]">
                <div className="p-2.5 bg-[var(--bg-secondary)]/30 border border-[var(--border-primary)]/60 rounded flex items-center justify-between">
                  <span className="text-[var(--text-secondary)]">SCRB Command Central Desk</span>
                  <a href="tel:+918022942111" className="text-[#1E6FD9] hover:underline font-bold flex items-center gap-1">
                    <Phone className="w-3 h-3" />
                    +91 80 2294 2111
                  </a>
                </div>

                <div className="p-2.5 bg-[var(--bg-secondary)]/30 border border-[var(--border-primary)]/60 rounded flex items-center justify-between">
                  <span className="text-[var(--text-secondary)]">Cyber Crime HQ (Bengaluru)</span>
                  <a href="tel:+918022943355" className="text-[#1E6FD9] hover:underline font-bold flex items-center gap-1">
                    <Phone className="w-3 h-3" />
                    +91 80 2294 3355
                  </a>
                </div>

                <div className="p-2.5 bg-[var(--bg-secondary)]/30 border border-[var(--border-primary)]/60 rounded flex items-center justify-between">
                  <span className="text-[var(--text-secondary)]">Emergency Response Support System</span>
                  <a href="tel:112" className="text-red-400 hover:underline font-bold flex items-center gap-1">
                    <Phone className="w-3 h-3" />
                    112 (Radio Dispatch)
                  </a>
                </div>
              </div>
            </div>

          </div>

          {/* Quick FAQ info block */}
          <div className="p-3 bg-[var(--bg-tertiary)]/50 border border-[#1e6fd9]/15 rounded text-[8.5px] leading-relaxed text-[var(--text-muted)] flex items-start gap-2 mt-4 select-none">
            <Info className="w-4 h-4 text-[#1E6FD9] shrink-0 mt-0.5" />
            <div>
              <span className="text-[var(--text-primary)] font-bold uppercase block text-[7.5px] mb-0.5">Operator Advisory</span>
              Shift handovers require clearing the active audit terminal window or generating a general dashboard telemetry dossier backup file before logout.
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};

const CheckCircleIcon = () => (
  <svg className="w-3.5 h-3.5 text-[var(--text-primary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export default SettingsHelp;
