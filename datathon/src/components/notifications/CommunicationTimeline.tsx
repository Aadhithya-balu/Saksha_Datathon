import React from 'react';
import { Clock, User, Building, AlertTriangle, AlertCircle, Info, Radio, CheckCircle } from 'lucide-react';
import type { NotificationRecord } from '../../services/api';

interface CommunicationTimelineProps {
  notifications: NotificationRecord[];
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#C94A2A',
  high: '#D4820A',
  medium: '#1E6FD9',
  low: '#6A7A96',
};

const timeAgo = (dateStr: string) => {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
};

const formatTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

export const CommunicationTimeline: React.FC<CommunicationTimelineProps> = ({ notifications }) => {
  if (notifications.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Clock className="w-8 h-8 text-[var(--text-muted)] mb-2 opacity-30" />
        <p className="text-[10px] font-mono text-[var(--text-muted)] uppercase">No timeline events</p>
      </div>
    );
  }

  return (
    <div className="relative pl-6">
      {/* Timeline line */}
      <div className="absolute left-[11px] top-2 bottom-2 w-px bg-[var(--border-primary)]" />

      <div className="space-y-0">
        {notifications.map((n) => {
          const color = PRIORITY_COLORS[n.priority] || PRIORITY_COLORS.medium;
          const Icon = n.priority === 'critical' ? AlertTriangle : n.priority === 'high' ? AlertCircle : n.is_broadcast ? Radio : n.status === 'acknowledged' ? CheckCircle : Info;

          return (
            <div key={n.id} className="relative pb-4">
              {/* Timeline dot */}
              <div
                className="absolute -left-[19px] top-1.5 w-3 h-3 rounded-full border-2 bg-[var(--bg-elevated)]"
                style={{ borderColor: color }}
              />

              <div className="flex items-start gap-3">
                <div className="mt-0.5 shrink-0" style={{ color }}>
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[9.5px] font-bold text-[var(--text-primary)] truncate">
                      {n.subject}
                    </span>
                    <span
                      className="shrink-0 px-1.5 py-0.5 rounded text-[6.5px] font-mono font-bold uppercase border"
                      style={{ color, backgroundColor: `${color}10`, borderColor: `${color}20` }}
                    >
                      {n.priority}
                    </span>
                  </div>
                  <p className="text-[8px] font-mono text-[var(--text-secondary)] line-clamp-1 mb-1">
                    {n.message}
                  </p>
                  <div className="flex items-center gap-3">
                    {n.sender_name && (
                      <span className="flex items-center gap-1 text-[7px] font-mono text-[var(--text-muted)]">
                        <User className="w-2.5 h-2.5" />
                        {n.sender_badge || n.sender_name}
                      </span>
                    )}
                    <span className="flex items-center gap-1 text-[7px] font-mono text-[var(--text-muted)]">
                      <Building className="w-2.5 h-2.5" />
                      {n.is_broadcast ? 'ALL' : (n.recipient_name || '—')}
                    </span>
                    <span className="flex items-center gap-1 text-[7px] font-mono text-[var(--text-muted)]">
                      <Clock className="w-2.5 h-2.5" />
                      {formatTime(n.created_at)} ({timeAgo(n.created_at)})
                    </span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CommunicationTimeline;
