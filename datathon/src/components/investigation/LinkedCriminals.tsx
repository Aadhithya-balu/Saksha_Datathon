import React from 'react';
import { UserX, Fingerprint, AlertTriangle, FileText } from 'lucide-react';
import type { InvestigationCriminal } from '../../services/api';

interface Props {
  criminals: InvestigationCriminal[];
}

const getRiskColor = (score: number) => {
  if (score >= 80) return 'text-red-400 bg-red-950/30 border-red-900/40';
  if (score >= 60) return 'text-orange-400 bg-orange-950/30 border-orange-900/40';
  if (score >= 40) return 'text-yellow-400 bg-yellow-950/30 border-yellow-900/40';
  return 'text-green-400 bg-green-950/30 border-green-900/40';
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'at_large': return 'text-red-400';
    case 'arrested': return 'text-amber-400';
    case 'convicted': return 'text-purple-400';
    default: return 'text-gray-400';
  }
};

const LinkedCriminals: React.FC<Props> = ({ criminals }) => {
  if (criminals.length === 0) {
    return (
      <div className="p-5 bg-secondary-bg border border-border-color rounded-card">
        <h3 className="text-xs uppercase tracking-wider font-bold text-[var(--text-primary)] flex items-center gap-2 mb-4 border-b border-border-color/60 pb-3">
          <UserX className="w-4 h-4 text-red-400" /> Linked Criminals
        </h3>
        <p className="text-[10px] text-[var(--text-muted)] py-4 text-center uppercase">No criminals linked to this case.</p>
      </div>
    );
  }

  return (
    <div className="p-5 bg-secondary-bg border border-border-color rounded-card">
      <div className="flex justify-between items-center mb-4 border-b border-border-color/60 pb-3">
        <h3 className="text-xs uppercase tracking-wider font-bold text-[var(--text-primary)] flex items-center gap-2">
          <UserX className="w-4 h-4 text-red-400" /> Linked Criminals
        </h3>
        <span className="text-[10px] text-[var(--text-muted)] font-bold">{criminals.length} NAMED</span>
      </div>

      <div className="space-y-3 max-h-[350px] overflow-y-auto custom-scrollbar pr-1">
        {criminals.map((criminal) => (
          <div key={criminal.id} className="p-3 bg-[var(--bg-secondary)]/40 border border-border-color/40 rounded hover:border-red-900/30 transition-colors">
            {/* Header */}
            <div className="flex justify-between items-start">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold text-[var(--text-primary)] uppercase">{criminal.full_name}</span>
                  <span className={`text-[8px] uppercase font-bold ${getStatusColor(criminal.status)}`}>
                    [{criminal.status.replace(/_/g, ' ')}]
                  </span>
                </div>
                {criminal.aliases && (
                  <span className="text-[8px] text-[var(--text-muted)] mt-0.5 block">ALIAS: {criminal.aliases}</span>
                )}
              </div>
              <span className={`px-1.5 py-0.5 text-[8px] rounded font-bold uppercase border ${getRiskColor(criminal.risk_score)}`}>
                RISK: {criminal.risk_score}
              </span>
            </div>

            {/* Details */}
            <div className="grid grid-cols-2 gap-2 mt-2 text-[8.5px] text-[var(--text-secondary)]">
              {criminal.gender && (
                <span>GENDER: {criminal.gender}</span>
              )}
              <span className="flex items-center gap-1">
                <FileText className="w-3 h-3 text-[var(--text-muted)]" />
                {criminal.linked_fir_count} FIR(s)
              </span>
            </div>

            {/* Identifying marks */}
            {criminal.identifying_marks && (
              <div className="flex items-start gap-1.5 mt-2 text-[8px] text-[var(--text-muted)]">
                <Fingerprint className="w-3 h-3 text-cyan-500 mt-0.5 shrink-0" />
                <span>{criminal.identifying_marks}</span>
              </div>
            )}

            {/* MO Summary */}
            {criminal.mo_summary && (
              <div className="flex items-start gap-1.5 mt-1.5 text-[8px] text-[var(--text-muted)]">
                <AlertTriangle className="w-3 h-3 text-amber-500 mt-0.5 shrink-0" />
                <span>{criminal.mo_summary}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default LinkedCriminals;

