import React from 'react';
import { Sparkles, AlertTriangle, Info, TrendingUp, Shield, Search } from 'lucide-react';
import type { InvestigationAIRecommendation } from '../../services/api';

interface Props {
  recommendations: InvestigationAIRecommendation[];
}

const typeIcons: Record<string, React.ReactNode> = {
  priority: <AlertTriangle className="w-3.5 h-3.5" />,
  evidence: <Search className="w-3.5 h-3.5" />,
  workload: <TrendingUp className="w-3.5 h-3.5" />,
  aging: <AlertTriangle className="w-3.5 h-3.5" />,
  pattern: <Shield className="w-3.5 h-3.5" />,
  general: <Info className="w-3.5 h-3.5" />,
};

const priorityColors: Record<string, string> = {
  high: 'border-red-900/40 bg-red-950/15 hover:bg-red-950/25',
  medium: 'border-amber-900/40 bg-amber-950/15 hover:bg-amber-950/25',
  low: 'border-blue-900/40 bg-blue-950/15 hover:bg-blue-950/25',
};

const AIRecommendations: React.FC<Props> = ({ recommendations }) => {
  if (recommendations.length === 0) {
    return (
      <div className="p-5 bg-secondary-bg border border-border-color rounded-card relative overflow-hidden">
        <div className="absolute right-[-10px] bottom-[-10px] text-[#1E6FD9]/5 rotate-[15deg]">
          <Sparkles className="w-24 h-24" />
        </div>
        <h3 className="text-xs uppercase tracking-wider font-bold text-white flex items-center gap-2 mb-4 border-b border-border-color/60 pb-3">
          <Sparkles className="w-4 h-4 text-[#1E6FD9] animate-pulse" /> AI Intelligence
        </h3>
        <p className="text-[10px] text-[#6A7A96] py-3 text-center uppercase">NO AI RECOMMENDATIONS AVAILABLE.</p>
      </div>
    );
  }

  return (
    <div className="p-5 bg-secondary-bg border border-border-color rounded-card relative overflow-hidden">
      <div className="absolute right-[-10px] bottom-[-10px] text-[#1E6FD9]/5 rotate-[15deg]">
        <Sparkles className="w-24 h-24" />
      </div>

      <h3 className="text-xs uppercase tracking-wider font-bold text-white flex items-center gap-2 mb-4 border-b border-border-color/60 pb-3">
        <Sparkles className="w-4 h-4 text-[#1E6FD9] animate-pulse" /> SAKSHA AI Intelligence
        <span className="ml-auto text-[8px] text-[#6A7A96] font-normal">{recommendations.length} INSIGHTS</span>
      </h3>

      <div className="space-y-3 max-h-[350px] overflow-y-auto custom-scrollbar pr-1">
        {recommendations.map((rec, i) => (
          <div
            key={i}
            className={`p-3 border rounded flex gap-2.5 transition-colors cursor-default ${priorityColors[rec.priority] || priorityColors.medium}`}
          >
            <div className="p-1 bg-[#1E6FD9]/10 rounded text-[#1E6FD9] shrink-0 h-fit mt-0.5">
              {typeIcons[rec.type] || <Info className="w-3.5 h-3.5" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-bold text-white uppercase">{rec.title}</span>
                <span className={`px-1 py-0.5 text-[7px] rounded font-bold uppercase ${
                  rec.priority === 'high' ? 'bg-red-950/40 text-red-400' :
                  rec.priority === 'medium' ? 'bg-amber-950/40 text-amber-400' :
                  'bg-blue-950/40 text-blue-400'
                }`}>
                  {rec.priority}
                </span>
              </div>
              <p className="text-[9px] text-[#A8B4CC] leading-relaxed mt-1">{rec.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AIRecommendations;

