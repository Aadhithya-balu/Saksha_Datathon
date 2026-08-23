import React, { useEffect, useState } from 'react';
import { ShieldCheck, Loader2, Lock } from 'lucide-react';

type EntryPhase = 'verified' | 'initializing' | 'leaving';

interface EntryOverlayProps {
  badgeId: string;
  clearance: string;
  reduced: boolean;
}

/**
 * Post-authentication handoff transition card.
 * Rendered imperatively by `showSecureEntry` in SecureEntryOverlay.tsx.
 */
const EntryOverlay: React.FC<EntryOverlayProps> = ({ badgeId, clearance, reduced }) => {
  const [phase, setPhase] = useState<EntryPhase>('verified');

  useEffect(() => {
    const t1 = window.setTimeout(
      () => setPhase('initializing'),
      reduced ? 500 : 1250
    );
    const t2 = window.setTimeout(
      () => setPhase('leaving'),
      reduced ? 900 : 2050
    );
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [reduced]);

  return (
    <div
      className={`lp-entry-root ${phase === 'leaving' ? 'lp-entry-leave' : ''}`}
      role="status"
      aria-live="polite"
    >
      <div className="lp-entry-card">
        {phase === 'verified' ? (
          <ShieldCheck className="w-10 h-10" style={{ color: 'var(--lp-green)' }} strokeWidth={1.6} />
        ) : (
          <Loader2 className="w-7 h-7 animate-spin" style={{ color: 'var(--lp-accent-hi)' }} strokeWidth={1.8} />
        )}

        <p className="text-lg font-semibold tracking-wide text-[var(--lp-text)] font-sans">
          {phase === 'verified' ? 'Identity Verified' : 'Secure Session Initializing'}
        </p>

        <div className="w-full max-w-[240px] space-y-2 pt-4 border-t border-[var(--lp-border)]">
          <div className="flex items-center justify-between gap-6">
            <span className="text-[10px] uppercase tracking-[0.16em] text-[var(--lp-text-3)] font-sans">
              Badge
            </span>
            <span className="text-[11px] font-mono text-[var(--lp-text)]">{badgeId}</span>
          </div>
          <div className="flex items-center justify-between gap-6">
            <span className="text-[10px] uppercase tracking-[0.16em] text-[var(--lp-text-3)] font-sans">
              Clearance
            </span>
            <span className="text-[11px] font-mono flex items-center gap-1.5" style={{ color: 'var(--lp-green)' }}>
              <Lock className="w-3 h-3" />
              {clearance}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EntryOverlay;
