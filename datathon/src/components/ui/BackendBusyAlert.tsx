import React, { useEffect, useRef, useState } from 'react';
import { Loader, WifiOff, X } from 'lucide-react';

interface BusyState {
  message: string;
}

/** After this long of continuous backend failure, show the sticky alert. */
const DEGRADED_THRESHOLD_MS = 60000;

/**
 * Global alerts for backend infrastructure pressure (DB connection pool
 * exhaustion / Supabase free-tier throttling).
 *
 * - A single transient failure shows a short banner ("Systems under load").
 * - If failures persist for 60s, a persistent "Database connection lost" alert
 *   explains the free-tier throttling and that developers will rectify it; it
 *   clears automatically once traffic succeeds again (system:backend-ok).
 */
export const BackendBusyAlert: React.FC = () => {
  const [busy, setBusy] = useState<BusyState | null>(null);
  const [degraded, setDegraded] = useState(false);
  const timer = useRef<number | null>(null);
  const checkTimer = useRef<number | null>(null);
  const degradedSince = useRef<number | null>(null);
  const dismissed = useRef(false);

  const scheduleDegradedCheck = () => {
    if (checkTimer.current) window.clearTimeout(checkTimer.current);
    const elapsed = degradedSince.current === null ? 0 : Date.now() - degradedSince.current;
    const remaining = Math.max(DEGRADED_THRESHOLD_MS - elapsed, 0) + 500;
    checkTimer.current = window.setTimeout(() => {
      if (
        degradedSince.current !== null &&
        !dismissed.current &&
        Date.now() - degradedSince.current >= DEGRADED_THRESHOLD_MS
      ) {
        setDegraded(true);
      }
    }, remaining);
  };

  useEffect(() => {
    const onBusy = (event: Event) => {
      const detail = (event as CustomEvent<{ message?: string }>).detail;
      setBusy({ message: detail?.message ?? 'Backend infrastructure is temporarily busy. Please wait a moment.' });
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setBusy(null), 9000);

      if (degradedSince.current === null) {
        degradedSince.current = Date.now();
        dismissed.current = false;
        scheduleDegradedCheck();
      }
    };

    const onOk = () => {
      degradedSince.current = null;
      dismissed.current = false;
      if (checkTimer.current) window.clearTimeout(checkTimer.current);
      setDegraded(false);
    };

    window.addEventListener('system:backend-busy', onBusy);
    window.addEventListener('system:backend-ok', onOk);
    return () => {
      window.removeEventListener('system:backend-busy', onBusy);
      window.removeEventListener('system:backend-ok', onOk);
      if (timer.current) window.clearTimeout(timer.current);
      if (checkTimer.current) window.clearTimeout(checkTimer.current);
    };
  }, []);

  const dismissDegraded = () => {
    dismissed.current = true;
    setDegraded(false);
  };

  return (
    <>
      {busy && (
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
      )}

      {degraded && (
        <div
          role="alert"
          className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[300] max-w-[92vw] w-auto"
        >
          <div className="flex items-start gap-3 rounded-xl border border-[var(--accent-coral)]/50 bg-[var(--bg-tertiary)]/95 backdrop-blur px-4 py-3 shadow-[0_8px_30px_rgba(0,0,0,0.45)] font-mono">
            <WifiOff className="w-4 h-4 text-[var(--accent-coral)] animate-pulse mt-0.5 shrink-0" />
            <div className="min-w-0">
              <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--accent-coral)]">
                Database connection lost
              </div>
              <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                The database connection has been unavailable for over a minute. This is likely due
                to throttling on the free-tier (Supabase) plan. Our developers will rectify this
                shortly — please check back later.
              </div>
              <div className="text-[10px] text-[var(--text-muted)] mt-1">
                This alert clears automatically once the connection recovers.
              </div>
            </div>
            <button
              type="button"
              onClick={dismissDegraded}
              className="shrink-0 p-1 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)] transition-colors cursor-pointer"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default BackendBusyAlert;