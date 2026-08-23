import React, { useEffect, useState } from 'react';
import { useMapStore } from '../../store/mapStore';
import { Sun, Moon, Clock, Play, Pause } from 'lucide-react';

export const TimeSlider: React.FC = () => {
  const { timeOfDay, setTimeOfDay } = useMapStore();
  const [isPlaying, setIsPlaying] = useState(false);

  // Play animation simulation: cycle hours
  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    if (isPlaying) {
      timer = setInterval(() => {
        setTimeOfDay((timeOfDay + 1) % 24);
      }, 850);
    }
    return () => clearInterval(timer);
  }, [isPlaying, timeOfDay, setTimeOfDay]);

  const getPeriodLabel = (h: number) => {
    if (h >= 5 && h < 12) return 'Morning Watch';
    if (h >= 12 && h < 17) return 'Afternoon Patrol';
    if (h >= 17 && h < 21) return 'Evening Peak Shift';
    return 'Night Beat Operation';
  };

  const padTime = (h: number) => {
    const period = h >= 12 ? 'PM' : 'AM';
    const displayHour = h % 12 === 0 ? 12 : h % 12;
    return `${displayHour.toString().padStart(2, '0')}:00 ${period}`;
  };

  return (
    <div className="w-full bg-secondary-bg/80 backdrop-blur-md border border-border-color p-4 rounded-card flex flex-col md:flex-row items-center gap-4 select-none">
      
      {/* Play/Pause controls */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className={`p-2 rounded-full border cursor-pointer transition-all ${
            isPlaying 
              ? 'bg-[var(--accent-teal)]/10 border-[var(--accent-teal)] text-[var(--accent-teal)] shadow-glow-teal' 
              : 'bg-[var(--accent-blue)]/15 border-[var(--accent-blue)] text-[var(--accent-blue)]'
          }`}
        >
          {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
        </button>
        
        <div className="flex flex-col text-left min-w-[140px]">
          <span className="text-xs font-mono font-bold text-[var(--text-primary)] flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-[var(--accent-blue)]" />
            {padTime(timeOfDay)}
          </span>
          <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase mt-0.5">
            {getPeriodLabel(timeOfDay)}
          </span>
        </div>
      </div>

      {/* Slider track bar */}
      <div className="flex-1 w-full flex items-center gap-3">
        <Moon className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
        
        <div className="flex-grow relative flex items-center">
          <input
            type="range"
            min="0"
            max="23"
            value={timeOfDay}
            onChange={(e) => setTimeOfDay(parseInt(e.target.value))}
            className="w-full h-1.5 bg-[var(--bg-elevated)] rounded-lg appearance-none cursor-pointer accent-[var(--accent-blue)] focus:outline-none"
          />
          
          {/* Tick markings overlay */}
          <div className="absolute top-4 left-0 right-0 flex justify-between px-1 text-[8px] font-mono text-[var(--text-muted)] pointer-events-none">
            <span>00:00</span>
            <span>06:00</span>
            <span>12:00</span>
            <span>18:00</span>
            <span>23:00</span>
          </div>
        </div>

        <Sun className="w-3.5 h-3.5 text-amber-500 shrink-0 select-none" />
      </div>

      {/* Quick Jump buttons */}
      <div className="hidden lg:flex items-center gap-2 border-l border-border-color pl-4">
        {[8, 14, 20].map((hour) => (
          <button
            key={hour}
            onClick={() => { setIsPlaying(false); setTimeOfDay(hour); }}
            className={`px-2 py-1 text-[9px] font-mono rounded border transition-colors cursor-pointer ${
              timeOfDay === hour
                ? 'bg-[var(--accent-blue)] border-[var(--accent-blue)] text-[var(--text-primary)]'
                : 'bg-[var(--bg-tertiary)] border-border-color text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
            }`}
          >
            {hour === 8 ? '08:00 AM' : hour === 14 ? '02:00 PM' : '08:00 PM'}
          </button>
        ))}
      </div>

    </div>
  );
};

export default TimeSlider;
