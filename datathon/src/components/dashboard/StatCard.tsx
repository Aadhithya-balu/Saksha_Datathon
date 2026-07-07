import React from 'react';
import KPICounter from './KPICounter';

interface StatCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  icon: React.ReactNode;
  trend: 'up' | 'down' | 'stable';
  trendValue: string;
  subtext: string;
  glowColor: 'blue' | 'teal' | 'amber' | 'coral' | 'purple' | 'indigo' | 'emerald';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  prefix = '',
  suffix = '',
  icon,
  trend,
  trendValue,
  subtext,
  glowColor
}) => {
  // Rich colors mapping from reference design system
  const colorSchemes = {
    blue: { 
      bg: 'bg-blue-500/10 border-blue-500/20', 
      iconColor: 'text-[#1E6FD9]', 
      glow: 'hover:shadow-[0_0_20px_rgba(30,111,217,0.25)] hover:border-blue-500/45' 
    },
    teal: { 
      bg: 'bg-teal-500/10 border-teal-500/20', 
      iconColor: 'text-[#0E9E78]', 
      glow: 'hover:shadow-[0_0_20px_rgba(14,158,120,0.25)] hover:border-emerald-500/45' 
    },
    amber: { 
      bg: 'bg-amber-500/10 border-amber-500/20', 
      iconColor: 'text-[#D4820A]', 
      glow: 'hover:shadow-[0_0_20px_rgba(212,130,10,0.25)] hover:border-amber-500/45' 
    },
    coral: { 
      bg: 'bg-red-500/10 border-red-500/20', 
      iconColor: 'text-[#C94A2A]', 
      glow: 'hover:shadow-[0_0_20px_rgba(201,74,42,0.25)] hover:border-red-500/45' 
    },
    purple: { 
      bg: 'bg-purple-500/10 border-purple-500/20', 
      iconColor: 'text-[#6C43CC]', 
      glow: 'hover:shadow-[0_0_20px_rgba(108,67,204,0.25)] hover:border-purple-500/45' 
    },
    indigo: { 
      bg: 'bg-indigo-500/10 border-indigo-500/20', 
      iconColor: 'text-indigo-400', 
      glow: 'hover:shadow-[0_0_20px_rgba(99,102,241,0.25)] hover:border-indigo-500/45' 
    },
    emerald: { 
      bg: 'bg-emerald-500/10 border-emerald-500/20', 
      iconColor: 'text-emerald-400', 
      glow: 'hover:shadow-[0_0_20px_rgba(16,185,129,0.25)] hover:border-emerald-500/45' 
    }
  };

  const isUp = trend === 'up';
  const isDown = trend === 'down';
  const isStable = trend === 'stable';

  const trendColor = isUp 
    ? 'text-emerald-500' 
    : isDown 
    ? 'text-rose-500' 
    : 'text-blue-500';

  return (
    <div 
      className={`p-3.5 rounded-xl border border-white/5 bg-[#0a1220]/80 backdrop-blur-md flex flex-col items-start gap-3 select-none relative overflow-hidden transition-all duration-300 ease-out cursor-pointer transform hover:-translate-y-1.5 hover:scale-[1.02] hover:rotate-x-2 hover:rotate-y-2 ${colorSchemes[glowColor].glow}`}
      style={{ transformStyle: 'preserve-3d', perspective: '800px' }}
    >
      
      {/* Icon at the top left */}
      <div 
        className={`w-9 h-9 rounded-lg flex items-center justify-center border shrink-0 transition-transform duration-300 ease-out ${colorSchemes[glowColor].bg} ${colorSchemes[glowColor].iconColor}`}
        style={{ transform: 'translateZ(15px)' }}
      >
        {icon}
      </div>

      {/* Metrics Stack */}
      <div className="w-full text-left" style={{ transform: 'translateZ(10px)' }}>
        <span className="block text-[9px] font-mono uppercase tracking-wider text-[#6A7A96] font-bold">
          {title}
        </span>
        <h3 className="text-lg md:text-xl font-mono font-extrabold text-white mt-1 leading-none">
          <KPICounter value={value} prefix={prefix} suffix={suffix} />
        </h3>
        
        {/* Trend marker wrap flex */}
        <div className="flex flex-wrap items-center gap-1.5 mt-2 text-[8px] font-mono leading-none">
          <span className={`font-bold flex items-center gap-0.5 ${trendColor}`}>
            {isUp && '▲'}
            {isDown && '▼'}
            {isStable && '•'}
            {trendValue}
          </span>
          <span className="text-[#6A7A96]">{subtext}</span>
        </div>
      </div>

      {/* Background visual diagnostics lines */}
      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default StatCard;
