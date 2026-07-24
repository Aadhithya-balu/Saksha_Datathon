import React from 'react';
import { TrendingUp } from 'lucide-react';

interface Props {
  progress: number;
  status: string;
}

const CaseProgress: React.FC<Props> = ({ progress, status }) => {
  const getStatusLabel = (s: string) => {
    switch (s) {
      case 'closed': return 'RESOLVED';
      case 'charge sheet filed': return 'CHARGE SHEET FILED';
      case 'evidence collected': return 'EVIDENCE COLLECTED';
      case 'investigating': return 'INVESTIGATING';
      case 'assigned': return 'ASSIGNED';
      default: return 'OPEN';
    }
  };

  const getProgressColor = (p: number) => {
    if (p >= 100) return 'from-emerald-500 to-emerald-400';
    if (p >= 75) return 'from-blue-500 to-cyan-400';
    if (p >= 50) return 'from-amber-500 to-yellow-400';
    if (p >= 25) return 'from-orange-500 to-amber-400';
    return 'from-red-500 to-orange-400';
  };

  return (
    <div className="p-5 bg-secondary-bg border border-border-color rounded-card">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-xs uppercase tracking-wider font-bold text-[var(--text-primary)] flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-[var(--accent-teal)]" /> Case Progress
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[var(--text-muted)] uppercase">{getStatusLabel(status)}</span>
          <span className="text-xs font-bold text-[var(--accent-teal)]">{progress}%</span>
        </div>
      </div>

      <div className="h-3 bg-[var(--bg-secondary)] rounded-full overflow-hidden border border-[var(--border-primary)]">
        <div
          className={`h-full bg-gradient-to-r ${getProgressColor(progress)} transition-all duration-700 ease-out rounded-full`}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>

      {/* Progress milestones */}
      <div className="flex justify-between mt-2 text-[8px] text-[var(--text-muted)] uppercase">
        <span>INITIATED</span>
        <span>25%</span>
        <span>50%</span>
        <span>75%</span>
        <span>RESOLVED</span>
      </div>

      {/* Progress markers */}
      <div className="flex justify-between mt-1 relative">
        {[0, 25, 50, 75, 100].map((marker) => (
          <div key={marker} className="flex flex-col items-center">
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                progress >= marker ? 'bg-[var(--accent-teal)]' : 'bg-[var(--bg-elevated)]'
              } transition-colors duration-300`}
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default CaseProgress;

