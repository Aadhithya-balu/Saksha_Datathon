import React from 'react';
import { Info } from 'lucide-react';
import type { StatusBadge, StatusTone } from '../../services/intelligenceStatus';

const TONE_CLASSES: Record<StatusTone, string> = {
  live: 'bg-[#0E9E78]/15 border-[#0E9E78]/40 text-[#0E9E78]',
  warn: 'bg-amber-500/15 border-amber-500/40 text-amber-400',
  danger: 'bg-red-500/15 border-red-500/40 text-red-400',
  muted: 'bg-blue-500/10 border-blue-500/30 text-blue-300',
};

interface Props {
  badges: StatusBadge | StatusBadge[];
  /** Show the info icon (tooltip affordance) next to the label. */
  withInfo?: boolean;
  className?: string;
}

/**
 * Compact intelligence-status chip. Status is always conveyed by readable
 * text plus a tooltip — never color alone (issue 9 §25).
 */
export const IntelligenceStatusBadges: React.FC<Props> = ({ badges, withInfo = true, className = '' }) => {
  const list = Array.isArray(badges) ? badges : [badges];
  if (list.length === 0) return null;
  return (
    <span className={`inline-flex items-center gap-1.5 flex-wrap ${className}`}>
      {list.slice(0, 2).map((badge) => (
        <span
          key={badge.kind}
          title={badge.tooltip}
          aria-label={`${badge.label}: ${badge.tooltip}`}
          role="status"
          className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border font-mono text-[8.5px] font-bold uppercase tracking-wide cursor-help ${TONE_CLASSES[badge.tone]}`}
        >
          {withInfo && <Info className="w-2.5 h-2.5 shrink-0" aria-hidden="true" />}
          {badge.label}
        </span>
      ))}
    </span>
  );
};

export default IntelligenceStatusBadges;
