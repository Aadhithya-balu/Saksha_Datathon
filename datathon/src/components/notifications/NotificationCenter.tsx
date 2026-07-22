import React, { useEffect, useState } from 'react';
import {
  X,
  CheckCheck,
  AlertTriangle,
  AlertCircle,
  Info,
  Trash2,
  Bell,
  Filter,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useNotificationStore } from '../../store/notificationStore';

interface NotificationCenterProps {
  onClose?: () => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ onClose }) => {
  const {
    notifications,
    counts,
    total,
    page,
    pageSize,
    loading,
    error,
    fetchNotifications,
    markRead,
    markAllRead,
    dismiss,
    setPage,
    startPolling,
    stopPolling,
  } = useNotificationStore();

  const [typeFilter, setTypeFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [unreadOnly, setUnreadOnly] = useState(false);

  useEffect(() => {
    fetchNotifications(1, pageSize, unreadOnly, typeFilter || undefined, severityFilter || undefined);
    startPolling(15000);
    return () => stopPolling();
  }, [typeFilter, severityFilter, unreadOnly]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <AlertTriangle className="w-4 h-4 text-[#C94A2A]" />;
      case 'high': return <AlertCircle className="w-4 h-4 text-[#D4820A]" />;
      case 'medium': return <Info className="w-4 h-4 text-[#1E6FD9]" />;
      default: return <Info className="w-4 h-4 text-[#6A7A96]" />;
    }
  };

  const getSeverityBadge = (severity: string) => {
    const styles: Record<string, string> = {
      critical: 'bg-[#C94A2A]/10 text-[#C94A2A] border border-[#C94A2A]/20',
      high: 'bg-[#D4820A]/10 text-[#D4820A] border border-[#D4820A]/20',
      medium: 'bg-[#1E6FD9]/10 text-[#1E6FD9] border border-[#1E6FD9]/20',
      low: 'bg-[#6A7A96]/10 text-[#6A7A96] border border-[#6A7A96]/20',
    };
    return styles[severity] || styles.low;
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      case_update: 'Case Update',
      evidence_update: 'Evidence Update',
      officer_update: 'Officer Update',
      ai_alert: 'AI Alert',
      crime_alert: 'Crime Alert',
      system_health: 'System Health',
    };
    return labels[type] || type;
  };

  const handleRefresh = () => {
    fetchNotifications(page, pageSize, unreadOnly, typeFilter || undefined, severityFilter || undefined);
  };

  return (
    <div className="h-full flex flex-col select-none">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border-color shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-[#1E6FD9]" />
            <h2 className="text-sm font-mono font-bold text-white uppercase tracking-wider">
              Notification Center
            </h2>
          </div>
          {counts.critical > 0 && (
            <span className="px-2 py-0.5 bg-[#C94A2A]/10 text-[#C94A2A] rounded-full text-[8px] font-bold font-mono border border-[#C94A2A]/20 animate-pulse">
              {counts.critical} CRITICAL
            </span>
          )}
          <span className="text-[8px] font-mono text-[#6A7A96]">
            {total} total • {counts.unread} unread
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleRefresh}
            className="p-1.5 hover:bg-[#1E6FD9]/10 rounded text-[#1E6FD9] cursor-pointer"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {counts.unread > 0 && (
            <button
              onClick={markAllRead}
              className="flex items-center gap-1 px-2 py-1.5 hover:bg-[#1E6FD9]/10 rounded text-[#1E6FD9] text-[8px] font-mono uppercase cursor-pointer"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark All Read
            </button>
          )}
          {onClose && (
            <button onClick={onClose} className="p-1.5 hover:bg-white/5 rounded text-[#6A7A96] cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 p-3 border-b border-border-color shrink-0">
        <Filter className="w-3.5 h-3.5 text-[#6A7A96]" />
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
          className="px-2 py-1 bg-slate-950 border border-slate-900 rounded text-[9px] font-mono text-[#A8B4CC] outline-none focus:border-[#1E6FD9] cursor-pointer"
        >
          <option value="">All Types</option>
          <option value="case_update">Case Updates</option>
          <option value="evidence_update">Evidence Updates</option>
          <option value="officer_update">Officer Updates</option>
          <option value="ai_alert">AI Alerts</option>
          <option value="crime_alert">Crime Alerts</option>
          <option value="system_health">System Health</option>
        </select>
        <select
          value={severityFilter}
          onChange={(e) => { setSeverityFilter(e.target.value); setPage(1); }}
          className="px-2 py-1 bg-slate-950 border border-slate-900 rounded text-[9px] font-mono text-[#A8B4CC] outline-none focus:border-[#1E6FD9] cursor-pointer"
        >
          <option value="">All Severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <label className="flex items-center gap-1.5 text-[9px] font-mono text-[#A8B4CC] cursor-pointer">
          <input
            type="checkbox"
            checked={unreadOnly}
            onChange={(e) => { setUnreadOnly(e.target.checked); setPage(1); }}
            className="w-3 h-3 accent-[#1E6FD9]"
          />
          Unread Only
        </label>
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-2 p-2 bg-[#C94A2A]/10 border border-[#C94A2A]/20 rounded text-[9px] font-mono text-[#C94A2A]">
          {error}
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {loading && notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-8 h-8 rounded-full border-2 border-[#1E6FD9] border-t-transparent animate-spin" />
            <p className="mt-3 text-[9px] font-mono text-[#6A7A96] uppercase">Loading notifications...</p>
          </div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center px-4">
            <Bell className="w-12 h-12 text-[#6A7A96] mb-3 opacity-30" />
            <p className="text-[10px] font-mono text-[#6A7A96] uppercase font-bold">No notifications</p>
            <p className="text-[8px] font-mono text-[#6A7A96]/60 mt-1">
              {unreadOnly ? 'All notifications are read' : 'No notifications match the current filters'}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.03]">
            {notifications.map((notif) => (
              <div
                key={notif.id}
                className={`px-4 py-3.5 transition-colors ${
                  notif.is_read ? 'opacity-70 hover:opacity-100' : 'bg-[#1E6FD9]/[0.02]'
                } hover:bg-white/[0.02]`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">
                    {getSeverityIcon(notif.severity)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[10.5px] font-mono font-bold text-white truncate">
                          {notif.title}
                        </span>
                        {!notif.is_read && (
                          <span className="w-2 h-2 rounded-full bg-[#1E6FD9] shrink-0 animate-pulse" />
                        )}
                      </div>
                      <span className={`shrink-0 px-1.5 py-0.5 rounded text-[7px] font-bold font-mono uppercase ${getSeverityBadge(notif.severity)}`}>
                        {notif.severity}
                      </span>
                    </div>
                    <p className="text-[9px] font-mono text-[#A8B4CC] leading-relaxed mb-2">
                      {notif.message}
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[7.5px] font-mono text-[#6A7A96] uppercase bg-white/[0.03] px-1.5 py-0.5 rounded">
                          {getTypeLabel(notif.notification_type)}
                        </span>
                        <span className="text-[7.5px] font-mono text-[#6A7A96]">
                          {new Date(notif.created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        {!notif.is_read && (
                          <button
                            onClick={() => markRead(notif.id)}
                            className="p-1 hover:bg-[#1E6FD9]/10 rounded text-[#1E6FD9] cursor-pointer"
                            title="Mark as read"
                          >
                            <CheckCheck className="w-3 h-3" />
                          </button>
                        )}
                        <button
                          onClick={() => dismiss(notif.id)}
                          className="p-1 hover:bg-[#C94A2A]/10 rounded text-[#6A7A96] hover:text-[#C94A2A] cursor-pointer"
                          title="Dismiss"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between p-3 border-t border-border-color shrink-0">
        <span className="text-[8px] font-mono text-[#6A7A96]">
          Page {page} of {totalPages} ({total} items)
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPage(page - 1)}
            disabled={page <= 1}
            className="p-1 hover:bg-[#1E6FD9]/10 rounded text-[#6A7A96] hover:text-[#1E6FD9] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= totalPages}
            className="p-1 hover:bg-[#1E6FD9]/10 rounded text-[#6A7A96] hover:text-[#1E6FD9] disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationCenter;

