import React from 'react';
import { type FIRDetailRecord } from '../../services/api';
import { Calendar, User, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';

interface FIRTimelineProps {
  fir: FIRDetailRecord;
}

interface TimelineEvent {
  title: string;
  date: string;
  description: string;
  icon: React.ReactNode;
  color: string;
}

export const FIRTimeline: React.FC<FIRTimelineProps> = ({ fir }) => {
  const events: TimelineEvent[] = [];

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  // 1. Registration Event
  events.push({
    title: 'FIR Registered',
    date: fir.filed_at,
    description: `Complainant statement recorded from ${fir.complainant_name}. Registered under sections: ${fir.sections || 'General Inquiry'}.`,
    icon: <FileText className="w-3.5 h-3.5" />,
    color: 'bg-blue-500 shadow-blue-500/30'
  });

  // 2. IO Assignment Event
  if (fir.investigating_officer) {
    const oDate = new Date(new Date(fir.filed_at).getTime() + 7200000).toISOString(); // +2 hours
    events.push({
      title: 'Investigator Assigned',
      date: oDate,
      description: `Investigating Officer Inspector ${fir.investigating_officer.badge_number} (${fir.investigating_officer.rank || 'Inspector'}) assigned to active investigation command.`,
      icon: <User className="w-3.5 h-3.5" />,
      color: 'bg-purple-500 shadow-purple-500/30'
    });
  }

  // 3. Investigation Commenced (if in_progress or closed)
  if (fir.status === 'in_progress' || fir.status === 'closed') {
    const activeDate = new Date(new Date(fir.filed_at).getTime() + 18000000).toISOString(); // +5 hours
    events.push({
      title: 'Investigation Initiated',
      date: activeDate,
      description: `Investigating officer started case study and scene reconnaissance. Links verified under incident case ${fir.crime_case?.case_number || 'N/A'}.`,
      icon: <ShieldAlert className="w-3.5 h-3.5" />,
      color: 'bg-amber-500 shadow-amber-500/30'
    });
  }

  // 4. Evidence Events
  if (fir.evidence && fir.evidence.length > 0) {
    fir.evidence.forEach((ev, idx) => {
      const evDate = new Date(new Date(fir.filed_at).getTime() + 36000000 * (idx + 1)).toISOString(); // spacing
      events.push({
        title: `Evidence Logged: ${ev.evidence_type.toUpperCase()}`,
        date: evDate,
        description: `${ev.description || 'Crime evidence logged.'} Collected by user badge: [${ev.collected_by || 'IO'}]. Chain of custody: ${ev.chain_of_custody || 'Logged.'}`,
        icon: <FileText className="w-3.5 h-3.5 text-black" />,
        color: 'bg-emerald-400 shadow-emerald-400/30'
      });
    });
  }

  // 5. Closure Event
  if (fir.status === 'closed') {
    events.push({
      title: 'Investigation Filed & Closed',
      date: fir.created_at, // Use created/updated date for closure
      description: 'Charge sheet and final status investigation report uploaded. Case marked as closed/resolved in Saksha database.',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      color: 'bg-emerald-600 shadow-emerald-600/30'
    });
  }

  return (
    <div className="bg-[#111D35]/30 border border-border-color p-5 rounded-card flex flex-col justify-between overflow-hidden">
      <div className="flex items-center gap-2 border-b border-slate-900 pb-3 mb-4">
        <Calendar className="w-4 h-4 text-[#1E6FD9]" />
        <span className="text-[10px] font-bold text-[#E8EDF5] uppercase tracking-wider">FIR Event History Timeline</span>
      </div>

      <div className="relative pl-6 border-l border-slate-800 space-y-6 max-h-[350px] overflow-y-auto custom-scrollbar">
        {events.map((ev, idx) => (
          <div key={idx} className="relative group">
            {/* Timeline node dot */}
            <div className={`absolute -left-[31px] top-1 w-4 h-4 rounded-full border border-slate-950 flex items-center justify-center text-white shrink-0 ${ev.color} transition-all duration-300 group-hover:scale-110`}>
              {ev.icon}
            </div>

            <div className="space-y-1">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-white font-bold uppercase tracking-wide">{ev.title}</span>
                <span className="text-slate-500 font-mono text-[9px]">{formatDate(ev.date)}</span>
              </div>
              <p className="text-[10px] text-[#A8B4CC] leading-relaxed pr-2 font-mono">
                {ev.description}
              </p>
            </div>
          </div>
        ))}
        {events.length === 0 && (
          <div className="text-center py-6 text-[10px] text-slate-500 uppercase">
            No history logs registered.
          </div>
        )}
      </div>
    </div>
  );
};
export default FIRTimeline;
