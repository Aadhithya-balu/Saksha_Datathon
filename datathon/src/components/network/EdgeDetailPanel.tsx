import React from 'react';
import type { GraphLink, GraphNode } from './CriminalGraph3D';
import { GitCommit, ShieldCheck, AlertTriangle, FileText, X, Database, CheckCircle2, HelpCircle, Clock, Layers } from 'lucide-react';

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
  const confidence = link.confidence !== undefined && link.confidence !== null ? Math.round(link.confidence * 100) : null;
  const confidenceLevel = link.confidence_level || 'HIGH';
  const isDemo = link.is_demo_derived || provenance === 'DEMO_SEED' || provenance === 'MIXED';
  const isVerified = verificationStatus === 'VERIFIED';
  const isPotential = verificationStatus === 'POTENTIAL';

  return (
    <div className="h-full bg-secondary-bg border-l border-border-color flex flex-col select-none overflow-hidden">
      
      {/* Header */}
      <div className="p-4 pb-3 border-b border-border-color shrink-0">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`w-10 h-10 shrink-0 rounded-full flex items-center justify-center ${
              isVerified ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 
              isPotential ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
              'bg-purple-500/10 text-purple-400 border border-purple-500/30'
            }`}>
              <GitCommit className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] truncate">{link.relationship}</h3>
              <p className="text-[11px] text-[var(--text-muted)] mt-0.5 capitalize">{verificationStatus.replace(/_/g, ' ').toLowerCase()}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-[var(--bg-tertiary)] rounded text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer shrink-0 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        {isDemo && (
          <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[var(--accent-purple)]/10 border border-[var(--accent-purple)]/20 text-[var(--accent-purple)] text-[10px]">
            <Database className="w-3 h-3" />
            Demo derived
          </div>
        )}
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-5 text-sm">

        {/* Connected entities */}
        <div className="p-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)]">
          <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)] mb-2">Connected Entities</p>
          <div className="flex items-center justify-between text-[13px] font-medium text-[var(--text-primary)]">
            <span className="truncate max-w-[100px]" title={sourceName}>{sourceName}</span>
            <span className="text-[var(--accent-blue)] mx-2">↔</span>
            <span className="truncate max-w-[100px]" title={targetName}>{targetName}</span>
          </div>
        </div>

        {/* Provenance & Status */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)]">
            <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)] mb-1">Provenance</p>
            <p className={`text-[11px] font-semibold uppercase flex items-center gap-1 ${
              provenance === 'DIRECT_DATABASE' ? 'text-emerald-400' :
              provenance === 'ANALYTICAL_INFERENCE' ? 'text-amber-400' :
              'text-purple-400'
            }`}>
              {provenance === 'DIRECT_DATABASE' && <CheckCircle2 className="w-3 h-3" />}
              {provenance === 'ANALYTICAL_INFERENCE' && <Layers className="w-3 h-3" />}
              {(provenance === 'DEMO_SEED' || provenance === 'MIXED') && <Database className="w-3 h-3" />}
              {provenance.replace(/_/g, ' ')}
            </p>
          </div>
          <div className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)]">
            <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)] mb-1">Verification</p>
            <p className={`text-[11px] font-semibold uppercase flex items-center gap-1 ${isVerified ? 'text-emerald-400' : isPotential ? 'text-amber-400' : 'text-purple-400'}`}>
              {isVerified ? <ShieldCheck className="w-3 h-3" /> : <HelpCircle className="w-3 h-3" />}
              {verificationStatus.replace(/_/g, ' ')}
            </p>
          </div>
        </div>

        {/* Confidence */}
        {confidence !== null && (
          <div className="p-3 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)]">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)]">Confidence ({confidenceLevel})</p>
              <p className="text-lg font-bold text-[var(--text-primary)]">{confidence}%</p>
            </div>
            <div className="w-full bg-[var(--bg-primary)] h-2 rounded-full overflow-hidden border border-[var(--border-color)]">
              <div className={`h-full ${confidence >= 80 ? 'bg-emerald-500' : confidence >= 60 ? 'bg-amber-500' : 'bg-slate-500'}`} style={{ width: `${confidence}%` }} />
            </div>
          </div>
        )}

        {/* Warning */}
        {link.operational_warning && (
          <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-amber-300 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
            <p className="text-[12px] leading-relaxed">{link.operational_warning}</p>
          </div>
        )}

        {/* Evidence */}
        {link.evidence && link.evidence.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-[var(--text-muted)] mb-2 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
              Evidence ({link.evidence.length})
            </p>
            <div className="space-y-2">
              {link.evidence.map((ev, idx) => (
                <div key={idx} className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] space-y-1">
                  <div className="flex justify-between items-center text-[12px]">
                    <span className="font-medium text-[var(--accent-blue)]">{ev.record_number || ev.record_type?.toUpperCase()}</span>
                    {ev.timestamp && (
                      <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(ev.timestamp).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                  {ev.details && <p className="text-[12px] text-[var(--text-secondary)]">{ev.details}</p>}
                  {ev.factors && ev.factors.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {ev.factors.map((factor, fIdx) => (
                        <span key={fIdx} className="px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-primary)] text-[10px]">{factor}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {!link.evidence || link.evidence.length === 0 && (
          <p className="text-[12px] text-[var(--text-muted)] italic">No additional evidence records for this link.</p>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border-color shrink-0">
        <button onClick={onClose}
          className="w-full py-2 bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-[11px] uppercase rounded-lg font-semibold border border-[var(--border-color)] cursor-pointer transition-colors">
          Close
        </button>
      </div>
    </div>
  );
};

export default EdgeDetailPanel;
