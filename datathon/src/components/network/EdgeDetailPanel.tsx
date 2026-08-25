import React from 'react';
import type { GraphLink, GraphNode } from './CriminalGraph3D';
import { 
  GitCommit, 
  ShieldCheck, 
  AlertTriangle, 
  FileText, 
  X, 
  Database, 
  CheckCircle2, 
  HelpCircle,
  Clock,
  Layers
} from 'lucide-react';

interface EdgeDetailPanelProps {
  link: GraphLink | null;
  nodes?: GraphNode[];
  onClose: () => void;
}

export const EdgeDetailPanel: React.FC<EdgeDetailPanelProps> = ({ link, nodes = [], onClose }) => {
  if (!link) return null;

  const sourceNode = nodes.find((n) => n.id === (typeof link.source === 'object' ? (link.source as any).id : link.source));
  const targetNode = nodes.find((n) => n.id === (typeof link.target === 'object' ? (link.target as any).id : link.target));

  const sourceName = sourceNode?.name || (typeof link.source === 'object' ? (link.source as any).name : link.source);
  const targetName = targetNode?.name || (typeof link.target === 'object' ? (link.target as any).name : link.target);

  const provenance = link.provenance || 'DIRECT_DATABASE';
  const verificationStatus = link.verification_status || 'VERIFIED';
  const relationshipType = link.relationship_type || 'OTHER';
  const confidence = link.confidence !== undefined && link.confidence !== null ? Math.round(link.confidence * 100) : null;
  const confidenceLevel = link.confidence_level || 'HIGH';
  const isDemo = link.is_demo_derived || provenance === 'DEMO_SEED' || provenance === 'MIXED';

  const isVerified = verificationStatus === 'VERIFIED';
  const isPotential = verificationStatus === 'POTENTIAL';

  return (
    <div className="h-full bg-secondary-bg border-l border-border-color p-5 flex flex-col justify-between select-none overflow-y-auto custom-scrollbar">
      {/* DRAWER HEADER */}
      <div>
        <div className="flex justify-between items-start pb-4 border-b border-border-color mb-4">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
              isVerified 
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' 
                : isPotential
                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                : 'bg-purple-500/10 text-purple-400 border border-purple-500/30'
            }`}>
              <GitCommit className="w-5 h-5" />
            </div>

            <div>
              <h4 className="text-xs font-mono font-bold text-[var(--text-primary)] uppercase max-w-[170px] truncate">
                {link.relationship}
              </h4>
              <span className="text-[8.5px] font-mono text-[var(--text-muted)] uppercase tracking-wider block mt-0.5">
                Type: {relationshipType}
              </span>
              {isDemo && (
                <span
                  title="This link involves bundled demo/seed data, not live operational intelligence."
                  className="mt-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[var(--accent-purple)]/10 border border-[var(--accent-purple)]/30 text-[var(--accent-purple)] text-[8px] font-mono uppercase tracking-widest"
                >
                  <Database className="w-2.5 h-2.5" />
                  Demo Derived
                </span>
              )}
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1 hover:bg-[var(--accent-blue)]/15 rounded text-[var(--text-secondary)] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* PRIMARY BODY */}
        <div className="flex flex-col gap-4 font-mono text-xs">
          
          {/* Connected Entities Banner */}
          <div className="p-3 rounded-card bg-[var(--bg-tertiary)] border border-[var(--border-muted)] flex flex-col gap-2">
            <span className="text-[8px] uppercase tracking-widest text-[var(--text-muted)]">
              Connected Graph Entities
            </span>
            <div className="flex items-center justify-between text-[11px] font-semibold text-[var(--text-primary)]">
              <span className="truncate max-w-[100px]" title={sourceName}>{sourceName}</span>
              <span className="text-[var(--accent-blue)]">↔</span>
              <span className="truncate max-w-[100px]" title={targetName}>{targetName}</span>
            </div>
          </div>

          {/* Provenance & Verification Badges */}
          <div className="grid grid-cols-2 gap-2">
            <div className="p-2.5 rounded-card bg-[var(--bg-tertiary)] border border-[var(--border-muted)]">
              <span className="text-[7.5px] uppercase tracking-widest text-[var(--text-muted)] block mb-1">
                Data Provenance
              </span>
              <span className={`text-[9.5px] font-bold uppercase tracking-wider flex items-center gap-1 ${
                provenance === 'DIRECT_DATABASE' ? 'text-emerald-400' :
                provenance === 'ANALYTICAL_INFERENCE' ? 'text-amber-400' :
                provenance === 'DEMO_SEED' ? 'text-purple-400' :
                provenance === 'MIXED' ? 'text-purple-300' : 'text-slate-400'
              }`}>
                {provenance === 'DIRECT_DATABASE' && <CheckCircle2 className="w-3 h-3" />}
                {provenance === 'ANALYTICAL_INFERENCE' && <Layers className="w-3 h-3" />}
                {provenance === 'DEMO_SEED' && <Database className="w-3 h-3" />}
                {provenance === 'MIXED' && <Database className="w-3 h-3" />}
                {provenance.replace('_', ' ')}
              </span>
            </div>

            <div className="p-2.5 rounded-card bg-[var(--bg-tertiary)] border border-[var(--border-muted)]">
              <span className="text-[7.5px] uppercase tracking-widest text-[var(--text-muted)] block mb-1">
                Verification Status
              </span>
              <span className={`text-[9.5px] font-bold uppercase tracking-wider flex items-center gap-1 ${
                isVerified ? 'text-emerald-400' :
                isPotential ? 'text-amber-400' :
                'text-purple-400'
              }`}>
                {isVerified ? <ShieldCheck className="w-3 h-3" /> : <HelpCircle className="w-3 h-3" />}
                {verificationStatus}
              </span>
            </div>
          </div>

          {/* Calculated Confidence Score */}
          {confidence !== null && (
            <div className="p-3 rounded-card bg-[var(--bg-tertiary)] border border-[var(--border-muted)] flex items-center justify-between">
              <div>
                <span className="text-[8px] uppercase tracking-widest text-[var(--text-muted)] block">
                  Grounding Confidence ({confidenceLevel})
                </span>
                <span className="text-base font-bold text-[var(--text-primary)] mt-0.5 block">
                  {confidence}%
                </span>
              </div>
              <div className="w-20 bg-[var(--bg-primary)] h-2 rounded-full overflow-hidden border border-[var(--border-muted)]">
                <div 
                  className={`h-full ${
                    confidence >= 80 ? 'bg-emerald-500' : confidence >= 60 ? 'bg-amber-500' : 'bg-slate-500'
                  }`}
                  style={{ width: `${confidence}%` }}
                />
              </div>
            </div>
          )}

          {/* Operational Evidence Disclaimer Warning */}
          {link.operational_warning && (
            <div className="p-3 rounded-card bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
              <div className="text-[8.5px] leading-relaxed">
                <strong className="block font-bold text-amber-400 uppercase tracking-wider mb-0.5">
                  Analytical Lead Advisory
                </strong>
                {link.operational_warning}
              </div>
            </div>
          )}

          {/* Supporting Evidence Records */}
          <div className="space-y-2">
            <span className="text-[8.5px] uppercase tracking-widest text-[var(--text-muted)] flex items-center gap-1 font-bold">
              <FileText className="w-3 h-3 text-[var(--accent-blue)]" />
              Supporting Database Evidence ({link.evidence?.length || 0})
            </span>

            {link.evidence && link.evidence.length > 0 ? (
              <div className="space-y-2">
                {link.evidence.map((ev, idx) => (
                  <div 
                    key={idx} 
                    className="p-2.5 rounded bg-[var(--bg-primary)] border border-[var(--border-muted)] text-[9px] space-y-1"
                  >
                    <div className="flex justify-between items-center text-[var(--accent-blue)] font-bold">
                      <span>{ev.record_number ? `Record: ${ev.record_number}` : ev.record_type?.toUpperCase()}</span>
                      {ev.timestamp && (
                        <span className="text-[7.5px] font-normal text-[var(--text-muted)] flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" />
                          {new Date(ev.timestamp).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    {ev.details && <p className="text-[var(--text-secondary)]">{ev.details}</p>}
                    {ev.factors && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {ev.factors.map((factor, fIdx) => (
                          <span 
                            key={fIdx} 
                            className="px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-primary)] text-[7.5px]"
                          >
                            • {factor}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[8.5px] text-[var(--text-muted)] italic">
                Direct relationship grounded in primary database schema linkage.
              </p>
            )}
          </div>

        </div>
      </div>

      {/* FOOTER ACTIONS */}
      <div className="pt-4 border-t border-border-color mt-4">
        <button
          onClick={onClose}
          className="w-full py-2 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/15 border border-[var(--border-secondary)] hover:border-[var(--accent-blue)]/50 text-[var(--text-primary)] text-[9.5px] font-mono uppercase tracking-wider rounded-btn transition-colors cursor-pointer"
        >
          Dismiss Inspector
        </button>
      </div>
    </div>
  );
};

export default EdgeDetailPanel;
