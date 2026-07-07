import React, { useState } from 'react';
import { LayoutGrid, Flame } from 'lucide-react';

interface HeatmapCell {
  day: string;
  hour: string;
  intensity: number; // 0 to 100
  cases: number;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'];

// Create mock data for spatiotemporal matrix
const HEATMAP_DATA: HeatmapCell[] = [];
DAYS.forEach(day => {
  HOURS.forEach(hour => {
    // Generate values representing weekend night surges
    let base = 25;
    if (day === 'Fri' || day === 'Sat') {
      if (hour === '00:00' || hour === '20:00') base = 85;
    } else if (hour === '12:00' || hour === '16:00') {
      base = 60; // daytime commercial theft
    }
    
    // add small noise
    const cases = Math.floor(base + Math.random() * 15);
    HEATMAP_DATA.push({
      day,
      hour,
      intensity: cases,
      cases
    });
  });
});

export const SpatiotemporalHeatmap: React.FC = () => {
  const [hoveredCell, setHoveredCell] = useState<HeatmapCell | null>(null);

  const getCellColor = (intensity: number) => {
    if (intensity < 35) return 'bg-blue-950/20 border-blue-900/10 text-blue-400';
    if (intensity < 60) return 'bg-[#1E6FD9]/20 border-[#1E6FD9]/30 text-blue-300';
    if (intensity < 80) return 'bg-[#6C43CC]/30 border-[#6C43CC]/40 text-purple-300';
    return 'bg-red-500/25 border-red-500/40 text-rose-300 shadow-[inset_0_0_8px_rgba(239,68,68,0.2)] animate-pulse';
  };

  return (
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none font-mono relative">
      
      {/* Header */}
      <div className="flex justify-between items-center mb-3">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Flame className="w-4 h-4 text-[#C94A2A] animate-pulse" />
            Spatiotemporal Incident Heatmap
          </h4>
          <span className="text-[8px] text-slate-500 uppercase">Hourly Density Matrix (Day of Week vs. Hour)</span>
        </div>
      </div>

      {/* Grid Canvas */}
      <div className="flex-grow flex flex-col justify-center py-2">
        <div className="grid grid-cols-8 gap-1.5 text-[8.5px]">
          
          {/* Top X-Axis labels */}
          <div />
          {HOURS.map(hour => (
            <div key={hour} className="text-center text-slate-500 font-semibold uppercase">{hour}</div>
          ))}

          {/* Rows mapping */}
          {DAYS.map(day => (
            <React.Fragment key={day}>
              {/* Row header (Y-Axis) */}
              <div className="text-slate-500 font-bold uppercase py-1.5">{day}</div>
              
              {/* Heatmap cells */}
              {HOURS.map(hour => {
                const cell = HEATMAP_DATA.find(c => c.day === day && c.hour === hour) || { day, hour, intensity: 10, cases: 10 };
                return (
                  <div
                    key={`${day}-${hour}`}
                    onMouseEnter={() => setHoveredCell(cell)}
                    onMouseLeave={() => setHoveredCell(null)}
                    className={`py-2 text-center rounded border transition-all duration-150 cursor-pointer ${getCellColor(cell.intensity)}`}
                  >
                    {cell.cases}
                  </div>
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Footer Info / Tooltip box */}
      <div className="flex justify-between items-center text-[8.5px] text-slate-500 uppercase tracking-widest pt-2 border-t border-slate-900 min-h-[22px]">
        {hoveredCell ? (
          <span className="text-white font-bold animate-[fadeIn_0.15s_ease-out]">
            {hoveredCell.day} @ {hoveredCell.hour} $\rightarrow$ {hoveredCell.cases} Cases Tracked
          </span>
        ) : (
          <span>Hover grids for coordinates details</span>
        )}
        <span className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" />
          Critical Density Peaks
        </span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default SpatiotemporalHeatmap;
