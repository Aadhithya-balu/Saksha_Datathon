import React, { useEffect } from 'react';
import { Mail, AlertTriangle, MessageSquare, CheckCircle, FileSearch, Radio } from 'lucide-react';
import { useNotificationStore } from '../../store/notificationStore';

interface SummaryCardsProps {
  onFilterBy?: (key: string, value: string) => void;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({ onFilterBy }) => {
  const { dashboard, loadingDashboard, fetchDashboard } = useNotificationStore();

  useEffect(() => {
    fetchDashboard();
  }, []);

  const cards = [
    {
      label: 'Unread Messages',
      value: dashboard?.unread_count ?? 0,
      icon: <Mail className="w-4 h-4" />,
      color: '#1E6FD9',
      filterKey: 'filterStatus',
      filterValue: 'unread',
    },
    {
      label: 'Critical Alerts',
      value: dashboard?.critical_alerts ?? 0,
      icon: <AlertTriangle className="w-4 h-4" />,
      color: '#C94A2A',
      filterKey: 'filterPriority',
      filterValue: 'critical',
    },
    {
      label: "Today's Messages",
      value: dashboard?.today_messages ?? 0,
      icon: <MessageSquare className="w-4 h-4" />,
      color: '#0E9E78',
      filterKey: null,
      filterValue: null,
    },
    {
      label: 'Pending Ack.',
      value: dashboard?.pending_acknowledgements ?? 0,
      icon: <CheckCircle className="w-4 h-4" />,
      color: '#D4820A',
      filterKey: 'filterStatus',
      filterValue: 'unread',
    },
    {
      label: 'Investigation Req.',
      value: dashboard?.investigation_requests ?? 0,
      icon: <FileSearch className="w-4 h-4" />,
      color: '#8B5CF6',
      filterKey: 'filterCategory',
      filterValue: 'investigation_update',
    },
    {
      label: 'Broadcasts',
      value: dashboard?.broadcast_messages ?? 0,
      icon: <Radio className="w-4 h-4" />,
      color: '#F472B6',
      filterKey: 'filterStatus',
      filterValue: 'all',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {cards.map((card) => (
        <button
          key={card.label}
          onClick={() => card.filterKey && onFilterBy?.(card.filterKey, card.filterValue)}
          disabled={!card.filterKey}
          className="flex items-center gap-3 p-3 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded-xl hover:border-[var(--border-active)] transition-all group cursor-pointer disabled:cursor-default"
        >
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            style={{ backgroundColor: `${card.color}15`, color: card.color }}
          >
            {card.icon}
          </div>
          <div className="min-w-0 text-left">
            <p className="text-lg font-bold text-[var(--text-primary)] leading-none">
              {loadingDashboard ? '—' : card.value}
            </p>
            <p className="text-[8px] font-mono text-[var(--text-muted)] uppercase tracking-wider mt-0.5 truncate">
              {card.label}
            </p>
          </div>
        </button>
      ))}
    </div>
  );
};

export default SummaryCards;
