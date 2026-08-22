import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  ShieldCheck,
  Delete,
  Loader2,
  AlertCircle,
  UserRound,
  BadgeCheck,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { showSecureEntry } from './SecureEntryOverlay';

interface BadgeLoginProps {
  onSuccess: () => void;
}

type AuthStatus = 'idle' | 'verifying' | 'granted' | 'initializing';

interface DemoProfile {
  badge: string;
  pin: string;
  title: string;
  rank: string;
  initials: string;
  tone: 'blue' | 'teal' | 'amber' | 'green';
}

/* Development/demo access profiles — clearly labelled as demo data. */
const DEMO_PROFILES: DemoProfile[] = [
  { badge: 'admin', pin: '564738', title: 'Administrator', rank: 'System Administration', initials: 'AD', tone: 'blue' },
  { badge: 'SP-0088', pin: '987654', title: 'Superintendent', rank: 'District Command · SP', initials: 'SP', tone: 'amber' },
  { badge: 'IO-3921', pin: '456789', title: 'Investigator', rank: 'Investigation Officer · DSP', initials: 'IO', tone: 'green' },
  { badge: 'SCRB-7740', pin: '123456', title: 'Analyst', rank: 'Intelligence Analyst · SCRB', initials: 'AN', tone: 'teal' },
];

const TONE_STYLES: Record<DemoProfile['tone'], { color: string; bg: string; border: string }> = {
  blue: { color: 'var(--lp-accent-hi)', bg: 'var(--lp-accent-soft)', border: 'var(--lp-border-strong)' },
  teal: { color: 'var(--lp-teal)', bg: 'rgba(58, 194, 164, 0.1)', border: 'rgba(58, 194, 164, 0.3)' },
  amber: { color: 'var(--lp-amber)', bg: 'var(--lp-amber-soft)', border: 'rgba(223, 162, 63, 0.3)' },
  green: { color: 'var(--lp-green)', bg: 'var(--lp-green-soft)', border: 'rgba(55, 201, 142, 0.3)' },
};

const CLEARANCE_LABELS: Record<string, string> = {
  ADMIN: 'SYSTEM ADMINISTRATOR',
  SP: 'SUPERINTENDENT OF POLICE',
  INSPECTOR: 'POLICE INSPECTOR',
  IO: 'INVESTIGATION OFFICER',
  SCRB: 'INTELLIGENCE ANALYST',
  FORENSIC: 'FORENSIC SERVICES',
  VIEWER: 'OBSERVER ACCESS',
};

/** Translate raw backend/store failures into calm, human language. */
const sanitizeAuthError = (raw: string | null): string => {
  const msg = (raw || '').toLowerCase();
  if (!msg) return 'Authentication failed. Please try again.';
  if (
    msg.includes('temporarily unavailable') ||
    msg.includes('offline') ||
    msg.includes('failed to fetch') ||
    msg.includes('networkerror') ||
    msg.includes('load failed') ||
    msg.includes('aborted')
  ) {
    return 'The secure authentication service is temporarily unavailable. Please try again shortly.';
  }
  if (msg.includes('session expired')) {
    return 'Your session could not be restored. Please authenticate again.';
  }
  return 'Badge ID or PIN was not recognized. Verify your credentials and try again.';
};

export const BadgeLogin: React.FC<BadgeLoginProps> = ({ onSuccess }) => {
  const login = useAuthStore((state) => state.login);

  const [badgeId, setBadgeId] = useState('');
  const [pin, setPin] = useState('');
  const [status, setStatus] = useState<AuthStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [pinFocused, setPinFocused] = useState(false);
  const [activeProfile, setActiveProfile] = useState<number | null>(null);

  const pinInputRef = useRef<HTMLInputElement>(null);
  const badgeInputRef = useRef<HTMLInputElement>(null);
  const statusRef = useRef<AuthStatus>('idle');
  statusRef.current = status;

  /* Role hint while typing a badge id */
  const detectedRole = (() => {
    const uc = badgeId.toUpperCase().trim();
    if (uc.startsWith('SCRB')) return 'SCRB';
    if (uc.startsWith('IO')) return 'IO';
    if (uc.startsWith('SP')) return 'SP';
    return null;
  })();

  const submit = useCallback(async () => {
    if (statusRef.current !== 'idle') return;

    const cleanBadge = badgeId.trim();
    if (!cleanBadge) {
      setError('Enter your authorized Badge ID to continue.');
      badgeInputRef.current?.focus();
      return;
    }
    if (pin.length < 6) {
      setError('Enter the complete 6-digit authentication PIN.');
      pinInputRef.current?.focus();
      return;
    }

    setError(null);
    setStatus('verifying');

    let ok = false;
    try {
      ok = await login(cleanBadge, pin);
    } catch {
      ok = false;
    }

    if (ok) {
      setStatus('granted');
      const user = useAuthStore.getState().user;
      window.setTimeout(() => {
        setStatus('initializing');
        showSecureEntry(
          user?.badgeId || cleanBadge,
          CLEARANCE_LABELS[user?.role || ''] || 'AUTHORIZED'
        );
      }, 550);
      window.setTimeout(() => onSuccess(), 1150);
    } else {
      setStatus('idle');
      setPin('');
      setError(sanitizeAuthError(useAuthStore.getState().loginError));
      pinInputRef.current?.focus();
    }
  }, [badgeId, pin, login, onSuccess]);

  /* Preserve legacy behaviour: authenticate automatically once 6 digits are entered. */
  useEffect(() => {
    if (pin.length === 6 && status === 'idle') {
      void submit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pin]);

  useEffect(() => {
    badgeInputRef.current?.focus();
  }, []);

  const handlePinInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const digits = e.target.value.replace(/\D/g, '').slice(0, 6);
    setPin(digits);
    if (error && digits.length > 0 && digits.length < 6) setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      void submit();
    }
  };

  const pressDigit = useCallback((digit: number) => {
    if (statusRef.current !== 'idle') return;
    setPin((prev) => (prev.length < 6 ? prev + String(digit) : prev));
    setError(null);
  }, []);

  const backspace = useCallback(() => {
    if (statusRef.current !== 'idle') return;
    setPin((prev) => prev.slice(0, -1));
  }, []);

  const clearPin = useCallback(() => {
    if (statusRef.current !== 'idle') return;
    setPin('');
    pinInputRef.current?.focus();
  }, []);

  const useProfile = (profile: DemoProfile, index: number) => {
    if (statusRef.current !== 'idle') return;
    setBadgeId(profile.badge);
    setPin('');
    setError(null);
    setActiveProfile(index);
    window.setTimeout(() => setPin(profile.pin), 120);
    window.setTimeout(() => setActiveProfile(null), 1400);
    pinInputRef.current?.focus();
  };

  const busy = status !== 'idle';

  return (
    <form className="flex w-full flex-col gap-4 text-left" onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      {/* Live region for validation / auth errors */}
      <div aria-live="polite" className="flex min-h-[18px] items-start">
        {error && (
          <div
            className="lp-shake flex w-full items-start gap-2 rounded-lg border px-3 py-2 text-[11.5px] leading-snug"
            style={{
              background: 'var(--lp-red-soft)',
              borderColor: 'rgba(224, 96, 85, 0.35)',
              color: 'var(--lp-red)',
            }}
          >
            <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Police Badge ID */}
      <div>
        <label
          htmlFor="saksha-badge-id"
          className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--lp-text-3)' }}
        >
          Police Badge ID
        </label>
        <div className="group relative">
          <ShieldCheck
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 transition-colors duration-200"
            style={{ color: 'var(--lp-text-3)' }}
          />
          <input
            ref={badgeInputRef}
            id="saksha-badge-id"
            type="text"
            autoComplete="username"
            spellCheck={false}
            placeholder="Enter authorized badge ID"
            value={badgeId}
            disabled={busy}
            onChange={(e) => {
              setBadgeId(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                pinInputRef.current?.focus();
              }
            }}
            className="lp-input h-11 rounded-lg pl-10 pr-24 font-mono text-sm"
          />
          {detectedRole && !busy && (
            <span
              className="absolute right-3 top-1/2 flex -translate-y-1/2 select-none items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[9px] font-bold tracking-wider"
              style={{
                color: 'var(--lp-accent-hi)',
                borderColor: 'var(--lp-border-strong)',
                background: 'var(--lp-accent-soft)',
              }}
            >
              <UserRound className="h-2.5 w-2.5" />
              {detectedRole}
            </span>
          )}
        </div>
      </div>

      {/* 6-Digit PIN — individual secure cells */}
      <div>
        <div className="mb-2 flex items-baseline justify-between">
          <label
            htmlFor="saksha-pin-input"
            className="text-[10px] font-semibold uppercase tracking-[0.14em]"
            style={{ color: 'var(--lp-text-3)' }}
          >
            Authentication PIN
          </label>
          <span className="font-mono text-[9px] tracking-wider" style={{ color: 'var(--lp-text-3)' }}>
            {pin.length}/6
          </span>
        </div>

        <div
          className="relative cursor-text"
          onClick={() => pinInputRef.current?.focus()}
          role="group"
          aria-label="6-digit authentication PIN entry"
        >
          {/* Real input captures keyboard, paste and mobile keypads */}
          <input
            ref={pinInputRef}
            id="saksha-pin-input"
            type="password"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={pin}
            disabled={busy}
            onChange={handlePinInput}
            onKeyDown={handleKeyDown}
            onFocus={() => setPinFocused(true)}
            onBlur={() => setPinFocused(false)}
            className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
            tabIndex={0}
          />
          <div className="pointer-events-none flex gap-2" aria-hidden="true">
            {Array.from({ length: 6 }).map((_, i) => {
              const filled = i < pin.length;
              const active = i === pin.length && pinFocused && !busy;
              return (
                <div
                  key={i}
                  className="h-12 flex-1 rounded-xl border transition-all duration-150"
                  style={{
                    background: active ? 'var(--lp-field-focus)' : 'var(--lp-field)',
                    borderColor: filled || active ? 'var(--lp-accent-hi)' : 'var(--lp-border)',
                    boxShadow:
                      filled
                        ? '0 0 12px rgba(47, 127, 224, 0.14)'
                        : active
                          ? '0 0 0 3px var(--lp-accent-soft)'
                          : 'inset 0 1px 0 var(--lp-inner-hi)',
                  }}
                >
                  {filled && (
                    <span
                      className="mx-auto mt-[21px] block h-2 w-2 rounded-full"
                      style={{ background: 'var(--lp-accent-hi)', boxShadow: '0 0 8px rgba(47, 127, 224, 0.5)' }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Secure numeric keypad */}
      <div
        role="group"
        aria-label="PIN keypad"
        className="grid grid-cols-3 gap-2 rounded-xl border p-2.5"
        style={{ background: 'var(--lp-surface-3)', borderColor: 'var(--lp-border)' }}
      >
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
          <button
            key={num}
            type="button"
            aria-label={`Digit ${num}`}
            disabled={busy}
            onClick={() => pressDigit(num)}
            className="lp-key h-11 cursor-pointer rounded-lg font-sans text-sm font-semibold"
          >
            {num}
          </button>
        ))}

        <button
          type="button"
          aria-label="Clear PIN"
          disabled={busy || pin.length === 0}
          onClick={clearPin}
          className="lp-key h-11 cursor-pointer rounded-lg font-sans text-[10px] font-bold uppercase tracking-widest hover:!bg-[color:var(--lp-red-soft)]"
          style={{ color: 'var(--lp-red)' }}
        >
          Clear
        </button>

        <button
          type="button"
          aria-label="Digit 0"
          disabled={busy}
          onClick={() => pressDigit(0)}
          className="lp-key h-11 cursor-pointer rounded-lg font-sans text-sm font-semibold"
        >
          0
        </button>

        <button
          type="button"
          aria-label="Delete last digit"
          disabled={busy || pin.length === 0}
          onClick={backspace}
          className="lp-key flex h-11 cursor-pointer items-center justify-center rounded-lg"
          style={{ color: 'var(--lp-text-2)' }}
        >
          <Delete className="h-4 w-4" />
        </button>
      </div>

      {/* Primary gateway action */}
      <button
        type="submit"
        disabled={busy || !badgeId.trim() || pin.length < 6}
        className="lp-primary-btn relative h-12 w-full cursor-pointer rounded-xl font-sans text-xs font-bold uppercase tracking-[0.18em] transition-all duration-200"
        style={
          status === 'granted'
            ? {
                background: 'linear-gradient(135deg, rgba(55,201,142,0.22), rgba(55,201,142,0.1))',
                border: '1px solid rgba(55,201,142,0.5)',
                color: 'var(--lp-green)',
              }
            : {
                background: 'linear-gradient(135deg, var(--lp-accent), #2467c2)',
                border: '1px solid transparent',
                color: '#f2f6fc',
                opacity: !badgeId.trim() || pin.length < 6 ? 0.45 : 1,
                boxShadow: busy ? 'none' : '0 8px 24px rgba(31, 92, 179, 0.32)',
              }
        }
      >
        <span className="flex items-center justify-center gap-2">
          {status === 'idle' && (
            <>
              <BadgeCheck className="h-4 w-4" strokeWidth={2} />
              Authenticate &amp; Enter
            </>
          )}
          {status === 'verifying' && (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Verifying Credentials…
            </>
          )}
          {status === 'granted' && (
            <>
              <ShieldCheck className="h-4 w-4" />
              Identity Verified
            </>
          )}
          {status === 'initializing' && (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Secure Session Initializing…
            </>
          )}
        </span>
      </button>

      {/* Authorized access profiles (demo environment only) */}
      <div className="bl-profiles pt-1">
        <div className="mb-2.5 flex items-center gap-2.5">
          <span className="text-[9px] font-semibold uppercase tracking-[0.18em]" style={{ color: 'var(--lp-text-3)' }}>
            Access Profiles
          </span>
          <span
            className="rounded px-1.5 py-px font-mono text-[8px] font-bold tracking-widest"
            style={{
              color: 'var(--lp-amber)',
              background: 'var(--lp-amber-soft)',
              border: '1px solid rgba(223, 162, 63, 0.25)',
            }}
          >
            DEMO
          </span>
          <div className="h-px flex-1" style={{ background: 'var(--lp-border)' }} />
        </div>

        <div className="grid grid-cols-4 gap-2">
          {DEMO_PROFILES.map((profile, index) => {
            const tone = TONE_STYLES[profile.tone];
            const selected = activeProfile === index;
            return (
              <button
                key={profile.badge}
                type="button"
                disabled={busy}
                onClick={() => useProfile(profile, index)}
                aria-label={`Use demo profile ${profile.title}, ${profile.badge} — ${profile.rank}`}
                title={`${profile.title} · ${profile.rank}`}
                className="flex min-w-0 cursor-pointer flex-col items-center gap-1.5 rounded-xl border px-1 py-2 transition-all duration-150 hover:-translate-y-px hover:border-[color:var(--lp-border-strong)] hover:bg-[color:var(--lp-accent-soft)] disabled:cursor-not-allowed disabled:opacity-40"
                style={{
                  background: selected ? 'var(--lp-accent-soft)' : 'var(--lp-field)',
                  borderColor: selected ? 'var(--lp-accent-hi)' : 'var(--lp-border)',
                }}
              >
                <span
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md font-mono text-[8px] font-bold"
                  style={{ background: tone.bg, color: tone.color, border: `1px solid ${tone.border}` }}
                >
                  {profile.initials}
                </span>
                <span
                  className="w-full truncate text-center font-mono text-[7.5px] leading-tight"
                  style={{ color: 'var(--lp-text-2)' }}
                >
                  {profile.badge}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </form>
  );
};

export default BadgeLogin;
