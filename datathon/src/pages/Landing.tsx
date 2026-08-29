import React, { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  Lock,
  ArrowRight,
  BookOpen,
  Brain,
  Network,
  FileText,
  Map,
  Bell,
  AlertTriangle,
  Search,
  Fingerprint,
  Users,
  MessageSquare,
  Globe2,
  CheckCircle,
  ChevronDown,
  Crosshair,
  Activity,
} from 'lucide-react';
import SecureBackdrop from '../components/auth/SecureBackdrop';

const formatIstClock = (): string =>
  `${new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date())} IST`;

interface Feature {
  icon: React.ReactNode;
  title: string;
  desc: string;
  tone: string;
  soft: string;
}

const CAPABILITIES: Feature[] = [
  { icon: <Activity className="w-4 h-4" />, title: 'Real-Time Analytics', desc: 'Live district dashboards, trends, KPIs and 3D spatiotemporal intelligence.', tone: 'var(--lp-accent-hi)', soft: 'var(--lp-accent-soft)' },
  { icon: <Brain className="w-4 h-4" />, title: 'AI Predictions', desc: 'Hotspot forecasting, district risk scoring and recidivism models.', tone: 'var(--lp-amber)', soft: 'var(--lp-amber-soft)' },
  { icon: <Network className="w-4 h-4" />, title: 'Network Intelligence', desc: '3D graph analysis of criminal associations, gangs and shortest-path links.', tone: 'var(--lp-green)', soft: 'var(--lp-green-soft)' },
  { icon: <Search className="w-4 h-4" />, title: 'Investigation Suite', desc: 'End-to-end FIR to closure with AI recommendations and case dossiers.', tone: 'var(--lp-accent-hi)', soft: 'var(--lp-accent-soft)' },
  { icon: <Map className="w-4 h-4" />, title: 'Hotspot Mapping', desc: 'Interactive Karnataka heatmap with a time slider for spatial crime patterns.', tone: 'var(--lp-amber)', soft: 'var(--lp-amber-soft)' },
  { icon: <MessageSquare className="w-4 h-4" />, title: 'AI Copilot Chat', desc: 'Natural-language queries over case data with source citations (RAG).', tone: 'var(--lp-green)', soft: 'var(--lp-green-soft)' },
  { icon: <FileText className="w-4 h-4" />, title: 'Report Engine', desc: 'Generate and export PDF / DOCX / CSV intelligence and legal reports.', tone: 'var(--lp-accent-hi)', soft: 'var(--lp-accent-soft)' },
  { icon: <Bell className="w-4 h-4" />, title: 'Intelligence Alerts', desc: 'Real-time anomaly and critical incident notifications platform-wide.', tone: 'var(--lp-red)', soft: 'var(--lp-red-soft)' },
  { icon: <Fingerprint className="w-4 h-4" />, title: 'Face / Badge Auth', desc: 'Secure badge-ID, password and face-recognition sign-in workflows.', tone: 'var(--lp-green)', soft: 'var(--lp-green-soft)' },
];

const MODULES = [
  { icon: <Activity className="w-4 h-4" />, label: 'Analytics Dashboard', tone: 'var(--lp-teal)' },
  { icon: <Fingerprint className="w-4 h-4" />, label: 'Investigation Hub', tone: 'var(--lp-accent-hi)' },
  { icon: <FileText className="w-4 h-4" />, label: 'FIR Registry', tone: 'var(--lp-green)' },
  { icon: <Map className="w-4 h-4" />, label: 'Hotspot Map', tone: 'var(--lp-amber)' },
  { icon: <Network className="w-4 h-4" />, label: 'Network Graph', tone: 'var(--lp-purple, #7c5cd6)' },
  { icon: <Brain className="w-4 h-4" />, label: 'Predictive AI', tone: 'var(--lp-amber)' },
  { icon: <Users className="w-4 h-4" />, label: 'Offender Dossiers', tone: 'var(--lp-red)' },
  { icon: <Globe2 className="w-4 h-4" />, label: 'Socio Intelligence', tone: 'var(--lp-teal)' },
];

const ROLES = [
  { role: 'Admin', desc: 'Full system control, user & role management', tone: 'var(--lp-red)' },
  { role: 'Crime Analyst (SCRB)', desc: 'Dashboards, AI analytics and reports', tone: 'var(--lp-accent-hi)' },
  { role: 'Investigator (IO)', desc: 'Case, FIR, criminal & evidence workflow', tone: 'var(--lp-green)' },
  { role: 'Inspector', desc: 'Investigator + officer management', tone: 'var(--lp-purple, #7c5cd6)' },
  { role: 'Policymaker (SP)', desc: 'Read-only strategic intelligence', tone: 'var(--lp-amber)' },
  { role: 'Officer / Viewer', desc: 'Evidence handling & read access', tone: 'var(--lp-text-2)' },
];

const navFor = (path: string) =>
  `${(import.meta.env.BASE_URL || '/').replace(/\/+$/, '') || ''}${path}`;

export const Landing: React.FC = () => {
  const [clock, setClock] = useState(formatIstClock);
  const [activeModule, setActiveModule] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => setClock(formatIstClock()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const pulse = window.setInterval(() => setActiveModule((m) => (m + 1) % MODULES.length), 2400);
    return () => window.clearInterval(pulse);
  }, []);

  const securityFacts = useMemo(
    () => [
      { icon: ShieldCheck, tone: 'var(--lp-green)', label: typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'TLS Encrypted' : 'Local Channel' },
      { icon: Lock, tone: 'var(--lp-accent-hi)', label: 'Activity Audited' },
      { icon: Crosshair, tone: 'var(--lp-amber)', label: 'AI-Grounded Intel' },
    ],
    []
  );

  return (
    <div className="landing-root relative flex min-h-[100dvh] w-full flex-col overflow-x-clip font-sans select-none">
      <SecureBackdrop />

      {/* ── Top system bar ── */}
      <header
        className="sticky top-0 z-30 flex h-12 shrink-0 items-center justify-between gap-3 border-b px-4 sm:px-6"
        style={{ borderColor: 'var(--lp-border)', background: 'var(--lp-bg)' }}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg border" style={{ background: 'var(--lp-accent-soft)', borderColor: 'var(--lp-border-strong)' }}>
            <img src="/logo.svg" alt="Saksha emblem" className="h-[68%] w-[68%]" draggable={false} />
          </div>
          <div className="hidden sm:block">
            <span className="block font-extrabold uppercase leading-none tracking-[0.2em]" style={{ color: 'var(--lp-text)', fontSize: 12 }}>Saksha</span>
            <span className="block font-mono uppercase tracking-[0.24em]" style={{ color: 'var(--lp-teal)', fontSize: 7.5 }}>KSP Crime Intelligence</span>
          </div>
        </div>

        <nav className="hidden items-center gap-5 font-mono text-[9px] uppercase tracking-[0.18em] md:flex" style={{ color: 'var(--lp-text-3)' }}>
          <a href={navFor('/docs')} className="transition-colors hover:text-[color:var(--lp-accent-hi)]">Documentation</a>
          <span className="flex items-center gap-1.5" style={{ color: 'var(--lp-green)' }}>
            <span className="lp-live-dot" style={{ background: 'var(--lp-green)' }} />
            SECURE NODE ONLINE
          </span>
        </nav>

        <div className="flex items-center gap-3 font-mono text-[8px] tracking-[0.2em]" style={{ color: 'var(--lp-text-3)' }}>
          <span className="hidden lg:inline" aria-label="Current time, Indian Standard Time">{clock}</span>
          <a
            href={navFor('/login')}
            className="inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 font-mono text-[8.5px] font-bold uppercase tracking-[0.18em] transition-colors"
            style={{
              borderColor: 'var(--lp-border-strong)',
              background: 'var(--lp-accent-soft)',
              color: 'var(--lp-accent-hi)',
            }}
          >
            Sign In <Lock className="h-3 w-3" />
          </a>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative z-10 mx-auto w-full max-w-6xl px-4 pb-10 pt-14 text-center sm:pt-20">
        <motion.span
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[8px] uppercase tracking-[0.24em]"
          style={{ borderColor: 'rgba(224, 96, 85, 0.35)', background: 'var(--lp-red-soft)', color: 'var(--lp-red)' }}
        >
          <Crosshair className="h-3 w-3" /> RESTRICTED · KARNATAKA STATE POLICE · 2026
        </motion.span>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.05 }}
          className="mx-auto mt-6 max-w-4xl"
          style={{ fontSize: 'clamp(34px, 6vw, 68px)' }}
        >
          <span className="lp-gradient-title block font-extrabold uppercase leading-[0.95] tracking-tight">
            Crime Intelligence
          </span>
          <span className="mt-1 block font-extrabold uppercase leading-none tracking-[0.14em]" style={{ color: 'var(--lp-teal)' }}>
            Analytical Platform
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.12 }}
          className="mx-auto mt-6 max-w-2xl text-sm leading-relaxed"
          style={{ color: 'var(--lp-text-2)' }}
        >
          Saksha transforms raw crime records into actionable intelligence for the Karnataka State Police —
          blending AI/ML predictive models, graph-based criminal network analysis, real-time alerts and a
          secure role-based command platform.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.18 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <a
            href={navFor('/login')}
            className="inline-flex items-center gap-2 rounded-xl border px-6 py-3 font-mono text-[11px] font-bold uppercase tracking-[0.16em] transition-all hover:brightness-110"
            style={{
              borderColor: 'var(--lp-accent)',
              background: 'linear-gradient(180deg, var(--lp-accent), color-mix(in srgb, var(--lp-accent) 80%, black))',
              color: '#fff',
              boxShadow: '0 8px 30px rgba(47,127,224,0.25)',
            }}
          >
            Enter Secure Platform <ArrowRight className="h-4 w-4" />
          </a>
          <a
            href={navFor('/docs')}
            className="inline-flex items-center gap-2 rounded-xl border px-6 py-3 font-mono text-[11px] font-bold uppercase tracking-[0.16em] transition-colors"
            style={{ borderColor: 'var(--lp-border-strong)', background: 'var(--lp-surface-3)', color: 'var(--lp-text)' }}
          >
            <BookOpen className="h-4 w-4" style={{ color: 'var(--lp-accent-hi)' }} /> Read Documentation
          </a>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="mt-9 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 font-mono text-[8px] uppercase tracking-[0.18em]"
          style={{ color: 'var(--lp-text-3)' }}
        >
          {securityFacts.map(({ icon: Icon, tone, label }) => (
            <span key={label} className="inline-flex items-center gap-1.5">
              <Icon className="h-3 w-3" style={{ color: tone }} /> {label}
            </span>
          ))}
        </motion.div>

        <motion.a
          href="#capabilities"
          className="mx-auto mt-10 inline-flex flex-col items-center gap-1 font-mono text-[8px] uppercase tracking-[0.24em]"
          style={{ color: 'var(--lp-text-3)' }}
        >
          Explore
          <ChevronDown className="h-4 w-4 animate-bounce" />
        </motion.a>
      </section>

      {/* ── Capabilities ── */}
      <section id="capabilities" className="relative z-10 mx-auto w-full max-w-6xl px-4 py-10">
        <div className="mb-8 text-center">
          <h2 className="text-lg font-extrabold uppercase tracking-[0.14em]" style={{ color: 'var(--lp-text)' }}>
            Platform Capabilities
          </h2>
          <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.2em]" style={{ color: 'var(--lp-text-3)' }}>
            8 AI/ML algorithms · 75+ intelligence endpoints · 16 data tables · Live graph DB
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map(({ icon, title, desc, tone, soft }, i) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: i * 0.04 }}
              className="rounded-xl border p-4 transition-colors duration-200"
              style={{ background: 'var(--lp-surface-3)', borderColor: 'var(--lp-border)' }}
            >
              <div className="flex items-center gap-3">
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border"
                  style={{ background: soft, borderColor: 'var(--lp-border-strong)', color: tone }}
                >
                  {icon}
                </span>
                <h3 className="text-[12px] font-bold uppercase tracking-wider" style={{ color: 'var(--lp-text)' }}>
                  {title}
                </h3>
              </div>
              <p className="mt-3 text-xs leading-relaxed" style={{ color: 'var(--lp-text-2)' }}>{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Modules ticker ── */}
      <section className="relative z-10 mx-auto w-full max-w-6xl px-4 py-10">
        <div
          className="overflow-hidden rounded-2xl border"
          style={{ background: 'var(--lp-surface)', borderColor: 'var(--lp-border)' }}
        >
          <div className="grid grid-cols-1 md:grid-cols-2">
            <div className="flex flex-col justify-center border-b p-6 md:border-b-0 md:border-r md:p-8" style={{ borderColor: 'var(--lp-border)' }}>
              <span className="font-mono text-[8px] uppercase tracking-[0.26em]" style={{ color: 'var(--lp-teal)' }}>
                Integrated Command Modules
              </span>
              <h3 className="mt-3 text-lg font-extrabold uppercase tracking-wide" style={{ color: 'var(--lp-text)' }}>
                One platform. Every layer of the investigation.
              </h3>
              <p className="mt-3 text-sm leading-relaxed" style={{ color: 'var(--lp-text-2)' }}>
                From the moment an FIR is filed to predictive hotspot analysis and network forensics,
                Saksha unifies the entire intelligence lifecycle under a single tactical interface.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-px bg-[color:var(--lp-border)]">
              {MODULES.map(({ icon, label, tone }, i) => (
                <div
                  key={label}
                  className={`flex items-center gap-2.5 p-4 transition-colors ${activeModule === i ? 'bg-[color:var(--lp-accent-soft)]' : 'bg-[color:var(--lp-surface-3)]'}`}
                >
                  <span className="shrink-0" style={{ color: tone }}>{icon}</span>
                  <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: 'var(--lp-text)' }}>{label}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Roles ── */}
      <section className="relative z-10 mx-auto w-full max-w-6xl px-4 py-10">
        <div className="mb-8 text-center">
          <h2 className="text-lg font-extrabold uppercase tracking-[0.14em]" style={{ color: 'var(--lp-text)' }}>
            Built For Every Role
          </h2>
          <p className="mt-2 font-mono text-[9px] uppercase tracking-[0.2em]" style={{ color: 'var(--lp-text-3)' }}>
            Role-based access control across the force
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {ROLES.map(({ role, desc, tone }) => (
            <div key={role} className="rounded-xl border p-4" style={{ background: 'var(--lp-surface-3)', borderColor: 'var(--lp-border)' }}>
              <div className="flex items-center gap-2">
                <CheckCircle className="h-3.5 w-3.5 shrink-0" style={{ color: tone }} />
                <span className="text-[12px] font-bold uppercase tracking-wider" style={{ color: 'var(--lp-text)' }}>{role}</span>
              </div>
              <p className="mt-2 text-xs" style={{ color: 'var(--lp-text-2)' }}>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="relative z-10 mx-auto w-full max-w-6xl px-4 py-12 text-center">
        <div
          className="rounded-2xl border p-8 sm:p-12"
          style={{ background: 'linear-gradient(165deg, var(--lp-accent-soft), transparent 60%)', borderColor: 'var(--lp-border-strong)' }}
        >
          <h2 className="text-xl font-extrabold uppercase tracking-wide" style={{ color: 'var(--lp-text)' }}>
            Ready to begin?
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm" style={{ color: 'var(--lp-text-2)' }}>
            Authorised personnel can sign in with a badge ID and PIN, username, or secure face recognition.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <a
              href={navFor('/login')}
              className="inline-flex items-center gap-2 rounded-xl border px-7 py-3.5 font-mono text-[11px] font-bold uppercase tracking-[0.16em] transition-all hover:brightness-110"
              style={{
                borderColor: 'var(--lp-accent)',
                background: 'linear-gradient(180deg, var(--lp-accent), color-mix(in srgb, var(--lp-accent) 80%, black))',
                color: '#fff',
                boxShadow: '0 8px 30px rgba(47,127,224,0.25)',
              }}
            >
              Sign In to Saksha <Lock className="h-4 w-4" />
            </a>
            <a
              href={navFor('/docs')}
              className="inline-flex items-center gap-2 rounded-xl border px-7 py-3.5 font-mono text-[11px] font-bold uppercase tracking-[0.16em] transition-colors"
              style={{ borderColor: 'var(--lp-border-strong)', background: 'var(--lp-surface-3)', color: 'var(--lp-text)' }}
            >
              <BookOpen className="h-4 w-4" style={{ color: 'var(--lp-accent-hi)' }} /> Documentation
            </a>
          </div>
        </div>
      </section>

      {/* ── Alert strip ── */}
      <section className="relative z-10 mx-auto w-full max-w-6xl px-4 pb-10">
        <div
          className="flex items-center gap-3 rounded-xl border px-4 py-3"
          style={{ borderColor: 'rgba(224, 96, 85, 0.3)', background: 'var(--lp-red-soft)' }}
        >
          <AlertTriangle className="h-4 w-4 shrink-0" style={{ color: 'var(--lp-red)' }} />
          <p className="text-xs leading-relaxed" style={{ color: 'var(--lp-text-2)' }}>
            <span className="font-bold uppercase" style={{ color: 'var(--lp-red)' }}>Access controlled.</span> Saksha is restricted to authorised Karnataka State Police personnel.
            All session activity is recorded and audited under KSP Security Directive 7.2.
          </p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer
        className="relative z-20 mt-auto shrink-0 border-t py-4 text-center font-mono text-[8px] uppercase tracking-[0.24em]"
        style={{ borderColor: 'var(--lp-border)', background: 'var(--lp-bg)', color: 'var(--lp-text-3)' }}
      >
        SAKSHA v2.0 · Karnataka State Police · © 2026 · Datathon 2026 Challenge 2 — Crime Intelligence & Analytical Platform
      </footer>
    </div>
  );
};

export default Landing;
