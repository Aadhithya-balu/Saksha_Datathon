import React, { useEffect, useState } from 'react';
import { Database, Shield, FlaskConical, AlertTriangle, Info } from 'lucide-react';
import { getSystemDataMode, type SystemDataModeResponse } from '../../services/api';

/**
 * Global data-mode indicator (Issue #190 §3, §5).
 *
 * Fetches the runtime data mode from `/api/v2/system/data-mode` and renders a
 * compact chip so operators can always tell whether the platform is running in
 * PRODUCTION, DEMO, or TEST mode — and whether demo/seed fallback is permitted.
 *
 * - PRODUCTION : no silent fallback; seed/demo data is never presented as live.
 * - DEMO       : fallback permitted; clearly labelled.
 * - TEST       : test fixtures; no fallback.
 */
type Mode = SystemDataModeResponse['mode'];

const MODE_META: Record<Mode, { label: string; tone: string; icon: React.ReactNode; tooltip: string }> = {
  production: {
    label: 'PRODUCTION',
    tone: 'bg-[#0E9E78]/15 border-[#0E9E78]/40 text-[#0E9E78]',
    icon: <Shield className="w-3 h-3 shrink-0" aria-hidden="true" />,
    tooltip: 'Production mode — no silent fallback to demo/seed data. Errors are reported honestly.',
  },
  demo: {
    label: 'DEMO',
    tone: 'bg-amber-500/15 border-amber-500/40 text-amber-400',
    icon: <Database className="w-3 h-3 shrink-0" aria-hidden="true" />,
    tooltip: 'Demo mode — demo/seed data may be used as a fallback and is clearly labelled.',
  },
  test: {
    label: 'TEST',
    tone: 'bg-blue-500/10 border-blue-500/30 text-blue-300',
    icon: <FlaskConical className="w-3 h-3 shrink-0" aria-hidden="true" />,
    tooltip: 'Test mode — test fixtures; fallback is disabled.',
  },
};

interface DataModeBadgeProps {
  className?: string;
}

export const DataModeBadge: React.FC<DataModeBadgeProps> = ({ className = '' }) => {
  const [mode, setMode] = useState<Mode | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    getSystemDataMode()
      .then((res) => {
        if (active) setMode(res.mode);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return (
      <span
        title="Could not determine data mode. Demo/fallback state is unverified."
        role="status"
        aria-label="Data mode unavailable"
        className={`inline-flex items-center gap-1 px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider rounded-md border border-red-500/40 bg-red-500/10 text-red-400 cursor-help ${className}`}
      >
        <AlertTriangle className="w-3 h-3 shrink-0" aria-hidden="true" />
        MODE ?
      </span>
    );
  }

  if (!mode) {
    return null;
  }

  const meta = MODE_META[mode];

  return (
    <span
      title={meta.tooltip}
      role="status"
      aria-label={`${meta.label}: ${meta.tooltip}`}
      className={`inline-flex items-center gap-1 px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider rounded-md border cursor-help ${meta.tone} ${className}`}
    >
      {meta.icon}
      {meta.label}
      <Info className="w-2.5 h-2.5 shrink-0 opacity-70" aria-hidden="true" />
    </span>
  );
};

export default DataModeBadge;
