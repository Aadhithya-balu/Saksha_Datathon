import { useEffect, useState } from 'react';
import { getSystemDataMode, type SystemDataModeResponse } from '../services/api';

/**
 * Runtime data-mode hook (Issue #190 §3, §5).
 *
 * Fetches the backend data mode once and caches it. Pages use this to decide
 * whether demo/seed fallback is permitted:
 *   - production: demo fallback is NOT permitted — show an honest error state.
 *   - demo/test:  fallback permitted and labelled.
 *
 * If the endpoint is unreachable the hook reports `error=true` so callers can
 * avoid silently substituting demo intelligence (fail-safe).
 */
interface UseDataModeResult {
  mode: SystemDataModeResponse['mode'] | null;
  allowsDemoFallback: boolean;
  isProduction: boolean;
  isDemo: boolean;
  isTest: boolean;
  loading: boolean;
  error: boolean;
}

let cachedPromise: Promise<SystemDataModeResponse> | null = null;

function fetchDataMode(): Promise<SystemDataModeResponse> {
  if (!cachedPromise) {
    cachedPromise = getSystemDataMode().catch((err) => {
      cachedPromise = null; // allow retry on next mount
      throw err;
    });
  }
  return cachedPromise;
}

export function useDataMode(): UseDataModeResult {
  const [mode, setMode] = useState<SystemDataModeResponse['mode'] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [allows, setAllows] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);
    fetchDataMode()
      .then((res) => {
        if (!active) return;
        setMode(res.mode);
        setAllows(res.allow_demo_fallback);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError(true);
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return {
    mode,
    allowsDemoFallback: allows,
    isProduction: mode === 'production' && !error,
    isDemo: mode === 'demo' && !error,
    isTest: mode === 'test' && !error,
    loading,
    error,
  };
}
