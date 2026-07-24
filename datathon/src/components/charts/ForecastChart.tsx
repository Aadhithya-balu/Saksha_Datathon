import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Sparkles, HelpCircle } from 'lucide-react';

interface ForecastDataPoint {
  day: string;
  value: number;
  type: 'historical' | 'predicted' | 'today';
  color: string;
}

const FORECAST_SERIES: ForecastDataPoint[] = [
  { day: 'T-10d', value: 145, type: 'historical', color: '#1E6FD9' },
  { day: 'T-8d', value: 152, type: 'historical', color: '#1E6FD9' },
  { day: 'T-6d', value: 148, type: 'historical', color: '#1E6FD9' },
  { day: 'T-4d', value: 160, type: 'historical', color: '#1E6FD9' },
  { day: 'T-2d', value: 172, type: 'historical', color: '#1E6FD9' },
  { day: 'TODAY', value: 185, type: 'today', color: '#0E9E78' },
  { day: 'P+2d', value: 191, type: 'predicted', color: '#0ea5e9' },
  { day: 'P+4d', value: 198, type: 'predicted', color: '#0ea5e9' },
  { day: 'P+6d', value: 215, type: 'predicted', color: '#0ea5e9' },
  { day: 'P+8d', value: 202, type: 'predicted', color: '#0ea5e9' },
  { day: 'P+10d', value: 210, type: 'predicted', color: '#0ea5e9' },
  { day: 'P+12d', value: 226, type: 'predicted', color: '#0ea5e9' },
  { day: 'P+14d', value: 238, type: 'predicted', color: '#0ea5e9' }
];

export const ForecastChart: React.FC = () => {
  return (
    <div className="w-full h-[280px] bg-[var(--bg-tertiary)]/30 border border-[var(--border-primary)] p-4 rounded-lg relative overflow-hidden flex flex-col justify-between font-mono">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2 select-none">
        <div>
          <span className="text-[10px] text-[var(--accent-amber)] uppercase font-bold tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-[var(--accent-amber)]" />
            AI PREDICTIVE TIMELINE
          </span>
          <h4 className="text-[12px] font-bold text-[var(--text-primary)] mt-0.5">14-Day Forecast Model</h4>
        </div>
      </div>

      {/* Area Chart */}
      <div className="flex-grow w-full min-h-[170px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={FORECAST_SERIES} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="historicalGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#1E6FD9" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#1E6FD9" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="day" stroke="#A8B4CC" tickLine={false} axisLine={false} dy={6} style={{ fill: 'var(--text-primary)', fontSize: '9px', fontWeight: 'bold' }} />
            <YAxis stroke="#A8B4CC" tickLine={false} axisLine={false} dx={-6} style={{ fill: 'var(--text-primary)', fontSize: '10px', fontWeight: 'bold' }} />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(11, 20, 38, 0.96)',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                borderRadius: '6px',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '11px',
                color: '#E8EDF5',
              }}
              formatter={(value: number) => [`${value} Incidents`, 'Cases']}
              labelStyle={{ color: '#E8EDF5', fontWeight: 700 }}
            />
            <Area type="monotone" dataKey="value" stroke="#0ea5e9" fillOpacity={1} fill="url(#forecastGrad)" strokeWidth={2} dot={(props: any) => {
              const { cx, cy, payload } = props;
              const fillColor = payload.type === 'today' ? '#0E9E78' : payload.type === 'predicted' ? '#0ea5e9' : '#1E6FD9';
              return <circle cx={cx} cy={cy} r={3} fill={fillColor} stroke="none" />;
            }} activeDot={{ r: 5, strokeWidth: 0 }} name="Incidents" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[8px] text-[#a8b4cc] uppercase font-bold tracking-wider pt-2 border-t border-[var(--border-primary)] select-none">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#1E6FD9]" /> HISTORICAL</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#0E9E78]" /> TODAY</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#0ea5e9]" /> AI PREDICTED</span>
        <span className="ml-auto flex items-center gap-1">
          <HelpCircle className="w-3 h-3 text-[var(--accent-amber)]" />
          Confidence: 94.6%
        </span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default ForecastChart;
