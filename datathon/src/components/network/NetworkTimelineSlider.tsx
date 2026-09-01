import React, { useEffect, useMemo, useState } from 'react';
import { Calendar, Play, Pause, RotateCcw, Clock } from 'lucide-react';

interface NetworkTimelineSliderProps {
  onDateChange?: (range: [string, string]) => void;
}

const DATA_START_YEAR = 2025;
const DATA_END_YEAR = 2026;
const MIN_INDEX = 1;
const MAX_INDEX = (DATA_END_YEAR - DATA_START_YEAR + 1) * 12; // 24 months
const FULL_RANGE: [string, string] = ['2025-01-01', '2026-12-31'];

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

function monthEndDate(index: number): string {
  const offset = index - 1;
  const year = DATA_START_YEAR + Math.floor(offset / 12);
  const month = (offset % 12) + 1; // 1-based
  const lastDay = new Date(year, month, 0).getDate();
  return `${year}-${String(month).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
}

function monthLabel(index: number): string {
  const offset = index - 1;
  const year = DATA_START_YEAR + Math.floor(offset / 12);
  const month = (offset % 12) + 1;
  return `${MONTH_NAMES[month - 1]} ${String(year).slice(2)}`;
}

export const NetworkTimelineSlider: React.FC<NetworkTimelineSliderProps> = ({ onDateChange }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [step, setStep] = useState(MAX_INDEX);

  const range = useMemo<[string, string]>(() => ['2025-01-01', monthEndDate(step)], [step]);

  // Auto-play scrubs the window forward until it reaches the full range, then stops.
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setStep((s) => (s >= MAX_INDEX ? MAX_INDEX : s + 1));
    }, 900);
    return () => clearInterval(timer);
  }, [isPlaying]);

  useEffect(() => {
    if (step >= MAX_INDEX) setIsPlaying(false);
  }, [step]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setStep(val);
    onDateChange?.(['2025-01-01', monthEndDate(val)]);
  };

  const handleReset = () => {
    setStep(MAX_INDEX);
    setIsPlaying(false);
    onDateChange?.(FULL_RANGE);
  };

  return (
    <div className="bg-[var(--bg-primary)] p-3 rounded-card border border-[var(--border-secondary)] font-mono flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-bold text-[var(--text-primary)] uppercase">
          <Calendar className="w-4 h-4 text-[var(--accent-blue)]" />
          <span>Network Relationship Timeline scrubber</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-1.5 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/20 border border-[var(--border-secondary)] rounded-btn text-[var(--text-primary)] text-xs cursor-pointer"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleReset}
            className="p-1.5 bg-[var(--bg-tertiary)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border-secondary)] rounded-btn text-[var(--text-muted)] hover:text-[var(--text-primary)] text-xs cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Clock className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        <input
          type="range"
          min={MIN_INDEX}
          max={MAX_INDEX}
          value={step}
          onChange={handleSliderChange}
          className="flex-1 accent-[var(--accent-blue)] cursor-pointer"
        />
        <span className="text-xs font-bold text-[#60A5FA] min-w-[84px] text-right uppercase">
          {monthLabel(step)}
        </span>
      </div>
      <div className="text-[10px] text-[var(--text-muted)] tracking-wider uppercase">
        Window: Jan 25 &rarr; {monthLabel(step)} ({range[1]} end-of-month)
      </div>
    </div>
  );
};

export default NetworkTimelineSlider;