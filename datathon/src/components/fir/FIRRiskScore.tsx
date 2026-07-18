import React from 'react';
import { ShieldCheck, AlertCircle, Cpu, Fingerprint } from 'lucide-react';

interface FIRRiskScoreProps {
  score: number;
  reasons: string[];
}

export const FIRRiskScore: React.FC<FIRRiskScoreProps> = ({ score, reasons }) => {
  // SVG circular path math
  const radius = 42;
  const strokeWidth = 6.5;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Determine threat levels
  let ratingLabel = 'MODERATE THREAT';
  let ratingColor = 'text-emerald-400';
  let gaugeColor = '#0E9E78'; // Green
  let borderGlow = 'shadow-emerald-500/10';

  if (score >= 75) {
    ratingLabel = 'CRITICAL RISKS';
    ratingColor = 'text-red-500 font-extrabold animate-pulse';
    gaugeColor = '#C94A2A'; // Red
    borderGlow = 'shadow-red-500/20';
  } else if (score >= 50) {
    ratingLabel = 'HIGH THREAT';
    ratingColor = 'text-amber-500 font-bold';
    gaugeColor = '#D4820A'; // Orange/Amber
    borderGlow = 'shadow-amber-500/15';
  }

  return (
    <div className={`bg-[#111D35]/30 border border-border-color p-5 rounded-card flex flex-col justify-between overflow-hidden relative shadow-lg ${borderGlow}`}>
      {/* Cyber radar scan aesthetic sweep line */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#1E6FD9]/5 to-transparent pointer-events-none -z-10 h-1/2 animate-[pulse_3s_infinite]" />

      <div className="flex items-center justify-between border-b border-slate-900 pb-3 mb-4">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-red-500 animate-spin-slow" />
          <span className="text-[10px] font-bold text-[#E8EDF5] uppercase tracking-wider">AI Risk & Threat Assessment</span>
        </div>
        <div className="flex items-center gap-1 text-[7px] font-mono text-[#6A7A96]">
          <Fingerprint className="w-3 h-3 text-[#1E6FD9]" />
          <span>INFERENCE MODEL: RULE-SQL-V2</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-12 gap-5 items-center">
        {/* Left Side: SVG gauge */}
        <div className="sm:col-span-5 flex flex-col items-center justify-center">
          <div className="relative w-28 h-28 flex items-center justify-center">
            {/* SVG circle meter */}
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              {/* Back track */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                className="stroke-slate-900 fill-none"
                strokeWidth={strokeWidth}
              />
              {/* Progress gauge */}
              <circle
                cx="50"
                cy="50"
                r={radius}
                className="fill-none transition-all duration-1000 ease-out"
                strokeWidth={strokeWidth}
                stroke={gaugeColor}
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
              />
            </svg>
            {/* Inside circular value */}
            <div className="absolute text-center select-none font-mono">
              <span className="text-xl font-extrabold text-white block leading-none">{score}%</span>
              <span className="text-[7.5px] text-[#6A7A96] block uppercase mt-1.5 tracking-wider">Severity</span>
            </div>
          </div>
          <span className={`text-[9.5px] uppercase tracking-wider mt-2.5 ${ratingColor}`}>
            {ratingLabel}
          </span>
        </div>

        {/* Right Side: Threat reasons */}
        <div className="sm:col-span-7 space-y-2.5">
          <span className="text-[8.5px] text-slate-500 uppercase tracking-widest block font-bold">Threat Factors Detected</span>
          
          <div className="space-y-1.5 max-h-[140px] overflow-y-auto custom-scrollbar pr-1">
            {reasons.length > 0 ? reasons.map((reason, idx) => (
              <div key={idx} className="flex items-start gap-2 text-[9.5px] text-[#A8B4CC]">
                <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                <span className="font-mono leading-relaxed">{reason}</span>
              </div>
            )) : (
              <div className="flex items-start gap-2 text-[9.5px] text-emerald-400">
                <ShieldCheck className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span className="font-mono leading-relaxed">No critical threat vectors registered. Standard investigation timeline.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default FIRRiskScore;
