import React, { useState, useEffect, useRef } from 'react';
import { useAuthStore } from '../../store/authStore';
import { Shield, Sparkles, AlertCircle, UserCheck } from 'lucide-react';

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

  const hiddenInputRef = useRef<HTMLInputElement>(null);

  // Auto-detect role as the user types their Badge ID prefix
  useEffect(() => {
    const uc = badgeId.toUpperCase().trim();
    if (uc.startsWith('KG')) {
      const digits = uc.replace(/\D/g, '');
      const rankHint = digits.length >= 6 ? 'KSP OFFICER' : null;
      setDetectedRole(rankHint ? 'SCRB' : null);
    } else {
      setDetectedRole(null);
    }
  }, [badgeId]);

  // Handle typing PIN and automatically submit at 6 digits
  useEffect(() => {
    if (pin.length === 6) {
      handleFormSubmit();
    }
  }, [pin]);

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

  const handleDotClick = () => {
    hiddenInputRef.current?.focus();
  };

  const handlePinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setPin(value);
  };

  const handleKeypadPress = (num: number) => {
    if (pin.length < 6) {
      setPin((prev) => prev + num);
    }
  };

  const handleBackspace = () => {
    setPin((prev) => prev.slice(0, -1));
  };

  return (
    <div className="w-full max-w-sm flex flex-col gap-4">
      {/* Officer badge icon and heading */}
      <div className="flex items-center gap-3 bg-secondary-bg/60 border border-border-color p-3 rounded-card">
        <div className="p-2 bg-[#1E6FD9]/10 rounded-full text-[#1E6FD9] animate-pulse">
          <Shield className="w-6 h-6" />
        </div>
        <div>
          <h4 className="text-[12px] font-mono uppercase text-[#A8B4CC]">Officer Registration Database</h4>
          <span className="text-[10px] text-[#6A7A96] uppercase select-none">Credentials verified via SCRB node-trust</span>
        </div>
      </div>

      {/* Inputs block */}
      <div className="flex flex-col gap-3">
        {/* Badge Input */}
        <div>
          <label className="block text-[10px] font-mono uppercase text-[#6A7A96] mb-1.5 tracking-wider">
            National Police Badge ID
          </label>
          <div className="relative">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-[#6A7A96]">
              {/* Indian flag colors ribbon style */}
              <div className="w-1.5 h-4 flex flex-col gap-0.5 mr-2">
                <div className="w-full bg-[#f48f42] h-1" />
                <div className="w-full bg-white h-1" />
                <div className="w-full bg-[#0E9E78] h-1" />
              </div>
              <Shield className="w-3.5 h-3.5" />
            </span>
            <input
              type="text"
              placeholder="e.g. SCRB-7740, IO-3921, SP-0088"
              value={badgeId}
              onChange={(e) => setBadgeId(e.target.value)}
              className="w-full pl-9 pr-20 py-2 bg-[#111D35]/80 text-[#E8EDF5] font-mono text-xs border border-border-color focus:border-[#1E6FD9] rounded-btn outline-none transition-colors"
            />
            {/* Live Role Preview Pill */}
            {detectedRole && (
              <span className="absolute right-2 top-1.5 px-2 py-0.5 bg-[#1E6FD9]/20 text-[#1E6FD9] text-[9px] font-mono rounded-full border border-[#1E6FD9]/30 flex items-center gap-1 select-none">
                <UserCheck className="w-2.5 h-2.5" />
                {detectedRole} RANK
              </span>
            )}
          </div>
        </div>

        {/* PIN Selection via Custom Dot input */}
        <div>
          <label className="block text-[10px] font-mono uppercase text-[#6A7A96] mb-1.5 tracking-wider">
            6-Digit Encryption PIN
          </label>

          {/* Hidden input to receive focus & text inputs */}
          <input
            ref={hiddenInputRef}
            type="text"
            pattern="[0-9]*"
            inputMode="numeric"
            value={pin}
            onChange={handlePinChange}
            className="absolute opacity-0 w-0 h-0 overflow-hidden"
          />

          {/* Graphical Circle Dots Bar */}
          <div 
            onClick={handleDotClick}
            className="flex justify-between items-center gap-2 px-6 py-3 bg-[#111D35]/80 border border-border-color rounded-btn cursor-pointer hover:border-[#1E6FD9]/50 transition-colors"
          >
            {[0, 1, 2, 3, 4, 5].map((idx) => {
              const filled = pin.length > idx;
              return (
                <div
                  key={idx}
                  className={`w-3.5 h-3.5 rounded-full transition-all duration-300 ${
                    filled
                      ? 'bg-[#1E6FD9] scale-110 shadow-glow-blue'
                      : 'border-2 border-slate-700 bg-transparent'
                  }`}
                />
              );
            })}
          </div>
        </div>
      </div>

      {/* Screen Pad (Custom Pinpad Grid) */}
      <div className="grid grid-cols-3 gap-2 bg-slate-950/20 p-2 border border-border-color/30 rounded-card">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((num) => (
          <button
            key={num}
            type="button"
            onClick={() => handleKeypadPress(num)}
            className="py-2.5 bg-[#111D35]/30 hover:bg-[#111D35] border border-border-color/20 text-[#A8B4CC] hover:text-white font-mono text-center hover:scale-105 active:scale-95 rounded transition-all cursor-pointer"
          >
            {num}
          </button>
        ))}
        <button
          type="button"
          onClick={handleBackspace}
          className="col-span-1 py-2.5 bg-[#C94A2A]/10 hover:bg-[#C94A2A]/20 border border-[#C94A2A]/20 text-[#C94A2A] font-mono text-center rounded transition-all cursor-pointer text-[10px] uppercase"
        >
          Clear
        </button>
        <button
          type="button"
          onClick={() => handleKeypadPress(0)}
          className="py-2.5 bg-[#111D35]/30 hover:bg-[#111D35] border border-border-color/20 text-[#A8B4CC] font-mono text-center rounded transition-all cursor-pointer"
        >
          0
        </button>
        <button
          type="button"
          onClick={handleFormSubmit}
          disabled={isSubmitting}
          className="col-span-1 py-2.5 bg-[#0e9e78]/10 hover:bg-[#0e9e78]/20 border border-[#0e9e78]/20 text-[#0e9e78] font-mono text-center rounded transition-all cursor-pointer text-[10px] uppercase"
        >
          Enter
        </button>
      </div>

      {/* Error Notices */}
      {(loginError || localErrors) && (
        <div className="flex items-start gap-2 bg-[#C94A2A]/15 border border-[#C94A2A]/30 p-2.5 rounded-btn text-xs text-[#E8EDF5] font-sans">
          <AlertCircle className="w-4 h-4 text-[#C94A2A] shrink-0 mt-0.5" />
          <span>{localErrors || loginError}</span>
        </div>
      )}

      {/* Help message */}
      <div className="text-center text-[9px] font-mono text-[#6A7A96] leading-relaxed select-none">
        LOGIN WITH YOUR KGID &amp; PIN:<br />
        BADGE ID: Your KGID (e.g. KG735408)<br />
        PIN: Last 6 digits of your KGID (e.g. 735408)
      </div>
    </div>
  );
};

export default BadgeLogin;
