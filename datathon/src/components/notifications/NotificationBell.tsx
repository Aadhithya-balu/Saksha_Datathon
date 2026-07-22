import React, { useEffect, useRef, useState } from 'react';
import { Bell, BellDot, ExternalLink, CheckCheck, X, AlertTriangle, Info, AlertCircle, ShieldAlert } from 'lucide-react';
import { useNotificationStore } from '../../store/notificationStore';

interface NotificationBellProps {
  onViewAll?: () => void;
}

export const NotificationBell: React.FC<NotificationBellProps> = ({ onViewAll }) => {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  // Close dropdown on outside click
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
      case 'critical': return <AlertTriangle className="w-3.5 h-3.5 text-[#C94A2A]" />;
      case 'high': return <AlertCircle className="w-3.5 h-3.5 text-[#D4820A]" />;
      case 'medium': return <Info className="w-3.5 h-3.5 text-[#1E6FD9]" />;
      default: return <Info className="w-3.5 h-3.5 text-[#6A7A96]" />;
    }
  };

  const getSeverityBorder = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-l-[#C94A2A]';
      case 'high': return 'border-l-[#D4820A]';
      case 'medium': return 'border-l-[#1E6FD9]';
      default: return 'border-l-[#6A7A96]';
    }
  };

  const getTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      case_update: 'Case Update',
      evidence_update: 'Evidence Update',
      officer_update: 'Officer Update',
      ai_alert: 'AI Alert',
      crime_alert: 'Crime Alert',
      system_health: 'System',
    };
    return labels[type] || type;
  };

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 hover:bg-white/5 border border-border-color rounded-lg text-[#A8B4CC] hover:text-white cursor-pointer transition-all group"
        title="Notifications"
      >
        {counts.unread > 0 ? (
          <BellDot className="w-4.5 h-4.5 text-[#1E6FD9] group-hover:text-white transition-colors" />
        ) : (
          <Bell className="w-4.5 h-4.5 group-hover:text-white transition-colors" />
        )}
        
        {/* Badge */}
        {counts.unread > 0 && (
          <span className="absolute -top-1 -right-1 w-4.5 h-4.5 bg-[#C94A2A] rounded-full text-[7px] font-bold text-white flex items-center justify-center border border-[#0a0e1a] shadow-[0_0_8px_rgba(201,74,42,0.6)]">
            {counts.unread > 99 ? '99+' : counts.unread}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 md:w-96 bg-secondary-bg border border-border-color rounded-xl shadow-2xl shadow-black/50 overflow-hidden z-50 animate-[fadeIn_0.15s_ease-out]">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-color">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-bold text-white uppercase tracking-wider">Notifications</span>
              {counts.critical > 0 && (
                <span className="px-1.5 py-0.5 bg-[#C94A2A]/10 border border-[#C94A2A]/20 rounded text-[7.5px] text-[#C94A2A] font-bold font-mono animate-pulse">
                  {counts.critical} CRITICAL
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {counts.unread > 0 && (
                <button
                  onClick={() => { markAllRead(); setOpen(false); }}
                  className="p-1 hover:bg-[#1E6FD9]/10 rounded text-[#1E6FD9] text-[8px] font-mono uppercase flex items-center gap-1 cursor-pointer"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-3 h-3" />
                  <span className="hidden md:inline">Mark Read</span>
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1 hover:bg-white/5 rounded text-[#6A7A96] cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* List */}
          <div className="max-h-72 overflow-y-auto custom-scrollbar">
            {loadingRecent ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-5 h-5 rounded-full border-2 border-[#1E6FD9] border-t-transparent animate-spin" />
              </div>
            ) : recentNotifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center px-4">
                <Bell className="w-8 h-8 text-[#6A7A96] mb-2 opacity-40" />
                <p className="text-[9px] font-mono text-[#6A7A96] uppercase">No new notifications</p>
                <p className="text-[7.5px] font-mono text-[#6A7A96]/60 mt-1">System is operating normally</p>
              </div>
            ) : (
              recentNotifications.map((notif) => (
                <button
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif.id)}
                  className={`w-full text-left px-4 py-3 border-l-[3px] ${getSeverityBorder(notif.severity)} ${
                    notif.is_read ? 'bg-transparent hover:bg-white/[0.02]' : 'bg-[#1E6FD9]/[0.03] hover:bg-[#1E6FD9]/[0.06]'
                  } transition-colors border-b border-white/[0.03] cursor-pointer group`}
                >
                  <div className="flex items-start gap-2.5">
                    <div className="mt-0.5 shrink-0">
                      {getSeverityIcon(notif.severity)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className="text-[9px] font-mono font-bold text-white truncate">
                          {notif.title}
                        </span>
                        {!notif.is_read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-[#1E6FD9] shrink-0 animate-pulse" />
                        )}
                      </div>
                      <p className="text-[8.5px] font-mono text-[#A8B4CC] line-clamp-2 leading-relaxed">
                        {notif.message}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-[7.5px] font-mono text-[#6A7A96] uppercase px-1.5 py-0.5 bg-white/[0.03] rounded">
                          {getTypeLabel(notif.notification_type)}
                        </span>
                        <span className="text-[7.5px] font-mono text-[#6A7A96]">
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
          <div className="border-t border-border-color px-4 py-2.5">
            <button
              onClick={() => { onViewAll?.(); setOpen(false); }}
              className="w-full flex items-center justify-center gap-1.5 text-[9px] font-mono text-[#1E6FD9] hover:text-white transition-colors uppercase tracking-wider font-bold cursor-pointer"
            >
              <ExternalLink className="w-3 h-3" />
              View Notification Center
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;

