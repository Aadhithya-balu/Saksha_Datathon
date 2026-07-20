import React from 'react';
import { Package, FileDigit, User, Link, Clock } from 'lucide-react';
import type { InvestigationEvidence } from '../../services/api';

interface Props {
  evidence: InvestigationEvidence[];
}

const typeConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  digital: { icon: <FileDigit className="w-3.5 h-3.5" />, color: 'text-cyan-400 bg-cyan-950/30 border-cyan-900/40' },
  physical: { icon: <Package className="w-3.5 h-3.5" />, color: 'text-amber-400 bg-amber-950/30 border-amber-900/40' },
  document: { icon: <FileDigit className="w-3.5 h-3.5" />, color: 'text-blue-400 bg-blue-950/30 border-blue-900/40' },
  biological: { icon: <Package className="w-3.5 h-3.5" />, color: 'text-red-400 bg-red-950/30 border-red-900/40' },
};

const LinkedEvidence: React.FC<Props> = ({ evidence }) => {
  if (evidence.length === 0) {
    return (
      <div className="p-5 bg-secondary-bg border border-border-color rounded-card">
        <h3 className="text-xs uppercase tracking-wider font-bold text-white flex items-center gap-2 mb-4 border-b border-border-color/60 pb-3">
          <Package className="w-4 h-4 text-emerald-400" /> Evidence Registry
        </h3>
        <p className="text-[10px] text-[#6A7A96] py-4 text-center uppercase">No evidence logged for this case.</p>
      </div>
    );
  }

  return (
    <div className="p-5 bg-secondary-bg border border-border-color rounded-card">
      <div className="flex justify-between items-center mb-4 border-b border-border-color/60 pb-3">
        <h3 className="text-xs uppercase tracking-wider font-bold text-white flex items-center gap-2">
          <Package className="w-4 h-4 text-emerald-400" /> Evidence Registry
        </h3>
        <span className="text-[10px] text-[#6A7A96] font-bold">{evidence.length} ITEMS</span>
      </div>

      <div className="space-y-3 max-h-[350px] overflow-y-auto custom-scrollbar pr-1">
        {evidence.map((item) => {
          const config = typeConfig[item.evidence_type] || typeConfig.document;
          return (
            <div key={item.id} className="p-3 bg-slate-950/40 border border-border-color/40 rounded hover:border-emerald-900/30 transition-colors">
              {/* Header */}
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <span className={`p-1 rounded ${config.color}`}>{config.icon}</span>
                  <span className="text-[10px] font-bold text-white uppercase">{item.evidence_type}</span>
                </div>
                <span className={`px-1.5 py-0.5 text-[8px] rounded font-bold uppercase border ${config.color}`}>
                  {item.evidence_type}
                </span>
              </div>

              {/* Description */}
              {item.description && (
                <p className="text-[9px] text-[#A8B4CC] leading-relaxed mb-2">{item.description}</p>
              )}

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-2 text-[8px] text-[#6A7A96]">
                {item.collected_by && (
                  <div className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    <span>COLLECTED BY: {item.collected_by}</span>
                  </div>
                )}
                {item.created_at && (
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                )}
              </div>

              {/* Chain of custody */}
              {item.chain_of_custody && (
                <div className="flex items-start gap-1.5 mt-2 pt-2 border-t border-slate-900 text-[8px] text-[#6A7A96]">
                  <Link className="w-3 h-3 text-cyan-500 mt-0.5 shrink-0" />
                  <span className="leading-relaxed">{item.chain_of_custody}</span>
                </div>
              )}

              {/* File URL */}
              {item.file_url && (
                <div className="mt-1.5">
                  <span className="text-[7.5px] text-blue-500 uppercase truncate block">{item.file_url}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default LinkedEvidence;

