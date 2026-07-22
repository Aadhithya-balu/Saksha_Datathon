import React, { useState } from 'react';
import { FileText, ShieldAlert, User, Database, ExternalLink, X } from 'lucide-react';
import type { ChatCitation } from '../../services/api';

interface CitationBadgeProps {
  citations: ChatCitation[];
}

export const CitationBadge: React.FC<CitationBadgeProps> = ({ citations }) => {
  const [activeCitation, setActiveCitation] = useState<ChatCitation | null>(null);

  if (!citations || citations.length === 0) return null;

  const getSourceIcon = (source: string) => {
    const s = source.toLowerCase();
    if (s.includes('fir')) return <FileText className="w-3 h-3 text-sky-400" />;
    if (s.includes('criminal') || s.includes('offender')) return <User className="w-3 h-3 text-amber-400" />;
    if (s.includes('evidence')) return <ShieldAlert className="w-3 h-3 text-rose-400" />;
    return <Database className="w-3 h-3 text-emerald-400" />;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.7) return 'text-emerald-400 border-emerald-500/30 bg-emerald-950/40';
    if (score >= 0.4) return 'text-amber-400 border-amber-500/30 bg-amber-950/40';
    return 'text-slate-400 border-slate-700 bg-slate-900/40';
  };

  return (
    <div className="mt-3 pt-3 border-t border-slate-900 select-none">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[8.5px] font-bold text-[#0E9E78] uppercase tracking-widest flex items-center gap-1 font-mono">
          <Database className="w-3 h-3" />
          Intelligence Citations ({citations.length})
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {citations.map((cit, idx) => {
          const scorePercent = Math.round(cit.score * 100);
          return (
            <button
              key={idx}
              onClick={() => setActiveCitation(cit)}
              className={`px-2.5 py-1.5 rounded border text-[9px] font-mono flex items-center gap-1.5 transition-all cursor-pointer hover:scale-[1.02] ${getScoreColor(
                cit.score
              )}`}
            >
              {getSourceIcon(cit.source)}
              <span className="font-semibold max-w-[160px] truncate">{cit.title}</span>
              <span className="opacity-75 text-[8px] font-bold">({scorePercent}%)</span>
              <ExternalLink className="w-2.5 h-2.5 opacity-60 ml-0.5" />
            </button>
          );
        })}
      </div>

      {/* Citation Detail Modal */}
      {activeCitation && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-[#0b1329] border border-slate-800 rounded-card p-5 max-w-lg w-full font-mono text-left shadow-2xl relative">
            <button
              onClick={() => setActiveCitation(null)}
              className="absolute top-3.5 right-3.5 text-slate-400 hover:text-white p-1 rounded transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2 mb-3">
              {getSourceIcon(activeCitation.source)}
              <span className="text-[9px] font-bold uppercase tracking-widest text-[#1E6FD9]">
                Source: {activeCitation.source}
              </span>
            </div>

            <h3 className="text-sm font-extrabold text-white mb-2">{activeCitation.title}</h3>

            <div className="p-3 bg-slate-950/80 border border-slate-900 rounded text-[10.5px] text-slate-300 leading-relaxed space-y-2">
              <div>
                <span className="text-slate-500 font-bold uppercase text-[8.5px] block">Relevance Match Confidence</span>
                <div className="flex items-center gap-2 mt-1">
                  <div className="flex-1 bg-slate-900 rounded-full h-1.5 overflow-hidden">
                    <div
                      className="bg-emerald-500 h-full rounded-full"
                      style={{ width: `${Math.round(activeCitation.score * 100)}%` }}
                    />
                  </div>
                  <span className="text-emerald-400 font-bold text-[10px]">
                    {Math.round(activeCitation.score * 100)}%
                  </span>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-900">
                <span className="text-slate-500 font-bold uppercase text-[8.5px] block">Document ID / Source</span>
                <p className="text-slate-200 mt-0.5">{activeCitation.title}</p>
              </div>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setActiveCitation(null)}
                className="px-4 py-1.5 bg-[#1E6FD9] hover:bg-[#1E6FD9]/85 text-white font-mono text-[10px] uppercase font-bold rounded cursor-pointer transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CitationBadge;
