import React, { useState } from 'react';
import { Calendar, Play, Pause, RotateCcw, Clock } from 'lucide-react';

interface NetworkTimelineSliderProps {
  onDateChange?: (range: [string, string]) => void;
}

export const NetworkTimelineSlider: React.FC<NetworkTimelineSliderProps> = ({ onDateChange }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [step, setStep] = useState(12);

  const months = [
    'Jan 25', 'Feb 25', 'Mar 25', 'Apr 25', 'May 25', 'Jun 25',
    'Jul 25', 'Aug 25', 'Sep 25', 'Oct 25', 'Nov 25', 'Dec 25',
  ];

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setStep(val);
    onDateChange?.(['2025-01-01', `2025-${val < 10 ? '0' + val : val}-30`]);
  };

  return (
    <div className="bg-[#050912] p-3 rounded-card border border-white/10 font-mono flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-bold text-white uppercase">
          <Calendar className="w-4 h-4 text-[#1E6FD9]" />
          <span>Network Relationship Timeline scrubber</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-1.5 bg-[#111D35] hover:bg-[#1E6FD9]/20 border border-white/10 rounded-btn text-white text-xs cursor-pointer"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={() => setStep(12)}
            className="p-1.5 bg-[#111D35] hover:bg-white/10 border border-white/10 rounded-btn text-[#8A99AD] hover:text-white text-xs cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Clock className="w-3.5 h-3.5 text-[#6A7A96]" />
        <input
          type="range"
          min={1}
          max={12}
          value={step}
          onChange={handleSliderChange}
          className="flex-1 accent-[#1E6FD9] cursor-pointer"
        />
        <span className="text-xs font-bold text-[#60A5FA] min-w-[60px] text-right uppercase">
          {months[step - 1] || 'Dec 25'}
        </span>
      </div>
    </div>
  );
};

export default NetworkTimelineSlider;
