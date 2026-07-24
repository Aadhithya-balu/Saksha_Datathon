import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import ParticleField from '../components/three/ParticleField';
import FaceIDScanner from '../components/auth/FaceIDScanner';
import BadgeLogin from '../components/auth/BadgeLogin';
import { ShieldCheck, UserCheck, Key, Lock, Eye } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export const Login: React.FC = () => {
  const [loginMethod, setLoginMethod] = useState<'face' | 'badge'>('face');
  const loginWithFace = useAuthStore((state) => state.loginWithFace);

  const [terminalLogs, setTerminalLogs] = useState<string[]>([
    'ESTABLISHING TLS TUNNEL...',
    'KSP CENTRAL NODE DETECTED...',
    'SHIELD ENCRYPTOR: ACTIVE',
  ]);

  useEffect(() => {
    const logTemplates = [
      'TUNNEL ROUTING: PORT 5432 SECURED',
      'LEDGER INTEGRITY CHECK: 100% IN-SYNC',
      'BROADCASTING NODE SECURE WATERMARK',
      'COMPLIANCE LEDGER ENGAGED',
      'IP AUDITING MONITOR ACTIVE',
      'ALERTS GATEWAY LISTENING...',
      'INCOMING PACKET CRYPTO VERIFIED',
    ];

    const interval = setInterval(() => {
      const randomLine = logTemplates[Math.floor(Math.random() * logTemplates.length)];
      const timestamp = new Date().toLocaleTimeString();
      setTerminalLogs((prev) => [...prev.slice(-2), `[${timestamp}] ${randomLine}`]);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const handleFaceSuccess = async () => {
    await loginWithFace();
  };

  const handleBadgeSuccess = () => {
    // Session state triggers layout swap in App.tsx
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center p-4 md:p-8 overflow-hidden select-none dynamic-login-mesh font-sans">
      {/* Dynamic abstract background particles */}
      <ParticleField />

      {/* Main split-panel container */}
      <div className="w-full max-w-5xl bg-[var(--bg-secondary)]/25 border border-[var(--border-primary)] rounded-2xl grid grid-cols-1 lg:grid-cols-12 overflow-hidden shadow-2xl relative z-20 backdrop-blur-lg">
        
        {/* LEFT COLUMN: Clean Police Branding & abstract security icon (5 cols on lg) */}
        <div className="lg:col-span-5 bg-[var(--bg-tertiary)]/40 border-r border-[var(--border-primary)] flex flex-col justify-between p-8 relative overflow-hidden">
          
          {/* Top Logo branding */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-blue)]/15 border border-[var(--accent-blue)]/30 flex items-center justify-center shadow-[0_0_12px_rgba(30,111,217,0.15)] overflow-hidden">
              <img src="/logo.svg" alt="Saksha" className="w-7 h-7" />
            </div>
            <div className="flex flex-col">
              <h2 className="text-[12px] font-mono font-bold tracking-widest text-[var(--text-primary)] uppercase">
                SAKSHA INTEL
              </h2>
              <span className="text-[8.5px] font-mono text-[var(--accent-teal)] uppercase font-bold tracking-widest">
                KSP Secure Portal
              </span>
            </div>
          </div>

          {/* Creative HUD Radar Visualization */}
          <div className="my-8 flex flex-col items-center justify-center relative py-8">
            <div className="relative w-48 h-48 flex items-center justify-center rounded-full border border-border-color/40 bg-[var(--bg-tertiary)]/20 backdrop-blur-md">
              {/* Rotating Radar Sweep Beam */}
              <div className="absolute inset-0 rounded-full bg-[conic-gradient(from_0deg,transparent_50%,rgba(30,111,217,0.15)_100%)] animate-[spin_4s_linear_infinite] pointer-events-none" />
              
              {/* Outer dashed scanner rings */}
              <div className="absolute inset-1 rounded-full border border-dashed border-[var(--accent-blue)]/20 animate-[spin_60s_linear_infinite]" />
              <div className="absolute inset-4 rounded-full border border-[var(--border-secondary)]/30" />
              <div className="absolute inset-8 rounded-full border border-dashed border-[var(--accent-teal)]/25 animate-[spin_20s_linear_infinite]" />
              
              {/* Corner brackets overlay */}
              <div className="absolute top-2 left-2 w-3.5 h-3.5 border-t-2 border-l-2 border-[var(--accent-blue)]/40" />
              <div className="absolute top-2 right-2 w-3.5 h-3.5 border-t-2 border-r-2 border-[var(--accent-blue)]/40" />
              <div className="absolute bottom-2 left-2 w-3.5 h-3.5 border-b-2 border-l-2 border-[var(--accent-blue)]/40" />
              <div className="absolute bottom-2 right-2 w-3.5 h-3.5 border-b-2 border-r-2 border-[var(--accent-blue)]/40" />
              
              {/* Core Lock badge */}
              <div className="w-16 h-16 rounded-full bg-[var(--bg-primary)] flex items-center justify-center border border-[var(--accent-blue)]/40 shadow-[0_0_25px_rgba(30,111,217,0.2)] z-10">
                <Lock className="w-6 h-6 text-[var(--accent-blue)] animate-pulse" />
              </div>
            </div>

            {/* Diagnostic system info readout */}
            <div className="mt-4 flex flex-col items-center gap-1 font-mono text-[8px] text-[var(--text-muted)] tracking-wider">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent-teal)] animate-ping" />
                SYSTEM CLEARANCE: L10
              </span>
              <span>DB INTEGRITY: 100% IN-SYNC</span>
              <span>TUNNEL ID: KSP-NODE-BNG</span>
            </div>

            {/* Terminal Live logs */}
            <div className="w-full mt-4 bg-[var(--bg-primary)]/80 border border-[var(--border-primary)] rounded p-2.5 font-mono text-[7px] text-emerald-500 text-left space-y-1 select-none">
              <span className="text-[var(--text-disabled)] block uppercase font-bold text-[6.5px] tracking-widest border-b border-[var(--border-primary)] pb-1 mb-1">
                Live Audit Logs stream
              </span>
              {terminalLogs.map((log, index) => (
                <div key={index} className="truncate">{log}</div>
              ))}
            </div>
          </div>

          {/* Product description & compliance */}
          <div className="space-y-4 text-left font-mono">
            <div className="h-[1px] bg-[var(--border-primary)] w-full" />
            <div>
              <h3 className="text-[11px] font-bold text-[var(--text-primary)] uppercase tracking-wider">
                Crime Intelligence Gateway
              </h3>
              <p className="text-[9.5px] text-[var(--text-secondary)] leading-relaxed mt-1.5">
                Authorized law enforcement access only. Every session transaction is cryptographically signed and logged for compliance auditing.
              </p>
            </div>
            <div className="flex items-center gap-1.5 text-[8.5px] text-[var(--accent-teal)] font-bold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>SECURE TUNNEL ENCRYPTED</span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Authentication Card with tabs (7 cols on lg) */}
        <div className="lg:col-span-7 p-8 md:p-12 flex flex-col justify-center min-h-[520px] bg-[var(--bg-tertiary)]/20">
          
          {/* Header */}
          <div className="mb-6 text-center lg:text-left">
            <h1 className="text-xl md:text-2xl font-extrabold text-[var(--text-primary)] tracking-tight leading-tight uppercase font-sans">
              Gateway Access Verification
            </h1>
            <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-1 uppercase tracking-widest">
              Karnataka State Police Intelligence Node
            </p>
          </div>

          {/* Clean, Microsoft Fluent styled tabs */}
          <div className="flex w-full max-w-sm mb-6 bg-[var(--bg-primary)]/50 p-1 border border-[var(--border-primary)] rounded-lg mx-auto lg:mx-0">
            <button
              onClick={() => { setLoginMethod('face'); }}
              className={`flex-1 py-1.5 text-[9.5px] font-mono uppercase tracking-wider flex items-center justify-center gap-2 rounded transition-all cursor-pointer ${
                loginMethod === 'face'
                  ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] shadow-sk-blue font-bold'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Face ID Verify
            </button>
            <button
              onClick={() => { setLoginMethod('badge'); }}
              className={`flex-1 py-1.5 text-[9.5px] font-mono uppercase tracking-wider flex items-center justify-center gap-2 rounded transition-all cursor-pointer ${
                loginMethod === 'badge'
                  ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] shadow-sk-blue font-bold'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Key className="w-3.5 h-3.5" />
              Badge Credentials
            </button>
          </div>

          {/* Form wrapper */}
          <div className="w-full flex justify-center lg:justify-start">
            <div className="w-full max-w-sm">
              {loginMethod === 'face' ? (
                <FaceIDScanner onVerifySuccess={handleFaceSuccess} />
              ) : (
                <BadgeLogin onSuccess={handleBadgeSuccess} />
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Footer telemetry details */}
      <div className="absolute bottom-4 left-4 z-20 text-[8px] font-mono text-[var(--text-muted)] select-none text-left leading-relaxed">
        SECURE GATEWAY ENCRYPTION: 512-BLAKE3<br />
        STATE COMPLIANCE DEPT © 2026
      </div>
      
      <div className="absolute bottom-4 right-4 z-20 text-[8px] font-mono text-[var(--text-muted)] select-none text-right">
        AUTHORIZED LAW ENFORCEMENT SERVICES ONLY<br />
        UNAUTHORIZED ACCESS SENSING MONITOR ENGAGED
      </div>
    </div>
  );
};

export default Login;
