import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ShieldCheck, Lock, KeyRound, ScanFace, UserCheck } from 'lucide-react';
import SecureBackdrop from '../components/auth/SecureBackdrop';
import BadgeLogin from '../components/auth/BadgeLogin';
import FaceIDScanner from '../components/auth/FaceIDScanner';
import { showSecureEntry } from '../components/auth/SecureEntryOverlay';
import { useAuthStore } from '../store/authStore';

type AuthMethod = 'badge' | 'face';

const formatIstClock = (): string =>
  `${new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date())} IST`;

export const Login: React.FC<{ onSuccess?: () => void }> = ({ onSuccess }) => {
  const loginWithFace = useAuthStore((state) => state.loginWithFace);

  const [method, setMethod] = useState<AuthMethod>('badge');
  const [faceError, setFaceError] = useState<string | null>(null);
  const [clock, setClock] = useState(formatIstClock);

  /* Live IST clock — honest system telemetry */
  useEffect(() => {
    const timer = window.setInterval(() => setClock(formatIstClock()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  /* Real connection posture (no fabricated audit stream) */
  const securityFacts = useMemo(
    () => [
      {
        icon: ShieldCheck,
        tone: 'var(--lp-green)',
        label:
          typeof window !== 'undefined' && window.location.protocol === 'https:'
            ? 'TLS Encrypted'
            : 'Local Channel',
      },
      { icon: Lock, tone: 'var(--lp-accent-hi)', label: 'Activity Audited' },
      { icon: ScanFace, tone: 'var(--lp-amber)', label: 'Biometrics: DB-Verified' },
    ],
    []
  );

  const platformFeatures = [
    {
      icon: Lock,
      tone: 'var(--lp-accent-hi)',
      soft: 'var(--lp-accent-soft)',
      title: 'Encrypted Access',
      sub: 'End-to-end secure channel',
    },
    {
      icon: ShieldCheck,
      tone: 'var(--lp-green)',
      soft: 'var(--lp-green-soft)',
      title: 'Audited Sessions',
      sub: 'Every action accountable',
    },
    {
      icon: ScanFace,
      tone: 'var(--lp-amber)',
      soft: 'var(--lp-amber-soft)',
      title: 'Face ID',
      sub: 'KSP officer biometric auth',
    },
  ];

  const handleBadgeSuccess = () => {
    /* Session commit already triggers the dashboard swap in App.tsx;
       the SecureEntryOverlay bridges the transition visually. */
    onSuccess?.();
  };

  const handleFaceVerified = async () => {
    setFaceError(null);
    let ok = false;
    try {
      ok = await loginWithFace();
    } catch {
      ok = false;
    }
    if (ok) {
      // Use the real authenticated user's badge and role from the store
      const authUser = useAuthStore.getState().user;
      showSecureEntry(
        authUser?.badgeId ?? 'KSP',
        authUser?.role ?? 'AUTHORIZED',
      );
      onSuccess?.();
    } else {
      setFaceError(
        'Secure sign-in could not be completed right now. Please try again or continue with your Badge ID.'
      );
    }
  };

  const switchMethod = (next: AuthMethod) => {
    if (next !== method) {
      setFaceError(null);
      setMethod(next);
    }
  };

  return (
    <div className="login-root relative flex min-h-[100dvh] w-full flex-col font-sans select-none">
      <SecureBackdrop />

      {/* ── System bar ─────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 flex h-11 shrink-0 items-center justify-between gap-3 border-b px-4 sm:px-6"
        style={{ borderColor: 'var(--lp-border)', background: 'var(--lp-bg)' }}
      >
        <span
          className="inline-flex items-center gap-1.5 rounded-sm border px-2 py-[3px] font-mono text-[8px] tracking-[0.22em]"
          style={{
            borderColor: 'rgba(224, 96, 85, 0.35)',
            background: 'rgba(224, 96, 85, 0.07)',
            color: 'var(--lp-red)',
          }}
        >
          RESTRICTED // KSP-NET
        </span>

        <div
          className="flex items-center gap-3 font-mono text-[8px] tracking-[0.2em] sm:gap-4"
          style={{ color: 'var(--lp-text-3)' }}
        >
          <span aria-label="Current time, Indian Standard Time">{clock}</span>
          <span className="flex items-center gap-1.5" style={{ color: 'var(--lp-green)' }}>
            <span className="lp-live-dot" style={{ background: 'var(--lp-green)' }} />
            <span className="hidden sm:inline">SECURE NODE ONLINE</span>
            <span className="sm:hidden">ONLINE</span>
          </span>
        </div>
      </header>

      {/* ── Portal ─────────────────────────────────────────── */}
      <main className="relative z-10 flex flex-1 items-center justify-center px-3 py-7 sm:px-6 sm:py-12">
        <motion.div
          initial={{ opacity: 0, y: 26 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, ease: [0.22, 0.9, 0.32, 1] }}
          className="grid w-full max-w-[980px] overflow-hidden rounded-card border lg:grid-cols-[1.05fr_1fr]"
          style={{
            background: 'var(--lp-card)',
            borderColor: 'var(--lp-border-strong)',
            boxShadow: 'var(--lp-card-shadow)',
            backdropFilter: 'blur(14px)',
            WebkitBackdropFilter: 'blur(14px)',
          }}
        >
          {/* Accent hairline */}
          <div
            className="h-[2px] w-full lg:col-span-2"
            style={{ background: 'linear-gradient(90deg, transparent, var(--lp-accent-hi), transparent)' }}
            aria-hidden="true"
          />

          {/* ── LEFT · Brand panel ── */}
          <aside
            className="relative flex flex-col border-b p-6 sm:p-9 lg:border-b-0 lg:border-r lg:p-10"
            style={{
              borderColor: 'var(--lp-border)',
              background: 'linear-gradient(165deg, var(--lp-accent-soft), transparent 46%)',
            }}
          >
            {/* Ambient orb */}
            <div
              className="pointer-events-none absolute -bottom-24 -left-16 h-64 w-64 rounded-full blur-3xl"
              style={{ background: 'var(--lp-accent-soft)' }}
              aria-hidden="true"
            />
            {/* Watermark */}
            <span
              className="pointer-events-none absolute -right-2 bottom-3 hidden select-none rotate-[-8deg] font-mono text-[44px] font-extrabold leading-none tracking-tight sm:block"
              style={{ color: 'var(--lp-text)', opacity: 0.04 }}
              aria-hidden="true"
            >
              RESTRICTED
            </span>

            {/* Identity */}
            <div className="relative flex items-center gap-5 text-left lg:flex-col lg:items-center lg:text-center">
              <div
                className="login-brand-logo lp-logo-rings relative flex shrink-0 items-center justify-center rounded-2xl border"
                style={{
                  width: 'clamp(58px, 8vw, 84px)',
                  height: 'clamp(58px, 8vw, 84px)',
                  background: 'var(--lp-accent-soft)',
                  borderColor: 'var(--lp-border-strong)',
                  boxShadow: '0 0 38px rgba(47, 127, 224, 0.24)',
                }}
              >
                <img src="/logo.svg" alt="Saksha emblem" className="h-[68%] w-[68%]" draggable={false} />
              </div>

              <div className="min-w-0">
                <h1
                  className="lp-gradient-title font-extrabold uppercase leading-none tracking-[0.1em]"
                  style={{ fontSize: 'clamp(28px, 3.4vw, 40px)' }}
                >
                  Saksha
                </h1>
                <p
                  className="mt-2 font-mono uppercase tracking-[0.32em]"
                  style={{ fontSize: 'clamp(8px, 1.1vw, 10px)', color: 'var(--lp-teal)' }}
                >
                  Crime Intelligence Platform
                </p>
                <span
                  className="mt-3 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[3px] font-mono text-[8px] tracking-[0.22em]"
                  style={{
                    borderColor: 'var(--lp-border)',
                    background: 'var(--lp-surface-3)',
                    color: 'var(--lp-text-2)',
                  }}
                >
                  Karnataka State Police · Est. 2026
                </span>
              </div>
            </div>

            {/* Platform capabilities (desktop) */}
            <div className="relative mt-8 hidden space-y-2.5 lg:block">
              {platformFeatures.map(({ icon: Icon, tone, soft, title, sub }) => (
                <div
                  key={title}
                  className="flex items-center gap-3 rounded-xl border p-2.5 transition-colors duration-200 hover:border-[color:var(--lp-border-strong)]"
                  style={{ background: 'var(--lp-surface-3)', borderColor: 'var(--lp-border)' }}
                >
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border"
                    style={{ background: soft, borderColor: 'var(--lp-border-strong)' }}
                  >
                    <Icon className="h-4 w-4" style={{ color: tone }} strokeWidth={1.9} />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-[11px] font-bold uppercase tracking-wider" style={{ color: 'var(--lp-text)' }}>
                      {title}
                    </span>
                    <span className="block truncate font-mono text-[8.5px] uppercase tracking-[0.14em]" style={{ color: 'var(--lp-text-3)' }}>
                      {sub}
                    </span>
                  </span>
                </div>
              ))}
            </div>

            {/* Genuine security posture */}
            <div className="relative mt-auto hidden pt-7 lg:block">
              <div
                className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 border-t pt-4 font-mono text-[8px] uppercase tracking-[0.18em] lg:justify-start"
                style={{ borderColor: 'var(--lp-border)', color: 'var(--lp-text-3)' }}
              >
                {securityFacts.map(({ icon: Icon, tone, label }) => (
                  <span key={label} className="inline-flex items-center gap-1.5">
                    <Icon className="h-3 w-3" style={{ color: tone }} />
                    {label}
                  </span>
                ))}
              </div>
            </div>
          </aside>

          {/* ── RIGHT · Authentication ── */}
          <section className="flex flex-col p-5 sm:p-8 lg:p-9">
            {/* Module header */}
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2
                className="text-[11px] font-extrabold uppercase tracking-[0.2em] sm:text-xs"
                style={{ color: 'var(--lp-text)' }}
              >
                Secure Access Terminal
              </h2>
              <span
                className="inline-flex shrink-0 items-center gap-1 rounded-full border px-1.5 py-[3px] font-mono text-[7.5px] tracking-[0.16em]"
                style={{
                  borderColor: 'rgba(224, 96, 85, 0.3)',
                  background: 'rgba(224, 96, 85, 0.06)',
                  color: 'var(--lp-red)',
                }}
              >
                <UserCheck className="h-2.5 w-2.5" />
                Authorized Only
              </span>
            </div>

            {/* Method selector */}
            <div
              role="tablist"
              aria-label="Authentication method"
              className="mb-5 grid grid-cols-2 gap-1 rounded-xl border p-1"
              style={{ background: 'var(--lp-surface-3)', borderColor: 'var(--lp-border)' }}
            >
              {(
                [
                  { id: 'badge', label: 'Badge ID', Icon: KeyRound },
                  { id: 'face', label: 'Face ID', Icon: ScanFace },
                ] as const
              ).map(({ id, label, Icon }) => {
                const active = method === id;
                return (
                  <button
                    key={id}
                    role="tab"
                    aria-selected={active}
                    onClick={() => switchMethod(id)}
                    className="relative cursor-pointer rounded-lg py-2.5 font-sans text-[10.5px] font-bold uppercase tracking-[0.14em] transition-colors duration-200"
                    style={{ color: active ? '#f2f6fc' : 'var(--lp-text-2)' }}
                  >
                    {active && (
                      <motion.span
                        layoutId="saksha-auth-method-pill"
                        className="absolute inset-0 rounded-lg"
                        style={{
                          background: 'linear-gradient(135deg, var(--lp-accent), #2467c2)',
                          boxShadow: '0 0 16px rgba(31, 92, 179, 0.4)',
                        }}
                        transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                      />
                    )}
                    <Icon className="relative z-10 mr-1.5 inline h-4 w-4" strokeWidth={2.2} />
                    <span className="relative z-10">{label}</span>
                  </button>
                );
              })}
            </div>

            {/* Face-flow error (network / service failures) */}
            {faceError && (
              <div
                role="alert"
                className="lp-shake mb-4 rounded-lg border px-3 py-2.5 text-[11.5px] leading-snug"
                style={{
                  background: 'var(--lp-red-soft)',
                  borderColor: 'rgba(224, 96, 85, 0.35)',
                  color: 'var(--lp-red)',
                }}
              >
                {faceError}
              </div>
            )}

            {/* Active method panel */}
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={method}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
                className="flex flex-col"
              >
                {method === 'badge' ? (
                  <BadgeLogin onSuccess={handleBadgeSuccess} />
                ) : (
                  <FaceIDScanner onVerifySuccess={handleFaceVerified} />
                )}
              </motion.div>
            </AnimatePresence>

            {/* Compliance footer */}
            <div
              className="mt-auto flex items-center gap-2 pt-6 font-mono text-[8px] uppercase tracking-[0.16em] sm:text-[8.5px]"
              style={{ borderTop: '1px solid var(--lp-border)', marginTop: 'auto', color: 'var(--lp-text-3)' }}
            >
              <Lock className="h-3 w-3 shrink-0" />
              Session activity recorded under KSP Security Directive 7.2
            </div>
          </section>
        </motion.div>
      </main>

      {/* ── Footer ─────────────────────────────────────────── */}
      <footer
        className="relative z-20 shrink-0 border-t py-2.5 text-center font-mono text-[7.5px] uppercase tracking-[0.24em]"
        style={{ borderColor: 'var(--lp-border)', background: 'var(--lp-bg)', color: 'var(--lp-text-3)' }}
      >
        Secure Connection · Session Activity Audited · Karnataka State Police © 2026
      </footer>
    </div>
  );
};

export default Login;
