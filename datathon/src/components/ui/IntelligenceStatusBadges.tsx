import React, { useState, useRef, useEffect } from 'react';
import { Info, X, ShieldAlert, CheckCircle2, AlertTriangle, Database } from 'lucide-react';
import type { StatusBadge, StatusTone } from '../../services/intelligenceStatus';

const TONE_CLASSES: Record<StatusTone, string> = {
  live: 'bg-[#0E9E78]/15 border-[#0E9E78]/40 text-[#0E9E78] hover:bg-[#0E9E78]/25',
  warn: 'bg-amber-500/15 border-amber-500/40 text-amber-400 hover:bg-amber-500/25',
  danger: 'bg-red-500/15 border-red-500/40 text-red-400 hover:bg-red-500/25',
  muted: 'bg-blue-500/10 border-blue-500/30 text-blue-300 hover:bg-blue-500/20',
};

const TONE_ICONS: Record<StatusTone, React.ReactNode> = {
  live: <CheckCircle2 className="w-3.5 h-3.5 text-[#0E9E78]" />,
  warn: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
  danger: <ShieldAlert className="w-3.5 h-3.5 text-red-400" />,
  muted: <Database className="w-3.5 h-3.5 text-blue-300" />,
};

interface Props {
  badges: StatusBadge | StatusBadge[];
  /** Show the info icon (tooltip affordance) next to the label. */
  withInfo?: boolean;
  className?: string;
}

/**
 * Compact intelligence-status chip. Status is conveyed by readable
 * text, a hover tooltip, and an interactive popover card on click.
 */
export const IntelligenceStatusBadges: React.FC<Props> = ({ badges, withInfo = true, className = '' }) => {
  const [openBadge, setOpenBadge] = useState<string | null>(null);
  const containerRef = useRef<HTMLSpanElement>(null);

  // Close popover when clicking outside or pressing Escape
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenBadge(null);
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpenBadge(null);
    };

    if (openBadge) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [openBadge]);

  const list = Array.isArray(badges) ? badges : [badges];
  if (list.length === 0) return null;

  return (
    <span ref={containerRef} className={`inline-flex items-center gap-1.5 flex-wrap relative ${className}`}>
      {list.slice(0, 2).map((badge) => {
        const isOpen = openBadge === badge.kind;
        return (
          <div key={badge.kind} className="relative inline-block">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setOpenBadge(isOpen ? null : badge.kind);
              }}
              title={badge.tooltip}
              aria-label={`${badge.label}: ${badge.tooltip}`}
              role="status"
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border font-mono text-[8.5px] font-bold uppercase tracking-wide cursor-pointer transition-all select-none ${TONE_CLASSES[badge.tone]} ${isOpen ? 'ring-1 ring-white/30' : ''}`}
            >
              {withInfo && <Info className="w-2.5 h-2.5 shrink-0" aria-hidden="true" />}
              <span>{badge.label}</span>
            </button>

            {/* INTERACTIVE POPOVER CARD ON CLICK */}
            {isOpen && (
              <div 
                className="absolute right-0 top-full mt-2 w-72 sm:w-80 p-3 bg-[var(--bg-secondary,#0F172A)] border border-[var(--border-color,#334155)] rounded-lg shadow-2xl z-50 font-sans text-left select-none animate-in fade-in zoom-in-95 duration-150"
                style={{ backdropFilter: 'blur(12px)', backgroundColor: 'rgba(15, 23, 42, 0.96)' }}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-white/10">
                  <div className="flex items-center gap-1.5">
                    {TONE_ICONS[badge.tone]}
                    <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-white">
                      {badge.label} Status
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setOpenBadge(null)}
                    className="text-gray-400 hover:text-white p-0.5 rounded hover:bg-white/10 transition-colors cursor-pointer"
                    title="Close"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed font-normal">
                  {badge.tooltip}
                </p>
                <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-[9px] font-mono text-slate-400">
                  <span>SAKSHA Intelligence Provenance</span>
                  <button
                    type="button"
                    onClick={() => setOpenBadge(null)}
                    className="text-sky-400 hover:text-sky-300 font-semibold cursor-pointer underline"
                  >
                    Got it
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </span>
  );
};

export default IntelligenceStatusBadges;
