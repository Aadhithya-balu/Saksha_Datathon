import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import ParticleField from '../components/three/ParticleField';
import FaceIDScanner from '../components/auth/FaceIDScanner';
import BadgeLogin from '../components/auth/BadgeLogin';
import { ShieldCheck, UserCheck, Key, Lock, Eye, ChevronRight } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export const Login: React.FC = () => {
  const [loginMethod, setLoginMethod] = useState<'face' | 'badge'>('badge');
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
      {/* Background particles */}
      <ParticleField />

      {/* Main container */}
      <div className="w-full max-w-6xl bg-[var(--bg-secondary)]/25 border border-[var(--border-primary)] rounded-2xl grid grid-cols-1 lg:grid-cols-2 overflow-hidden shadow-2xl relative z-20 backdrop-blur-lg">
        
        {/* LEFT COLUMN: Saksha Logo & Branding */}
        <div className="bg-[var(--bg-tertiary)]/40 border-r border-[var(--border-primary)] flex flex-col items-center justify-center p-8 md:p-12 relative overflow-hidden">
          
          {/* Large Logo */}
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col items-center"
          >
            <div className="w-24 h-24 rounded-2xl bg-[var(--accent-blue)]/15 border border-[var(--accent-blue)]/30 flex items-center justify-center shadow-[0_0_30px_rgba(30,111,217,0.2)] mb-6 overflow-hidden">
              <img src="/logo.svg" alt="Saksha" className="w-16 h-16" />
            </div>
            
            <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--text-primary)] tracking-tight uppercase font-sans mb-2">
              SAKSHA
            </h1>
            <p className="text-[11px] font-mono text-[var(--accent-teal)] uppercase font-bold tracking-[0.3em] mb-8">
              Crime Intelligence Platform
            </p>

            {/* Feature highlights */}
            <div className="flex flex-col gap-3 w-full max-w-xs">
              <div className="flex items-center gap-3 p-3 bg-[var(--bg-primary)]/50 border border-[var(--border-primary)] rounded-lg">
                <div className="w-8 h-8 rounded-lg bg-[#1E6FD9]/15 flex items-center justify-center">
                  <Lock className="w-4 h-4 text-[#1E6FD9]" />
                </div>
                <div>
                  <p className="text-[10px] font-mono font-bold text-[var(--text-primary)] uppercase">Encrypted Access</p>
                  <p className="text-[9px] font-mono text-[var(--text-muted)]">512-BLAKE3 Security</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3 p-3 bg-[var(--bg-primary)]/50 border border-[var(--border-primary)] rounded-lg">
                <div className="w-8 h-8 rounded-lg bg-[#0E9E78]/15 flex items-center justify-center">
                  <ShieldCheck className="w-4 h-4 text-[#0E9E78]" />
                </div>
                <div>
                  <p className="text-[10px] font-mono font-bold text-[var(--text-primary)] uppercase">Audited Sessions</p>
                  <p className="text-[9px] font-mono text-[var(--text-muted)]">KSP Compliance</p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-[var(--bg-primary)]/50 border border-[var(--border-primary)] rounded-lg">
                <div className="w-8 h-8 rounded-lg bg-[#8B5CF6]/15 flex items-center justify-center">
                  <Eye className="w-4 h-4 text-[#8B5CF6]" />
                </div>
                <div>
                  <p className="text-[10px] font-mono font-bold text-[var(--text-primary)] uppercase">Face ID Ready</p>
                  <p className="text-[9px] font-mono text-[var(--text-muted)]">Biometric Verify</p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Terminal Live logs */}
          <div className="w-full mt-8 bg-[var(--bg-primary)]/80 border border-[var(--border-primary)] rounded p-3 font-mono text-[8px] text-emerald-500 text-left space-y-1 select-none">
            <span className="text-[var(--text-disabled)] block uppercase font-bold text-[7px] tracking-widest border-b border-[var(--border-primary)] pb-1 mb-1">
              Live Audit Stream
            </span>
            {terminalLogs.map((log, index) => (
              <div key={index} className="truncate">{log}</div>
            ))}
          </div>
        </div>

        {/* RIGHT COLUMN: Authentication */}
        <div className="p-8 md:p-12 flex flex-col justify-center min-h-[520px] bg-[var(--bg-tertiary)]/20">
          
          {/* Header */}
          <div className="mb-6">
            <h2 className="text-xl md:text-2xl font-extrabold text-[var(--text-primary)] tracking-tight leading-tight uppercase font-sans">
              Secure Access
            </h2>
            <p className="text-[10px] font-mono text-[var(--text-muted)] mt-1 uppercase tracking-widest">
              Karnataka State Police Intelligence Node
            </p>
          </div>

          {/* Login method tabs */}
          <div className="flex w-full mb-6 bg-[var(--bg-primary)]/50 p-1 border border-[var(--border-primary)] rounded-lg">
            <button
              onClick={() => setLoginMethod('badge')}
              className={`flex-1 py-2 text-[10px] font-mono uppercase tracking-wider flex items-center justify-center gap-2 rounded transition-all cursor-pointer ${
                loginMethod === 'badge'
                  ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] shadow-sk-blue font-bold'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Key className="w-3.5 h-3.5" />
              Badge Login
            </button>
            <button
              onClick={() => setLoginMethod('face')}
              className={`flex-1 py-2 text-[10px] font-mono uppercase tracking-wider flex items-center justify-center gap-2 rounded transition-all cursor-pointer ${
                loginMethod === 'face'
                  ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] shadow-sk-blue font-bold'
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <Eye className="w-3.5 h-3.5" />
              Face ID
            </button>
          </div>

          {/* Login form */}
          <div className="w-full">
            {loginMethod === 'face' ? (
              <FaceIDScanner onVerifySuccess={handleFaceSuccess} />
            ) : (
              <BadgeLogin onSuccess={handleBadgeSuccess} />
            )}
          </div>

        </div>
      </div>

      {/* Footer */}
      <div className="absolute bottom-4 left-4 z-20 text-[8px] font-mono text-[var(--text-muted)] select-none text-left leading-relaxed">
        SECURE GATEWAY ENCRYPTION: 512-BLAKE3<br />
        Saksha © 2026
      </div>
      
      <div className="absolute bottom-4 right-4 z-20 text-[8px] font-mono text-[var(--text-muted)] select-none text-right">
        AUTHORIZED LAW ENFORCEMENT SERVICES ONLY<br />
        UNAUTHORIZED ACCESS MONITORING ACTIVE
      </div>
    </div>
  );
};

export default Login;
