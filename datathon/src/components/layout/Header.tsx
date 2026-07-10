import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { SessionTimer } from '../auth/SessionTimer';
import { ShieldCheck, HardDrive, Key, UserCheck, AlertTriangle } from 'lucide-react';
import { isEmulatorActive } from '../../services/api';

export const Header: React.FC = () => {
  const { user } = useAuthStore();
  const [systime, setSystime] = useState(new Date().toLocaleTimeString());
  const [emulatorActive, setEmulatorActive] = useState(isEmulatorActive);

  useEffect(() => {
    const handler = (e: Event) => {
      setEmulatorActive((e as CustomEvent).detail);
    };
    window.addEventListener('emulator-status-changed', handler);
    return () => window.removeEventListener('emulator-status-changed', handler);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setSystime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-16 border-b border-border-color bg-secondary-bg/20 backdrop-blur-md px-6 flex items-center justify-between select-none z-30">
      {/* Platform Meta Info */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#0E9E78] animate-ping" />
          <span className="text-[10px] font-mono text-[#0E9E78] uppercase font-bold tracking-widest">
            KSP CORE SECURE SUITE
          </span>
        </div>
        
        {emulatorActive ? (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-cyan-950/40 border border-cyan-500/30 text-cyan-400 text-[8.5px] font-mono rounded tracking-widest uppercase font-bold shadow-[0_0_10px_rgba(6,182,212,0.15)] select-none">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            LOCAL HUD EMULATOR
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2 py-0.5 bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 text-[8.5px] font-mono rounded tracking-widest uppercase font-bold shadow-[0_0_10px_rgba(16,185,129,0.15)] select-none">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
            SYSTEM ONLINE
          </div>
        )}
      </div>

      {/* Center Title or Notification Info */}
      <div className="hidden lg:flex items-center gap-2 px-3 py-1 bg-slate-950/40 border border-border-color rounded-full text-[9px] font-mono text-[#A8B4CC]">
        <HardDrive className="w-3 h-3 text-[#1E6FD9]" />
        <span>DB REPLICATION: <span className="text-[#0E9E78] font-bold">100% IN-SYNC</span></span>
        <span className="text-slate-600">|</span>
        <span>LATENCY: <span className="text-sky-400">12ms</span></span>
      </div>

      {/* Right User Telemetry Block */}
      <div className="flex items-center gap-4">
        {/* Real-time Digital Clock */}
        <div className="hidden sm:flex flex-col text-right">
          <span className="text-xs font-mono font-bold text-[#E8EDF5]">{systime}</span>
          <span className="text-[8px] font-mono tracking-wider text-[#6A7A96] uppercase select-none">
            IST (UTC+5:30)
          </span>
        </div>

        {/* Security watermark badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-[#1E6FD9]/10 border border-[#1E6FD9]/30 text-[#1E6FD9] text-[9.5px] font-mono rounded">
          <Key className="w-3 h-3" />
          <span className="uppercase tracking-wider">CONFIDENTIAL</span>
        </div>

        {/* Active Role and Session Time Indicator */}
        <SessionTimer />
      </div>
    </header>
  );
};

export default Header;
