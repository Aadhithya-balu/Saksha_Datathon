import React from 'react';
import type { GraphNode } from './CriminalGraph3D';
import { User, ShieldAlert, Phone, MapPin, Briefcase, Plus, X, Heart, Link2 } from 'lucide-react';
import { downloadSecureDossier } from '../../utils/downloader';
import { useAuditStore } from '../../store/auditStore';
import { useAuthStore } from '../../store/authStore';

interface NodeDetailPanelProps {
  node: GraphNode | null;
  onClose: () => void;
}

export const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({ node, onClose }) => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  if (!node) return null;

  const isSuspect = node.category === 'suspect';
  const isOffender = node.category === 'offender';
  const isLocation = node.category === 'location';
  const isVictim = node.category === 'victim';

  return (
    <div className="h-full bg-secondary-bg border-l border-border-color p-5 flex flex-col justify-between select-none">
      
      {/* DRAWER HEADER */}
      <div>
        <div className="flex justify-between items-start pb-4 border-b border-border-color mb-4">
          <div className="flex items-center gap-3">
            {/* Color-badge dynamic avatar */}
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
              isSuspect ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 
              isOffender ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20' :
              isLocation ? 'bg-sky-500/10 text-sky-500 border border-sky-500/20' :
              'bg-[var(--bg-tertiary)] text-[var(--text-muted)] border border-[var(--border-secondary)]'
            }`}>
              {isLocation ? <MapPin className="w-5 h-5" /> : <User className="w-5 h-5" />}
            </div>

            <div>
              <h4 className="text-xs font-mono font-bold text-[var(--text-primary)] uppercase max-w-[160px] truncate">
                {node.name}
              </h4>
              <span className="text-[8.5px] font-mono text-[var(--text-muted)] uppercase tracking-wider block mt-0.5">
                Clearance: {node.category}
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 hover:bg-[var(--accent-blue)]/15 rounded text-[var(--text-secondary)] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* PRIMARY DOSSIER BODY */}
        <div className="flex flex-col gap-4 font-mono text-xs">
          
          {/* Active Risk Banner */}
          {!isVictim && !isLocation && (
            <div className={`p-3 rounded-card border flex items-center justify-between ${
              node.riskScore >= 80 
                ? 'bg-[var(--accent-coral)]/5 border-[var(--accent-coral)]/20 text-[var(--accent-coral)]' 
                : 'bg-[var(--accent-amber)]/5 border-[var(--accent-amber)]/20 text-[var(--accent-amber)]'
            }`}>
              <div>
                <span className="text-[8px] uppercase tracking-widest text-[var(--text-muted)] block">
                  Threat Threat Metric
                </span>
                <span className="text-lg font-bold block mt-0.5">{node.riskScore}%</span>
              </div>
              <ShieldAlert className="w-5 h-5 animate-pulse" />
            </div>
          )}

          {/* Location Risk Banner */}
          {isLocation && (
            <div className="p-3 rounded-card bg-[var(--accent-blue)]/5 border border-[var(--accent-blue)]/20 text-[var(--accent-blue)]">
              <span className="text-[8px] uppercase tracking-widest text-[var(--text-muted)] block">
                Regional Grid Density
              </span>
              <span className="text-lg font-bold block mt-0.5">{node.riskScore}% severity</span>
            </div>
          )}

          {/* Details Descriptions */}
          <div className="space-y-4 pt-1">
            <div>
              <span className="text-[8.5px] font-bold text-[var(--text-muted)] uppercase tracking-widest block mb-1">
                Intelligence Description
              </span>
              <p className="text-[10.5px] text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-secondary)] p-3 rounded-btn border border-[var(--border-primary)]">
                {node.details}
              </p>
            </div>

            {/* Suspect context meta details */}
            <div className="space-y-2 border-t border-[var(--border-primary)] pt-3">
              {node.phone && (
                <div className="flex items-center justify-between text-[10px]">
                  <span className="text-[var(--text-muted)] flex items-center gap-1">
                    <Phone className="w-3 h-3 text-[var(--accent-blue)]" /> Core Contact
                  </span>
                  <span className="text-[var(--text-primary)] hover:text-[var(--accent-blue)] cursor-pointer">{node.phone}</span>
                </div>
              )}

              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[var(--text-muted)] flex items-center gap-1">
                  <Briefcase className="w-3 h-3 text-[var(--accent-teal)]" /> Related Case Files
                </span>
                <span className="text-[var(--accent-teal)] font-bold">{node.casesCount} active FIRs</span>
              </div>
            </div>

            {/* Modus Operandi tags */}
            {!isVictim && !isLocation && (
              <div>
                <span className="text-[8.5px] font-bold text-[var(--text-muted)] uppercase tracking-widest block mb-1.5">
                  Modus Operandi Marks
                </span>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {isSuspect && (
                    <>
                      <span className="px-2 py-0.5 bg-red-950/20 text-red-400 rounded text-[9px] border border-red-900/30">Biometric Forgery</span>
                      <span className="px-2 py-0.5 bg-purple-950/20 text-purple-400 rounded text-[9px] border border-purple-900/30">Night Looting</span>
                      <span className="px-2 py-0.5 bg-orange-950/20 text-orange-400 rounded text-[9px] border border-orange-900/30">Goon Coordinator</span>
                    </>
                  )}
                  {isOffender && (
                    <>
                      <span className="px-2 py-0.5 bg-amber-950/20 text-amber-400 rounded text-[9px] border border-amber-900/30">Tax Evasion</span>
                      <span className="px-2 py-0.5 bg-sky-950/20 text-sky-400 rounded text-[9px] border border-sky-900/30">Transit Violations</span>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Location coordinates mock grid */}
            {isLocation && (
              <div>
                <span className="text-[8.5px] font-bold text-[var(--text-muted)] uppercase tracking-widest block mb-1.5">
                  Sub-grid sectors
                </span>
                <div className="flex flex-col gap-1 mt-1 text-[10px] text-[var(--text-secondary)]">
                  <div className="flex justify-between py-1 bg-[var(--bg-secondary)]/30 px-2 rounded">
                    <span>Beat Sector A (High Density)</span>
                    <span className="text-red-400">88% ris</span>
                  </div>
                  <div className="flex justify-between py-1 bg-[var(--bg-secondary)]/30 px-2 rounded">
                    <span>Beat Sector B (Medium Density)</span>
                    <span className="text-amber-400">62% ris</span>
                  </div>
                </div>
              </div>
            )}

          </div>

        </div>
      </div>

      {/* FOOTER ACTIONS */}
      <div className="pt-4 border-t border-border-color flex flex-col gap-2 font-mono">
        <button
          onClick={() => {
            downloadSecureDossier(
              `${node.name} Dossier`, 
              node, 
              user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE'
            );
            if (user) {
              addLog(
                user.name,
                user.badgeId,
                'EXPORT',
                `Exported police dossier dossier for ${node.name}`
              );
            }
          }}
          className="w-full py-2 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/80 text-[var(--text-primary)] text-[10px] uppercase rounded-btn font-semibold cursor-pointer text-center select-none"
        >
          View Full Police Dossier
        </button>
        <button
          onClick={() => {
            downloadSecureDossier(
              `${node.name} Connection Map`, 
              {
                suspectName: node.name,
                category: node.category,
                casesFilings: node.casesCount,
                links: ['Accomplice: Ramu Swamy', 'Funnels through Indo-Sector Checkpoints']
              }, 
              user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE'
            );
            if (user) {
              addLog(
                user.name,
                user.badgeId,
                'EXPORT',
                `Exported suspect association linkage map for ${node.name}`
              );
            }
          }}
          className="w-full py-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] text-[10px] uppercase rounded-btn font-semibold border border-[var(--border-primary)] hover:border-[var(--border-secondary)] cursor-pointer text-center select-none flex items-center justify-center gap-1.5"
        >
          <Link2 className="w-3.5 h-3.5" />
          Export Connection Map
        </button>
      </div>

    </div>
  );
};
export default NodeDetailPanel;
