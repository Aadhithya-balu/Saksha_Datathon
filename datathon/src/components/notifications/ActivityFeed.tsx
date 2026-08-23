import React, { useEffect, useState } from 'react';
import { Activity, FileText, UserCheck, AlertTriangle, Shield, RefreshCw, Search } from 'lucide-react';
import { getActivityFeed } from '../../services/api';
import type { ActivityFeedResponse } from '../../services/api';

interface ActivityFeedProps {
  limit?: number;
  compact?: boolean;
}

export const ActivityFeed: React.FC<ActivityFeedProps> = ({ limit = 50, compact = false }) => {
  const [feed, setFeed] = useState<ActivityFeedResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventFilter, setEventFilter] = useState('');

  const loadFeed = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getActivityFeed(limit, eventFilter || undefined);
      setFeed(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load activity feed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeed();
  }, [eventFilter]);

  const getEventIcon = (eventType: string) => {
    if (eventType.includes('case') || eventType.includes('fir')) return <FileText className="w-3.5 h-3.5" />;
    if (eventType.includes('officer') || eventType.includes('user')) return <UserCheck className="w-3.5 h-3.5" />;
    if (eventType.includes('alert') || eventType.includes('anomaly')) return <AlertTriangle className="w-3.5 h-3.5" />;
    if (eventType.includes('system') || eventType.includes('health')) return <Shield className="w-3.5 h-3.5" />;
    return <Activity className="w-3.5 h-3.5" />;
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error': return 'text-[#C94A2A] border-l-[#C94A2A]';
      case 'warning': return 'text-[#D4820A] border-l-[#D4820A]';
      case 'success': return 'text-[#0E9E78] border-l-[#0E9E78]';
      default: return 'text-[#1E6FD9] border-l-[#1E6FD9]';
    }
  };

  const getEventColor = (eventType: string, severity: string) => {
    if (severity === 'error' || severity === 'warning') return getSeverityColor(severity);
    if (eventType.includes('update') || eventType.includes('created') || eventType.includes('registered')) {
      return 'text-[#0E9E78] border-l-[#0E9E78]';
    }
    if (eventType.includes('deleted') || eventType.includes('alert')) {
      return 'text-[#C94A2A] border-l-[#C94A2A]';
    }
    return 'text-[#1E6FD9] border-l-[#1E6FD9]';
  };

  const events = feed?.results || [];

  if (compact) {
    return (
      <div className="flex flex-col gap-2">
        {loading ? (
          <div className="flex items-center justify-center py-4">
            <div className="w-5 h-5 rounded-full border-2 border-[#1E6FD9] border-t-transparent animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-4 text-[8px] font-mono text-[var(--text-muted)]">No recent activity</div>
        ) : (
          events.slice(0, 10).map((event) => (
            <div key={event.id} className={`flex items-start gap-2.5 pl-2 border-l-2 ${getEventColor(event.event_type, event.severity)}`}>
              <div className="mt-0.5 shrink-0 opacity-70">
                {getEventIcon(event.event_type)}
              </div>
              <div className="min-w-0">
                <p className="text-[8.5px] font-mono text-[var(--text-primary)] truncate max-w-[200px]">{event.title}</p>
                <p className="text-[7px] font-mono text-[var(--text-muted)]">
                  {event.actor || 'System'} • {new Date(event.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 select-none">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-[#1E6FD9]" />
          <h3 className="text-[11px] font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider">
            Unified Activity Feed
          </h3>
        </div>
        <button
          onClick={loadFeed}
          className="flex items-center gap-1 px-2 py-1 hover:bg-[#1E6FD9]/10 rounded text-[#1E6FD9] text-[8px] font-mono cursor-pointer"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Search className="w-3 h-3 text-[var(--text-muted)]" />
        <select
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
          className="flex-1 px-2 py-1 bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded text-[9px] font-mono text-[var(--text-secondary)] outline-none focus:border-[#1E6FD9] cursor-pointer"
        >
          <option value="">All Events</option>
          <option value="case_created">Case Created</option>
          <option value="fir_registered">FIR Registered</option>
          <option value="evidence_added">Evidence Added</option>
          <option value="status_changed">Status Changed</option>
          <option value="ai_alert">AI Alerts</option>
          <option value="system_health">System Health</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="p-2 bg-[#C94A2A]/10 border border-[#C94A2A]/20 rounded text-[8px] font-mono text-[#C94A2A]">
          {error}
        </div>
      )}

      {/* Event List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar max-h-[400px]">
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-6 h-6 rounded-full border-2 border-[#1E6FD9] border-t-transparent animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-12">
            <Activity className="w-8 h-8 text-[var(--text-muted)] mx-auto mb-2 opacity-40" />
            <p className="text-[9px] font-mono text-[var(--text-muted)]">No activity found</p>
          </div>
        ) : (
          <div className="relative pl-4">
            {/* Timeline line */}
            <div className="absolute left-[7px] top-2 bottom-2 w-px bg-[var(--border-secondary)]" />
            
            <div className="space-y-0">
              {events.map((event) => (
                <div key={event.id} className="relative pb-4">
                  {/* Timeline dot */}
                  <div className={`absolute -left-[13px] top-1 w-2.5 h-2.5 rounded-full border-2 ${
                    event.severity === 'error' ? 'border-[#C94A2A] bg-[#C94A2A]/20' :
                    event.severity === 'warning' ? 'border-[#D4820A] bg-[#D4820A]/20' :
                    event.severity === 'success' ? 'border-[#0E9E78] bg-[#0E9E78]/20' :
                    'border-[#1E6FD9] bg-[#1E6FD9]/20'
                  }`} />
                  
                  <div className="flex items-start gap-2.5">
                    <div className={`mt-0.5 shrink-0 ${event.severity === 'error' ? 'text-[#C94A2A]' : event.severity === 'warning' ? 'text-[#D4820A]' : event.severity === 'success' ? 'text-[#0E9E78]' : 'text-[#1E6FD9]'}`}>
                      {getEventIcon(event.event_type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[9.5px] font-mono font-bold text-[var(--text-primary)] truncate">
                          {event.title}
                        </span>
                        <span className={`shrink-0 text-[7px] font-mono uppercase px-1 py-0.5 rounded ${
                          event.severity === 'error' ? 'bg-[#C94A2A]/10 text-[#C94A2A]' :
                          event.severity === 'warning' ? 'bg-[#D4820A]/10 text-[#D4820A]' :
                          event.severity === 'success' ? 'bg-[#0E9E78]/10 text-[#0E9E78]' :
                          'bg-[#1E6FD9]/10 text-[#1E6FD9]'
                        }`}>
                          {event.event_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-[8px] font-mono text-[var(--text-secondary)] mt-0.5 leading-relaxed">
                        {event.description}
                      </p>
                      <div className="flex items-center gap-3 mt-1">
                        {event.actor && (
                          <span className="text-[7px] font-mono text-[var(--text-muted)]">
                            by {event.actor} {event.actor_badge ? `(${event.actor_badge})` : ''}
                          </span>
                        )}
                        <span className="text-[7px] font-mono text-[var(--text-muted)]">
                          {new Date(event.timestamp).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {feed && (
        <div className="text-[7px] font-mono text-[var(--text-muted)] text-right border-t border-border-color pt-2">
          {feed.total} events loaded
        </div>
      )}
    </div>
  );
};

export default ActivityFeed;

