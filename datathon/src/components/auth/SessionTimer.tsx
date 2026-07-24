import React, { useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { Timer, AlertTriangle } from 'lucide-react';

export const SessionTimer: React.FC = () => {
  const {
    isAuthenticated,
    sessionTimeRemaining,
    tickSession,
    resetSessionTimer,
  } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) return;
    const timer = setInterval(() => tickSession(), 1000);
    return () => clearInterval(timer);
  }, [isAuthenticated, tickSession]);

  useEffect(() => {
    if (!isAuthenticated) return;
    const handleActivity = () => resetSessionTimer();
    const events = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    events.forEach((e) => window.addEventListener(e, handleActivity));
    return () => events.forEach((e) => window.removeEventListener(e, handleActivity));
  }, [isAuthenticated, resetSessionTimer]);

  if (!isAuthenticated) return null;

  const minutes = Math.floor(sessionTimeRemaining / 60);
  const seconds = sessionTimeRemaining % 60;
  const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  const isWarn = sessionTimeRemaining <= 300;

  return (
    <div
      className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border transition-all ${
        isWarn
          ? 'bg-[var(--accent-coral-subtle)] border-[var(--accent-coral)]/30 text-[var(--accent-coral)]'
          : 'bg-[var(--bg-tertiary)] border-[var(--border-secondary)] text-[var(--text-secondary)]'
      }`}
      title={isWarn ? 'Session expiring soon - activity will reset timer' : `Session time remaining: ${timeString}`}
    >
      {isWarn ? (
        <AlertTriangle className="w-3 h-3 animate-pulse" />
      ) : (
        <Timer className="w-3 h-3 text-[var(--accent-blue)]" />
      )}
      <span>{timeString}</span>
    </div>
  );
};

export default SessionTimer;
