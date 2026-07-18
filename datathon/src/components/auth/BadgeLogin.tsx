import React, { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '../../store/authStore';
import { Shield, AlertCircle, UserCheck } from 'lucide-react';

interface BadgeLoginProps {
  onSuccess: () => void;
}

export const BadgeLogin: React.FC<BadgeLoginProps> = ({ onSuccess }) => {
  const login = useAuthStore((state) => state.login);
  const loginError = useAuthStore((state) => state.loginError);

  const [badgeId, setBadgeId] = useState('');
  const [pin, setPin] = useState('');
  const [detectedRole, setDetectedRole] = useState<'SCRB' | 'IO' | 'SP' | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localErrors, setLocalErrors] = useState<string | null>(null);

  const pinInputRef = useRef<HTMLInputElement>(null);

  // Auto-detect role as the user types their Badge ID prefix
  useEffect(() => {
    const uc = badgeId.toUpperCase().trim();
    if (uc.startsWith('SCRB')) {
      setDetectedRole('SCRB');
    } else if (uc.startsWith('IO')) {
      setDetectedRole('IO');
    } else if (uc.startsWith('SP')) {
      setDetectedRole('SP');
    } else {
      setDetectedRole(null);
    }
  }, [badgeId]);

  // Auto-submit form when PIN is fully entered
  useEffect(() => {
    if (pin.length === 6) {
      void handleFormSubmit();
    }
  }, [pin]);

  // Focus PIN input on mount
  useEffect(() => {
    if (pinInputRef.current) {
      pinInputRef.current.focus();
    }
  }, []);

  const handleFormSubmit = async () => {
    if (!badgeId.trim()) {
      setLocalErrors('Badge ID is required.');
      return;
    }
    if (pin.length < 6) {
      setLocalErrors('PIN must be exactly 6 digits.');
      return;
    }
    setLocalErrors(null);
    setIsSubmitting(true);

    try {
      const res = await login(badgeId, pin);
      if (res) {
        onSuccess();
      }
    } catch (e) {
      setLocalErrors('Authentication Service connection error.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '').slice(0, 6);
    setPin(val);
  };

  const handleKeypadPress = (num: number) => {
    if (pin.length < 6) {
      setPin((prev) => prev + num);
    }
  };

  const handleBackspace = () => {
    setPin((prev) => prev.slice(0, -1));
  };

  const handleClear = () => {
    setPin('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      void handleFormSubmit();
    }
  };

  return (
    <div className="w-full max-w-sm flex flex-col gap-4 font-sans text-left">
      
      {/* Insignia / Notice */}
      <div className="flex items-center gap-3 bg-secondary-bg/25 border border-border-color p-3 rounded-card">
        <div className="p-2 bg-[#1E6FD9]/10 rounded-full text-[#1E6FD9]">
          <Shield className="w-5 h-5 animate-pulse" />
        </div>
        <div>
          <h4 className="text-[11.5px] font-mono uppercase text-[#A8B4CC] font-bold">Officer Database Check</h4>
          <span className="text-[9.5px] font-mono text-[#6A7A96] uppercase select-none">Access audited by KSP secure logs</span>
        </div>
      </div>

      {/* Input Fields */}
      <div className="flex flex-col gap-3">
        
        {/* Badge ID Input */}
        <div>
          <label className="block text-[9px] font-mono uppercase text-[#6A7A96] mb-1 tracking-wider">
            Police Badge ID
          </label>
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-[#6A7A96] pointer-events-none">
              <div className="w-1.5 h-3.5 flex flex-col gap-0.5 mr-2 shrink-0">
                <div className="w-full bg-[#f48f42] h-0.5" />
                <div className="w-full bg-white h-0.5" />
                <div className="w-full bg-[#0E9E78] h-0.5" />
              </div>
            </span>
            <input
              type="text"
              placeholder="e.g. SCRB-7740, IO-3921"
              value={badgeId}
              onChange={(e) => setBadgeId(e.target.value)}
              className="w-full pl-8 pr-16 py-2 bg-slate-950/60 text-white font-mono text-xs border border-border-color focus:border-[#1E6FD9]/45 rounded-btn outline-none transition-colors"
            />
            {detectedRole && (
              <span className="absolute right-2 top-1.5 px-2 py-0.5 bg-[#1E6FD9]/20 text-[#1E6FD9] text-[8px] font-mono rounded-full border border-[#1E6FD9]/30 flex items-center gap-1 select-none font-bold">
                <UserCheck className="w-2.5 h-2.5" />
                {detectedRole}
              </span>
            )}
          </div>
          {detectedRole === 'SP' && (
            <div className="mt-2 p-1.5 bg-[#D4820A]/10 border border-[#D4820A]/20 text-[9.5px] font-mono text-[#D4820A] rounded select-none font-bold uppercase tracking-wider animate-[pulse_2s_infinite] text-center">
              [CLEARANCE LEVEL: SUPERINTENDENT OF POLICE]
            </div>
          )}
          {detectedRole === 'IO' && (
            <div className="mt-2 p-1.5 bg-[#1E6FD9]/10 border border-[#1E6FD9]/20 text-[9.5px] font-mono text-[#1E6FD9] rounded select-none font-bold uppercase tracking-wider animate-[pulse_2s_infinite] text-center">
              [CLEARANCE LEVEL: DEPUTY SP / INVESTIGATOR]
            </div>
          )}
          {detectedRole === 'SCRB' && (
            <div className="mt-2 p-1.5 bg-[#0E9E78]/10 border border-[#0E9E78]/20 text-[9.5px] font-mono text-[#0E9E78] rounded select-none font-bold uppercase tracking-wider animate-[pulse_2s_infinite] text-center">
              [CLEARANCE LEVEL: SCRB ANALYST]
            </div>
          )}
        </div>

        {/* 6-Digit PIN input (Masked & Keyboard-Typable) */}
        <div>
          <label className="block text-[9px] font-mono uppercase text-[#6A7A96] mb-1 tracking-wider">
            6-Digit Authentication PIN
          </label>
          
          <div className="relative flex items-center justify-center">
            {/* Real hidden PIN input for native typing */}
            <input
              ref={pinInputRef}
              type="password"
              pattern="[0-9]*"
              inputMode="numeric"
              maxLength={6}
              value={pin}
              onChange={handlePinChange}
              onKeyDown={handleKeyDown}
              className="w-full py-2 bg-slate-950/60 text-white font-mono text-center tracking-[1.5em] text-xs border border-border-color focus:border-[#1E6FD9]/45 rounded-btn outline-none transition-colors"
              placeholder="••••••"
            />
          </div>
        </div>
      </div>

      {/* Screen Pad (Numeric Keypad Grid) */}
      <div className="grid grid-cols-3 gap-1.5 bg-slate-950/40 p-2 border border-border-color/30 rounded-card">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
          <button
            key={num}
            type="button"
            onClick={() => handleKeypadPress(num)}
            className="py-2.5 bg-secondary-bg/25 hover:bg-[#1E6FD9]/10 border border-border-color/30 hover:border-[#1E6FD9]/45 text-[#A8B4CC] hover:text-white font-mono text-[13px] font-bold text-center hover:scale-[1.03] active:scale-[0.97] rounded transition-all cursor-pointer"
          >
            {num}
          </button>
        ))}
        
        {/* Keypad actions */}
        <button
          type="button"
          onClick={handleClear}
          className="py-2.5 bg-[#C94A2A]/5 hover:bg-[#C94A2A]/20 border border-[#C94A2A]/15 hover:border-[#C94A2A]/40 text-[#C94A2A] hover:text-white font-mono text-[10px] uppercase font-bold text-center rounded transition-all cursor-pointer"
        >
          Clear
        </button>
        
        <button
          type="button"
          onClick={() => handleKeypadPress(0)}
          className="py-2.5 bg-secondary-bg/25 hover:bg-[#1E6FD9]/10 border border-border-color/30 hover:border-[#1E6FD9]/45 text-[#A8B4CC] hover:text-white font-mono text-[13px] font-bold text-center hover:scale-[1.03] active:scale-[0.97] rounded transition-all cursor-pointer"
        >
          0
        </button>
        
        <button
          type="button"
          onClick={handleBackspace}
          className="py-2.5 bg-[#D4820A]/5 hover:bg-[#D4820A]/20 border border-[#D4820A]/15 hover:border-[#D4820A]/40 text-[#D4820A] hover:text-white font-mono text-[10px] uppercase font-bold text-center rounded transition-all cursor-pointer"
        >
          Del
        </button>
      </div>

      {/* Error Notices */}
      {(loginError || localErrors) && (
        <div className="flex items-start gap-2 bg-[#C94A2A]/15 border border-[#C94A2A]/30 p-2.5 rounded-btn text-[10.5px] text-white">
          <AlertCircle className="w-4 h-4 text-[#C94A2A] shrink-0 mt-0.5" />
          <span>{localErrors || loginError}</span>
        </div>
      )}

      {/* Mock credentials list */}
      <div className="text-center text-[8.5px] font-mono text-[#6A7A96] leading-relaxed select-none border-t border-border-color/30 pt-3">
        MOCK CREDENTIALS SPECIFICATION:<br />
        Superintendent: <span className="text-slate-400 font-bold">SP-0088</span> / PIN <span className="text-slate-400 font-bold">123456</span><br />
        Investigator: <span className="text-slate-400 font-bold">IO-3921</span> / PIN <span className="text-slate-400 font-bold">123456</span><br />
        Analyst: <span className="text-slate-400 font-bold">SCRB-7740</span> / PIN <span className="text-slate-400 font-bold">123456</span>
      </div>
    </div>
  );
};

export default BadgeLogin;
