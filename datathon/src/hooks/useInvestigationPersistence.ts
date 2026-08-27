import { useCallback, useEffect, useState } from 'react';
import { useAuthStore } from '../store/authStore';

/**
 * Investigation persistence — recent + saved investigations, scoped per officer
 * (keyed by badge ID). Only stores lightweight identifiers + labels, never
 * sensitive narrative content, and respects a fixed retention cap.
 *
 * Backs the "Recent Investigations" and "Saved Investigations" end-user
 * features (brief §12/§13/§20).
 */

export interface StoredInvestigation {
  /** Type discriminator so we can deep-link back into the right context. */
  type: 'person' | 'case' | 'fir' | 'mo' | 'search';
  /** Stable identifier (criminal id, case id, fir id...) or the search term. */
  id: string;
  /** Human label, e.g. "Ravi Kumar" or "CR-2026-KA-0001". */
  label: string;
  /** Short context, e.g. district / FIR number / query hint. */
  detail?: string;
  ts: number;
}

const RECENT_CAP = 12;
const RECENT_KEY = 'saksha_investigation_recent_v2';
const SAVED_KEY = 'saksha_investigation_saved_v2';

function load(key: string): StoredInvestigation[] {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as StoredInvestigation[]) : [];
  } catch {
    return [];
  }
}

function save(key: string, items: StoredInvestigation[]) {
  try {
    localStorage.setItem(key, JSON.stringify(items));
  } catch {
    // storage unavailable — degrade gracefully
  }
}

export function useInvestigationPersistence() {
  const badge = useAuthStore((state) => state.user?.badgeId) || 'unknown';
  const scope = `[${badge}]`;

  const [recent, setRecent] = useState<StoredInvestigation[]>([]);
  const [saved, setSaved] = useState<StoredInvestigation[]>([]);

  useEffect(() => {
    setRecent(load(`${RECENT_KEY}${scope}`));
    setSaved(load(`${SAVED_KEY}${scope}`));
  }, [scope]);

  /** Record an investigation as recently touched (deduplicated, capped). */
  const trackRecent = useCallback((item: StoredInvestigation) => {
    setRecent((prev) => {
      const next = prev.filter((r) => !(r.type === item.type && r.id === item.id));
      next.unshift({ ...item, ts: Date.now() });
      const trimmed = next.slice(0, RECENT_CAP);
      save(`${RECENT_KEY}${scope}`, trimmed);
      return trimmed;
    });
  }, [scope]);

  const removeRecent = useCallback((item: StoredInvestigation) => {
    setRecent((prev) => {
      const next = prev.filter((r) => !(r.type === item.type && r.id === item.id));
      save(`${RECENT_KEY}${scope}`, next);
      return next;
    });
  }, [scope]);

  const clearRecent = useCallback(() => {
    setRecent([]);
    save(`${RECENT_KEY}${scope}`, []);
  }, [scope]);

  const isSaved = useCallback((item: StoredInvestigation) => {
    return saved.some((s) => s.type === item.type && s.id === item.id);
  }, [saved]);

  const toggleSaved = useCallback((item: StoredInvestigation) => {
    setSaved((prev) => {
      const exists = prev.some((s) => s.type === item.type && s.id === item.id);
      const next = exists
        ? prev.filter((s) => !(s.type === item.type && s.id === item.id))
        : [{ ...item, ts: Date.now() }, ...prev];
      save(`${SAVED_KEY}${scope}`, next);
      return next;
    });
  }, [scope]);

  const renameSaved = useCallback((type: string, id: string, label: string) => {
    setSaved((prev) => {
      const next = prev.map((s) => (s.type === type && s.id === id ? { ...s, label } : s));
      save(`${SAVED_KEY}${scope}`, next);
      return next;
    });
  }, [scope]);

  const removeSaved = useCallback((item: StoredInvestigation) => {
    setSaved((prev) => {
      const next = prev.filter((s) => !(s.type === item.type && s.id === item.id));
      save(`${SAVED_KEY}${scope}`, next);
      return next;
    });
  }, [scope]);

  return {
    recent,
    saved,
    trackRecent,
    removeRecent,
    clearRecent,
    isSaved,
    toggleSaved,
    renameSaved,
    removeSaved,
  };
}
