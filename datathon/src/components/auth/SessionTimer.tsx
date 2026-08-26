import React, { useEffect, useRef } from 'react';
import { useAuthStore } from '../../store/authStore';
import { Timer, AlertTriangle } from 'lucide-react';

const IDLE_TIMEOUT_S = 30 * 60;      // 30 min idle → logout
const HARD_CAP_S     = 8 * 60 * 60; // 8 hr hard cap regardless of activity
const WARN_AT_S      = 5 * 60;       // warn when ≤ 5 min remain

// Only meaningful interactions reset the idle clock — not mouse movement or scroll
const ACTIVITY_EVENTS = ['click', 'keydown', 'touchstart'] as const;

export const SessionTimer: React.FC = () => {
  const {
    isAuthenticated,
    sessionTimeRemaining,
    tickSession,
    resetSessionTimer,
  } = useAuthStore();

  // Hard cap: track total session age independently of idle resets
  const sessionStartRef = useRef<number>(Date.now());
  const hardCapTriggered = useRef(false);

  // Reset session start ref whenever a new login occurs
  useEffect(() => {
    if (isAuthenticated) {
      sessionStartRef.current = Date.now();
      hardCapTriggered.current = false;
    }
  }, [isAuthenticated]);

  // Tick every second — also enforce hard cap
  useEffect(() => {
    if (!isAuthenticated) return;
    const timer = setInterval(() => {
      const sessionAgeS = Math.floor((Date.now() - sessionStartRef.current) / 1000);
      if (!hardCapTriggered.current && sessionAgeS >= HARD_CAP_S) {
        hardCapTriggered.current = true;
        useAuthStore.getState().logout(true);
        return;
      }
      tickSession();
    }, 1000);
    return () => clearInterval(timer);
  }, [isAuthenticated, tickSession]);

  // Reset idle timer only on meaningful user interactions
  useEffect(() => {
    if (!isAuthenticated) return;
    const handleActivity = () => resetSessionTimer();
    ACTIVITY_EVENTS.forEach((e) => window.addEventListener(e, handleActivity));
    return () => ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, handleActivity));
  }, [isAuthenticated, resetSessionTimer]);

  if (!isAuthenticated) return null;

  const minutes = Math.floor(sessionTimeRemaining / 60);
  const seconds = sessionTimeRemaining % 60;
  const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  const isWarn = sessionTimeRemaining <= WARN_AT_S;

  return (
    <div
      className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border transition-all ${
        isWarn
          ? 'bg-[var(--accent-coral-subtle)] border-[var(--accent-coral)]/30 text-[var(--accent-coral)]'
          : 'bg-[var(--bg-tertiary)] border-[var(--border-secondary)] text-[var(--text-secondary)]'
      }`}
      title={isWarn ? 'Session expiring soon — click or type anything to stay logged in' : `Idle timeout: ${timeString}`}
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
