import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from '../i18n';
import { motion } from 'framer-motion';
import { ShieldCheck, Lock, UserCheck, BadgeCheck, KeyRound } from 'lucide-react';
import SecureBackdrop from '../components/auth/SecureBackdrop';
import BadgeLogin from '../components/auth/BadgeLogin';
import PasswordLogin from '../components/auth/PasswordLogin';

const formatIstClock = (): string =>
  `${new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date())} IST`;

export const Login: React.FC<{ onSuccess?: () => void }> = ({ onSuccess }) => {
  const t = useTranslation();
  const [clock, setClock] = useState(formatIstClock);
  const [method, setMethod] = useState<'badge' | 'password'>('badge');

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
  ];

  const handleBadgeSuccess = () => {
    onSuccess?.();
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
                  {t.login_subtitle}
                </p>
                <span
                  className="mt-3 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[3px] font-mono text-[8px] tracking-[0.22em]"
                  style={{
                    borderColor: 'var(--lp-border)',
                    background: 'var(--lp-surface-3)',
                    color: 'var(--lp-text-2)',
                  }}
                >
                  {t.footer_version}
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

            {/* Access method toggle */}
            <div
              className="mb-4 grid grid-cols-2 gap-1 rounded-xl border p-1 font-mono text-[9px] font-bold uppercase tracking-[0.14em]"
              style={{ borderColor: 'var(--lp-border)', background: 'var(--lp-surface-3)' }}
              role="tablist"
              aria-label="Sign-in method"
            >
              <button
                type="button"
                role="tab"
                aria-selected={method === 'badge'}
                onClick={() => setMethod('badge')}
                className="flex cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 py-2 transition-colors duration-150"
                style={
                  method === 'badge'
                    ? { background: 'var(--lp-accent-soft)', color: 'var(--lp-accent-hi)' }
                    : { color: 'var(--lp-text-3)' }
                }
              >
                <BadgeCheck className="h-3.5 w-3.5" />
                Badge ID
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={method === 'password'}
                onClick={() => setMethod('password')}
                className="flex cursor-pointer items-center justify-center gap-1.5 rounded-lg px-2 py-2 transition-colors duration-150"
                style={
                  method === 'password'
                    ? { background: 'var(--lp-accent-soft)', color: 'var(--lp-accent-hi)' }
                    : { color: 'var(--lp-text-3)' }
                }
              >
                <KeyRound className="h-3.5 w-3.5" />
                Username
              </button>
            </div>

            {/* Badge ID login */}
            <motion.div
              key={method}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="flex flex-col"
            >
              {method === 'badge' ? (
                <BadgeLogin onSuccess={handleBadgeSuccess} />
              ) : (
                <PasswordLogin onSuccess={handleBadgeSuccess} />
              )}
            </motion.div>

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
