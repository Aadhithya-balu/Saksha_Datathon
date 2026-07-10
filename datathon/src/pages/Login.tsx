import React, { useState } from 'react';
import { motion } from 'framer-motion';
import GlobeScene from '../components/three/GlobeScene';
import ParticleField from '../components/three/ParticleField';
import FaceIDScanner from '../components/auth/FaceIDScanner';
import BadgeLogin from '../components/auth/BadgeLogin';
import { ShieldCheck, Fingerprint, Keyboard, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export const Login: React.FC = () => {
  const [loginMethod, setLoginMethod] = useState<'face' | 'badge'>('face');
  const loginWithFace = useAuthStore((state) => state.loginWithFace);
  const user = useAuthStore((state) => state.user);

  // Title Characters reveal parameters
  const platformTitle = "KSP Crime Intelligence & Analytical Platform";
  const titleWords = platformTitle.split(' ');

  const handleFaceSuccess = async () => {
    // Face ID match triggers Zustand Login
    await loginWithFace();
  };

  const handleBadgeSuccess = () => {
    // Zustand Login will trigger re-rendering of App layout
  };

  return (
    <div className="relative min-h-screen w-full flex items-center justify-center p-4 md:p-8 scanline-overlay overflow-hidden select-none bg-primary-bg">
      {/* Floating particles connected nodes */}
      <ParticleField />

      {/* Main double-panel console structure */}
      <div className="w-full max-w-6xl glassmorphism rounded-[14px] border border-border-color grid grid-cols-1 lg:grid-cols-12 overflow-hidden shadow-2xl relative z-20">
        
        {/* LEFT COLUMN: 3D Twin Globe representation (5 cols on lg) */}
        <div className="lg:col-span-5 h-[340px] lg:h-[620px] bg-slate-950/50 border-r border-border-color flex flex-col justify-between p-6 relative">
          {/* Header text watermark */}
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
            <span className="text-[10px] font-mono text-red-500 uppercase font-bold tracking-widest">
              STATE DIRECTORY TELEMETRY : REAL-TIME
            </span>
          </div>

          <div className="flex-1 w-full max-h-[460px]">
            <GlobeScene />
          </div>

          {/* District counter stats */}
          <div className="grid grid-cols-3 gap-2 border-t border-border-color/30 pt-4 text-center font-mono">
            <div>
              <span className="block text-[14px] font-extrabold text-[#E8EDF5]">9</span>
              <span className="text-[8px] text-[#6A7A96] uppercase">Active Nodes</span>
            </div>
            <div>
              <span className="block text-[14px] font-extrabold text-[#0E9E78]">97.8%</span>
              <span className="text-[8px] text-[#6A7A96] uppercase">Map Sync</span>
            </div>
            <div>
              <span className="block text-[14px] font-extrabold text-[#1E6FD9]">4.0s</span>
              <span className="text-[8px] text-[#6A7A96] uppercase">Interval</span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Biometrics Verification and Forms (7 cols on lg) */}
        <div className="lg:col-span-7 p-6 md:p-12 flex flex-col justify-center min-h-[500px] bg-[#111D35]/35 relative">
          
          {/* Top Karnataka State insignia / Title Header */}
          <div className="mb-8 text-center lg:text-left">
            <div className="flex items-center justify-center lg:justify-start gap-2.5 mb-3">
              {/* Karnataka Police Emblem replica or Shield icon */}
              <div className="p-1 px-2.5 border border-[#1E6FD9]/35 bg-[#1E6FD9]/15 text-[#1E6FD9] rounded-btn flex items-center gap-1.5 font-mono text-[9px] uppercase font-bold tracking-widest shadow-glow-blue select-none">
                <ShieldCheck className="w-3.5 h-3.5" />
                KARNATAKA STATE POLICE
              </div>
            </div>

            {/* Letter reveal title (Framer Motion) */}
            <h1 className="text-xl md:text-3xl font-extrabold text-[#E8EDF5] tracking-tight leading-snug text-glow-blue">
              {titleWords.map((word, wordIndex) => (
                <span key={wordIndex} className="inline-block mr-2">
                  {word.split('').map((char, charIndex) => (
                    <motion.span
                      key={charIndex}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        type: 'spring',
                        damping: 12,
                        stiffness: 100,
                        delay: (wordIndex * 3 + charIndex) * 0.035,
                      }}
                      className="inline-block hover:text-[#1E6FD9] transition-colors"
                    >
                      {char}
                    </motion.span>
                  ))}
                </span>
              ))}
            </h1>
            
            <p className="text-[11px] font-mono text-[#6A7A96] mt-2 uppercase tracking-wide">
              DATATHON 2026 CHALLENGE 2 — SYSTEM SECURITY COMPLIANCE GATEWAY
            </p>
          </div>

          {/* Login tab buttons selector */}
          <div className="flex w-full max-w-sm mb-6 bg-slate-950/60 p-1.5 border border-border-color rounded-btn mx-auto lg:mx-0">
            <button
              onClick={() => { setLoginMethod('face'); }}
              className={`flex-1 py-2 text-[10px] font-mono uppercase tracking-wider flex items-center justify-center gap-2 rounded transition-all cursor-pointer ${
                loginMethod === 'face'
                  ? 'bg-[#1E6FD9] text-white shadow-glow-blue font-semiboldScale'
                  : 'text-[#A8B4CC] hover:text-white'
              }`}
            >
              <Fingerprint className="w-3.5 h-3.5" />
              Biometric Face ID
            </button>
            <button
              onClick={() => { setLoginMethod('badge'); }}
              className={`flex-1 py-2 text-[10px] font-mono uppercase tracking-wider flex items-center justify-center gap-2 rounded transition-all cursor-pointer ${
                loginMethod === 'badge'
                  ? 'bg-[#1E6FD9] text-white shadow-glow-blue font-semiboldScale'
                  : 'text-[#A8B4CC] hover:text-white'
              }`}
            >
              <Keyboard className="w-3.5 h-3.5" />
              Badge Credentials
            </button>
          </div>

          {/* Login Form Components Wrapper */}
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

      {/* Decorative footer details */}
      <div className="absolute bottom-4 left-4 z-20 text-[9px] font-mono text-[#6A7A96] select-none text-left leading-relaxed">
        SECURE GATEWAY ENCRYPTION: 512-BLAKE3<br />
        STATE COMPLIANCE DEPT © 2026
      </div>
      
      <div className="absolute bottom-4 right-4 z-20 text-[9px] font-mono text-[#6A7A96] select-none text-right">
        AUTHORIZED LAW ENFORCEMENT SERVICES ONLY<br />
        UNAUTHORIZED ACCESS SENSING MONITOR ENGAGED
      </div>
    </div>
  );
};

export default Login;
