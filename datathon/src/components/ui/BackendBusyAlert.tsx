import React, { useEffect, useRef, useState } from 'react';
import { Loader, X } from 'lucide-react';

interface BusyState {
  message: string;
}

/**
 * Global alert for transient backend infrastructure pressure (DB connection
 * pool exhaustion). The api layer dispatches a `system:backend-busy` window
 * event when the backend returns 503 DB_POOL_EXHAUSTED; this banner tells the
 * operator the system is saturated so they wait instead of retrying blindly.
 */
export const BackendBusyAlert: React.FC = () => {
  const [busy, setBusy] = useState<BusyState | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    const onBusy = (event: Event) => {
      const detail = (event as CustomEvent<{ message?: string }>).detail;
      setBusy({ message: detail?.message ?? 'Backend infrastructure is temporarily busy. Please wait a moment.' });
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setBusy(null), 9000);
    };

    window.addEventListener('system:backend-busy', onBusy);
    return () => {
      window.removeEventListener('system:backend-busy', onBusy);
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, []);

  if (!busy) return null;

  return (
    <div
      role="alert"
      className="fixed top-4 left-1/2 -translate-x-1/2 z-[300] max-w-[92vw] w-auto"
    >
      <div className="flex items-start gap-3 rounded-xl border border-[var(--accent-amber)]/40 bg-[var(--bg-tertiary)]/95 backdrop-blur px-4 py-3 shadow-[0_8px_30px_rgba(0,0,0,0.45)] font-mono">
        <Loader className="w-4 h-4 text-[var(--accent-amber)] animate-spin mt-0.5 shrink-0" />
        <div className="min-w-0">
          <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--accent-amber)]">
            Systems under load
          </div>
          <div className="text-xs text-[var(--text-secondary)] mt-0.5">
            {busy.message}
          </div>
          <div className="text-[10px] text-[var(--text-muted)] mt-1">
            Safe reads are retried automatically once capacity frees up.
          </div>
        </div>
        <button
          type="button"
          onClick={() => setBusy(null)}
          className="shrink-0 p-1 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
          title="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

export default BackendBusyAlert;