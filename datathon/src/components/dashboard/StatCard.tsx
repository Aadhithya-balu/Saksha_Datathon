import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
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
  onClick?: () => void;
}

const ACCENTS: Record<StatCardProps['glowColor'], string> = {
  blue: 'var(--accent-blue)',
  teal: 'var(--accent-teal)',
  amber: 'var(--accent-amber)',
  coral: 'var(--accent-coral)',
  purple: 'var(--accent-purple)',
  indigo: '#6366f1',
  emerald: '#10b981',
};

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  prefix = '',
  suffix = '',
  icon,
  trend,
  trendValue,
  subtext,
  glowColor,
  onClick
}) => {
  const accent = ACCENTS[glowColor] ?? ACCENTS.blue;

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendTone =
    trend === 'up'
      ? 'var(--tone-success-text)'
      : trend === 'down'
      ? 'var(--tone-error-text)'
      : 'var(--tone-info-text)';
  const interactive = Boolean(onClick);

  const content = (
    <>
      <div className="flex items-start justify-between w-full">
        <span className="text-[13px] font-medium text-[var(--text-secondary)]">{title}</span>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ color: accent, backgroundColor: `color-mix(in srgb, ${accent} 12%, transparent)` }}
        >
          {icon}
        </div>
      </div>

      <h3 className="text-2xl font-bold text-[var(--text-primary)] leading-none tracking-tight">
        <KPICounter value={value} prefix={prefix} suffix={suffix} />
      </h3>

      <div className="flex items-center gap-2 text-xs mt-auto">
        <span
          className="inline-flex items-center gap-1 font-semibold px-1.5 py-0.5 rounded"
          style={{ color: trendTone, backgroundColor: `color-mix(in srgb, ${trendTone} 10%, transparent)` }}
        >
          <TrendIcon className="w-3 h-3" />
          {trendValue}
        </span>
        <span className="text-[var(--text-muted)] truncate">{subtext}</span>
      </div>

      {/* subtle bottom accent */}
      <div
        aria-hidden="true"
        className="absolute bottom-0 left-0 right-0 h-px"
        style={{ backgroundColor: `color-mix(in srgb, ${accent} 35%, transparent)` }}
      />
    </>
  );

  if (interactive) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="sk-panel p-4 flex flex-col gap-3 select-none relative overflow-hidden transition-all duration-200 cursor-pointer hover:border-[var(--accent-blue)]/60 hover:-translate-y-0.5 text-left w-full"
      >
        {content}
      </button>
    );
  }

  return (
    <div className="sk-panel p-4 flex flex-col gap-3 select-none relative overflow-hidden transition-all duration-200">
      {content}
    </div>
  );
};

export default StatCard;
