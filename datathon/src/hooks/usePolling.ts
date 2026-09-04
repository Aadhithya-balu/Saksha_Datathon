import { useEffect, useRef } from 'react';

/**
 * Runs `callback` immediately (on mount) and then every `intervalMs`.
 * The callback is expected to be a silent background refresh (no loading
 * spinner). The interval is paused when the document is not visible
 * (tab hidden) to avoid unnecessary network traffic.
 */
export function usePolling(callback: () => void | Promise<void>, intervalMs = 30000) {
  const savedCallback = useRef(callback);
  savedCallback.current = callback;

  useEffect(() => {
    let active = true;
    let timerId: ReturnType<typeof setInterval> | null = null;

    const tick = () => {
      if (!active) return;
      Promise.resolve(savedCallback.current()).catch(() => {});
    };

    const onVisible = () => {
      if (document.visibilityState === 'visible') tick();
    };

    tick();
    timerId = setInterval(() => {
      if (document.visibilityState === 'visible') tick();
    }, intervalMs);

    document.addEventListener('visibilitychange', onVisible);
    return () => {
      active = false;
      if (timerId) clearInterval(timerId);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [intervalMs]);
}
