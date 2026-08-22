import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ShieldCheck, Loader2, Lock } from 'lucide-react';

/**
 * SecureEntryOverlay — post-authentication handoff transition.
 *
 * Rendered imperatively on document.body so it survives the
 * Login → Dashboard swap that happens the moment the session
 * is committed in the auth store. Plays a short, professional
 * sequence: IDENTITY VERIFIED → SECURE SESSION INITIALIZING,
 * then removes itself to reveal the platform underneath.
 */

type EntryPhase = 'verified' | 'initializing' | 'leaving';

const CLEARANCE_LABELS: Record<string, string> = {
  ADMIN: 'SYSTEM ADMINISTRATOR',
  SP: 'SUPERINTENDENT OF POLICE',
  INSPECTOR: 'POLICE INSPECTOR',
  IO: 'INVESTIGATION OFFICER',
  SCRB: 'INTELLIGENCE ANALYST · SCRB',
  FORENSIC: 'FORENSIC SERVICES',
  VIEWER: 'OBSERVER ACCESS',
};

interface EntryOverlayProps {
  badgeId: string;
  clearance: string;
  reduced: boolean;
}

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

export const showSecureEntry = (badgeId: string, clearance?: string): void => {
  if (document.getElementById('saksha-entry-overlay')) return;

  const host = document.createElement('div');
  host.id = 'saksha-entry-overlay';
  document.body.appendChild(host);

  const root = createRoot(host);
  const cleanup = () => {
    root.unmount();
    host.remove();
  };

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  root.render(
    <React.StrictMode>
      <EntryOverlay badgeId={badgeId} clearance={clearance || 'AUTHORIZED'} reduced={reduced} />
    </React.StrictMode>
  );

  // Safety net — never leave the overlay stranded.
  window.setTimeout(() => {
    if (document.getElementById('saksha-entry-overlay')) cleanup();
  }, 6000);
};

export default showSecureEntry;
