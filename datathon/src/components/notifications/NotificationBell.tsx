import React, { useEffect, useRef, useState } from 'react';
import { Bell, BellDot, ExternalLink, CheckCheck, X, AlertTriangle, Info, AlertCircle } from 'lucide-react';
import { useNotificationStore } from '../../store/notificationStore';
import { useAppStore } from '../../store/appStore';
import { Badge } from '../ui/Badge';

export const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { setActiveTab } = useAppStore();

  const {
    counts,
    recentNotifications,
    loadingRecent,
    fetchCounts,
    fetchRecent,
    markRead,
    markAllRead,
    startPolling,
    stopPolling,
  } = useNotificationStore();

  useEffect(() => {
    fetchCounts();
    fetchRecent();
    startPolling(15000);
    return () => stopPolling();
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleNotificationClick = async (notificationId: string) => {
    await markRead(notificationId);
    setOpen(false);
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <AlertTriangle className="w-3.5 h-3.5 text-[var(--accent-coral)]" />;
      case 'high': return <AlertCircle className="w-3.5 h-3.5 text-[var(--accent-amber)]" />;
      case 'medium': return <Info className="w-3.5 h-3.5 text-[var(--accent-blue)]" />;
      default: return <Info className="w-3.5 h-3.5 text-[var(--text-muted)]" />;
    }
  };

  const getSeverityBorder = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-l-[var(--accent-coral)]';
      case 'high': return 'border-l-[var(--accent-amber)]';
      case 'medium': return 'border-l-[var(--accent-blue)]';
      default: return 'border-l-[var(--text-muted)]';
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      case_update: 'Case Update',
      evidence_update: 'Evidence',
      officer_update: 'Officer',
      ai_alert: 'AI Alert',
      crime_alert: 'Crime Alert',
      system_health: 'System',
    };
    return labels[type] || type;
  };

  const handleViewAll = () => {
    setActiveTab('notifications');
    setOpen(false);
  };

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
        title="Notifications"
      >
        {counts.unread > 0 ? (
          <BellDot className="w-[18px] h-[18px] text-[var(--accent-blue)]" />
        ) : (
          <Bell className="w-[18px] h-[18px]" />
        )}
        {counts.unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-[var(--accent-coral)] rounded-full text-[10px] font-bold text-[var(--text-primary)] flex items-center justify-center px-1">
            {counts.unread > 99 ? '99+' : counts.unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 md:w-96 bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-xl shadow-sk-xl overflow-hidden sk-fade-in" style={{ zIndex: 300 }}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border-secondary)]">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-[var(--text-primary)]">Notifications</span>
              {counts.critical > 0 && (
                <Badge variant="coral" size="xs" pulse>{counts.critical} Critical</Badge>
              )}
            </div>
            <div className="flex items-center gap-1">
              {counts.unread > 0 && (
                <button
                  onClick={() => { markAllRead(); setOpen(false); }}
                  className="p-1.5 rounded-md text-[var(--accent-blue)] hover:bg-[var(--accent-blue-subtle)] transition-colors cursor-pointer"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="max-h-72 overflow-y-auto">
            {loadingRecent ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-5 h-5 rounded-full border-2 border-[var(--accent-blue)] border-t-transparent animate-spin" />
              </div>
            ) : recentNotifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                <Bell className="w-8 h-8 text-[var(--text-disabled)] mb-2" />
                <p className="text-sm text-[var(--text-muted)]">No new notifications</p>
                <p className="text-xs text-[var(--text-disabled)] mt-1">System is operating normally</p>
              </div>
            ) : (
              recentNotifications.map((notif) => (
                <button
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif.id)}
                  className={`w-full text-left px-4 py-3 border-l-[3px] ${getSeverityBorder(notif.severity)} ${
                    notif.is_read
                      ? 'hover:bg-[var(--bg-tertiary)]/30'
                      : 'bg-[var(--accent-blue-subtle)]/50 hover:bg-[var(--accent-blue-subtle)]'
                  } transition-colors border-b border-[var(--border-secondary)]/50 cursor-pointer`}
                >
                  <div className="flex items-start gap-2.5">
                    <div className="mt-0.5 shrink-0">{getSeverityIcon(notif.severity)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-[13px] font-medium text-[var(--text-primary)] truncate">
                          {notif.title}
                        </span>
                        {!notif.is_read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-blue)] shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
                        {notif.message}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <Badge variant="default" size="xs">{getTypeLabel(notif.notification_type)}</Badge>
                        <span className="text-[10px] font-mono text-[var(--text-muted)]">
                          {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-[var(--border-secondary)] px-4 py-2.5">
            <button
              onClick={handleViewAll}
              className="w-full flex items-center justify-center gap-1.5 text-xs font-medium text-[var(--accent-blue)] hover:text-[var(--accent-blue-light)] transition-colors cursor-pointer"
            >
              <ExternalLink className="w-3 h-3" />
              View All Notifications
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
