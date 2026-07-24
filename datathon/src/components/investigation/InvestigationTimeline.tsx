import React from 'react';
import { Clock } from 'lucide-react';
import type { InvestigationTimelineEvent } from '../../services/api';

interface Props {
  events: InvestigationTimelineEvent[];
}

const categoryColors: Record<string, string> = {
  case: 'bg-blue-500 border-blue-400',
  fir: 'bg-amber-500 border-amber-400',
  evidence: 'bg-emerald-500 border-emerald-400',
  status: 'bg-purple-500 border-purple-400',
  note: 'bg-cyan-500 border-cyan-400',
};

const InvestigationTimeline: React.FC<Props> = ({ events }) => {
  if (events.length === 0) {
    return (
      <div className="p-5 bg-secondary-bg border border-border-color rounded-card">
        <h3 className="text-xs uppercase tracking-wider font-bold text-[var(--text-primary)] flex items-center gap-2 mb-4 border-b border-border-color/60 pb-3">
          <Clock className="w-4 h-4 text-purple-400" /> Investigation Timeline
        </h3>
        <p className="text-[10px] text-[var(--text-muted)] py-6 text-center uppercase">NO EVENTS LOGGED FOR THIS CASE.</p>
      </div>
    );
  }

  return (
    <div className="p-5 bg-secondary-bg border border-border-color rounded-card">
      <h3 className="text-xs uppercase tracking-wider font-bold text-[var(--text-primary)] flex items-center gap-2 mb-4 border-b border-border-color/60 pb-3">
        <Clock className="w-4 h-4 text-purple-400" /> Investigation Timeline
        <span className="ml-auto text-[8px] text-[var(--text-muted)] font-normal">{events.length} EVENTS</span>
      </h3>

      <div className="relative pl-4 border-l border-border-color/60 space-y-4 max-h-[400px] overflow-y-auto custom-scrollbar pr-1">
        {events.map((event, i) => (
          <div key={i} className="relative text-[11px]">
            <div className={`absolute left-[-20.5px] top-1.5 w-2.5 h-2.5 rounded-full border-2 border-[var(--border-primary)] ${categoryColors[event.category] || 'bg-[var(--bg-elevated)] border-[var(--border-secondary)]'}`} />
            <div className="text-[9px] text-[var(--text-muted)]">{new Date(event.timestamp).toLocaleString()}</div>
            <div className="font-bold text-[var(--text-primary)] uppercase mt-0.5 text-[11px]">{event.event}</div>
            {event.actor && (
              <div className="text-[9px] text-[var(--text-secondary)] mt-0.5">ACTOR: {event.actor}</div>
            )}
            <div className="text-[7.5px] text-[var(--text-muted)] uppercase mt-0.5">{event.category}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default InvestigationTimeline;

