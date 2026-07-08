import React, { useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { Timer, AlertTriangle, ShieldCheck } from 'lucide-react';

export const SessionTimer: React.FC = () => {
  const {
    isAuthenticated,
    sessionTimeRemaining,
    tickSession,
    resetSessionTimer,
    logout
  } = useAuthStore();

  // Ticks session timer every second
  useEffect(() => {
    if (!isAuthenticated) return;

    const timer = setInterval(() => {
      tickSession();
    }, 1000);

    return () => clearInterval(timer);
  }, [isAuthenticated, tickSession]);

  // Track global user interactivity to reset timer
  useEffect(() => {
    if (!isAuthenticated) return;

    const handleActivity = () => {
      resetSessionTimer();
    };

    // Events to monitor user activity
    const activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
    
    activityEvents.forEach((event) => {
      window.addEventListener(event, handleActivity);
    });

    return () => {
      activityEvents.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
    };
  }, [isAuthenticated, resetSessionTimer]);

  if (!isAuthenticated) return null;

  // Format time remaining MM:SS
  const minutes = Math.floor(sessionTimeRemaining / 60);
  const seconds = sessionTimeRemaining % 60;
  const timeString = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;

  // Countdown alerts triggers under 5 minutes (300 seconds)
  const isWarnPeriod = sessionTimeRemaining <= 300;

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full font-mono text-[11px] border transition-all duration-300 ${
      isWarnPeriod 
        ? 'bg-[#C94A2A]/15 border-[#C94A2A] text-[#C94A2A] shadow-glow-coral animate-[pulse_2s_infinite]' 
        : 'bg-[#111D35] border-border-color text-[#A8B4CC]'
    }`}>
      {isWarnPeriod ? (
        <AlertTriangle className="w-3.5 h-3.5 text-[#C94A2A] animate-bounce" />
      ) : (
        <Timer className="w-3.5 h-3.5 text-[#1E6FD9]" />
      )}
      
      <span>
        {isWarnPeriod ? 'SECURE TIMER:' : 'SESSION:'} {timeString}
      </span>

      {isWarnPeriod && (
        <span className="hidden md:inline text-[9px] uppercase tracking-wider pl-1 border-l border-[#C94A2A]/30">
          LOGOUT IMMINENT
        </span>
      )}
    </div>
  );
};

export default SessionTimer;
