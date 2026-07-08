import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, ReferenceLine, Tooltip } from 'recharts';

interface ForecastDataPoint {
  day: string;
  historical?: number;
  predicted?: number;
  anomalyLevel?: number;
}

const FORECAST_SERIES: ForecastDataPoint[] = [
  { day: 'T-10d', historical: 145 },
  { day: 'T-8d', historical: 152 },
  { day: 'T-6d', historical: 148 },
  { day: 'T-4d', historical: 160 },
  { day: 'T-2d', historical: 172 },
  { day: 'TODAY', historical: 185, predicted: 185 }, // crossover point
  { day: 'P+2d', predicted: 191 },
  { day: 'P+4d', predicted: 198 },
  { day: 'P+6d', predicted: 215 }, // predicted spikes due to festivals weekend
  { day: 'P+8d', predicted: 202 },
  { day: 'P+10d', predicted: 210 },
  { day: 'P+12d', predicted: 226 },
  { day: 'P+14d', predicted: 238 }
];

export const ForecastChart: React.FC = () => {
  return (
    <div className="w-full h-[280px] bg-[#111D35]/30 border border-border-color p-4 rounded-card relative overflow-hidden flex flex-col justify-between">
      
      {/* Target headers info */}
      <div className="flex justify-between items-center mb-3 font-mono select-none">
        <div>
          <span className="text-[10px] text-[#D4820A] uppercase font-bold tracking-wider">
            AI PREDICTIVE TIMELINE
          </span>
          <h4 className="text-[12px] font-bold text-white mt-0.5">30-Day Operational Forecast</h4>
        </div>
        <div className="flex items-center gap-3 text-[8.5px]">
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-1 bg-[#1E6FD9]" />
            <span className="text-[#A8B4CC]">HISTORICAL</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2.5 h-1 border-t border-dashed border-sky-400" />
            <span className="text-[#A8B4CC]">PREDICTED</span>
          </div>
        </div>
      </div>

      {/* Chart render core */}
      <div className="flex-1 w-full text-xs font-mono">
        <ResponsiveContainer width="100%" height="95%">
          <AreaChart data={FORECAST_SERIES} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="histGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1E6FD9" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#1E6FD9" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#80b3ff" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#80b3ff" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />

            <XAxis
              dataKey="day"
              stroke="#6A7A96"
              tickLine={false}
              axisLine={false}
              dy={6}
              style={{ fontSize: 8, fill: '#6A7A96' }}
            />
            <YAxis
              stroke="#6A7A96"
              tickLine={false}
              axisLine={false}
              dx={-6}
              style={{ fontSize: 8, fill: '#6A7A96' }}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(11, 20, 38, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '6px',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '9px',
              }}
            />

            {/* Crossover Line indicator */}
            <ReferenceLine x="TODAY" stroke="rgba(201, 74, 42, 0.5)" strokeWidth="1" strokeDasharray="2 2" />

            {/* Historical Series Filled */}
            <Area
              type="monotone"
              dataKey="historical"
              stroke="#1E6FD9"
              fillOpacity={1}
              fill="url(#histGrad)"
              strokeWidth={1.8}
            />

            {/* Future Predicted Series Dotted Line */}
            <Area
              type="monotone"
              dataKey="predicted"
              stroke="#0ea5e9"
              strokeDasharray="4 4"
              fillOpacity={1}
              fill="url(#predGrad)"
              strokeWidth={1.8}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Diagonal grid overlay */}
      <div className="absolute inset-0 chart-diagonal-grid opacity-10 pointer-events-none -z-10" />
    </div>
  );
};
export default ForecastChart;
