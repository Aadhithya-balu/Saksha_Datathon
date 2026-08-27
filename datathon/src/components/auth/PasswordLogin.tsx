import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  UserRound,
  KeyRound,
  Loader2,
  AlertCircle,
  LogIn,
  ShieldCheck,
  Eye,
  EyeOff,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { showSecureEntry } from './SecureEntryOverlay';

interface PasswordLoginProps {
  onSuccess: () => void;
}

type AuthStatus = 'idle' | 'verifying' | 'granted' | 'initializing';

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
  return 'Username or password was not recognized. Verify your credentials and try again.';
};

export const PasswordLogin: React.FC<PasswordLoginProps> = ({ onSuccess }) => {
  const login = useAuthStore((state) => state.login);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState<AuthStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const statusRef = useRef<AuthStatus>('idle');
  statusRef.current = status;

  const submit = useCallback(async () => {
    if (statusRef.current !== 'idle') return;

    const cleanUser = username.trim();
    if (!cleanUser) {
      setError('Enter the account username.');
      usernameRef.current?.focus();
      return;
    }
    if (!password) {
      setError('Enter the account password.');
      passwordRef.current?.focus();
      return;
    }

    setError(null);
    setStatus('verifying');

    let ok = false;
    try {
      ok = await login(cleanUser, password);
    } catch {
      ok = false;
    }

    if (ok) {
      setStatus('granted');
      const user = useAuthStore.getState().user;
      window.setTimeout(() => {
        setStatus('initializing');
        showSecureEntry(
          user?.badgeId || cleanUser,
          CLEARANCE_LABELS[user?.role || ''] || 'AUTHORIZED'
        );
      }, 550);
      window.setTimeout(() => onSuccess(), 1150);
    } else {
      setStatus('idle');
      setPassword('');
      setError(sanitizeAuthError(useAuthStore.getState().loginError));
      passwordRef.current?.focus();
    }
  }, [username, password, login, onSuccess]);

  useEffect(() => {
    usernameRef.current?.focus();
  }, []);

  const busy = status !== 'idle';

  return (
    <form
      className="flex w-full flex-col gap-4 text-left"
      onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}
    >
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

      {/* Account username */}
      <div>
        <label
          htmlFor="saksha-account-username"
          className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--lp-text-3)' }}
        >
          Account Username
        </label>
        <div className="group relative">
          <UserRound
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 transition-colors duration-200"
            style={{ color: 'var(--lp-text-3)' }}
          />
          <input
            ref={usernameRef}
            id="saksha-account-username"
            type="text"
            autoComplete="username"
            spellCheck={false}
            placeholder="Enter account username"
            value={username}
            disabled={busy}
            onChange={(e) => {
              setUsername(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                passwordRef.current?.focus();
              }
            }}
            className="lp-input h-11 rounded-lg pl-10 pr-3 font-mono text-sm"
          />
        </div>
      </div>

      {/* Password */}
      <div>
        <label
          htmlFor="saksha-account-password"
          className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--lp-text-3)' }}
        >
          Password
        </label>
        <div className="group relative">
          <KeyRound
            className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 transition-colors duration-200"
            style={{ color: 'var(--lp-text-3)' }}
          />
          <input
            ref={passwordRef}
            id="saksha-account-password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            spellCheck={false}
            placeholder="Enter account password"
            value={password}
            disabled={busy}
            onChange={(e) => {
              setPassword(e.target.value);
              if (error) setError(null);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                void submit();
              }
            }}
            className="lp-input h-11 rounded-lg pl-10 pr-11 font-mono text-sm"
          />
          <button
            type="button"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
            disabled={busy}
            onClick={() => setShowPassword((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer"
            style={{ color: 'var(--lp-text-3)' }}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        <p
          className="mt-1.5 flex items-start gap-1.5 font-mono text-[8.5px] uppercase tracking-[0.12em] leading-relaxed"
          style={{ color: 'var(--lp-text-3)' }}
        >
          <KeyRound className="mt-0.5 h-3 w-3 shrink-0" style={{ color: 'var(--lp-accent-hi)' }} />
          Format: 8+ characters with letters &amp; number — or a 6-digit numeric PIN
        </p>
      </div>

      {/* Primary gateway action */}
      <button
        type="submit"
        disabled={busy || !username.trim() || !password}
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
                opacity: !username.trim() || !password ? 0.45 : 1,
                boxShadow: busy ? 'none' : '0 8px 24px rgba(31, 92, 179, 0.32)',
              }
        }
      >
        <span className="flex items-center justify-center gap-2">
          {status === 'idle' && (
            <>
              <LogIn className="h-4 w-4" strokeWidth={2} />
              Sign In
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

      <p
        className="font-mono text-[8.5px] leading-relaxed uppercase tracking-[0.12em]"
        style={{ color: 'var(--lp-text-3)' }}
      >
        For accounts provisioned by an administrator, use the username and temporary
        password issued at creation. You can change it later from Settings.
      </p>
    </form>
  );
};

export default PasswordLogin;
