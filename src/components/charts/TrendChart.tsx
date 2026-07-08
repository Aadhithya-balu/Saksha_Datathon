import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';

interface TrendDataPoint {
  month: string;
  totalCrimes: number;
  solvedCrimes: number;
}

const CRIME_TREND_DATA: TrendDataPoint[] = [
  { month: 'Dec 2023', totalCrimes: 4500, solvedCrimes: 2800 },
  { month: 'Jan 2024', totalCrimes: 5200, solvedCrimes: 3100 },
  { month: 'Feb 2024', totalCrimes: 4900, solvedCrimes: 2900 },
  { month: 'Mar 2024', totalCrimes: 5800, solvedCrimes: 3500 },
  { month: 'Apr 2024', totalCrimes: 6200, solvedCrimes: 3900 },
  { month: 'May 2024', totalCrimes: 7892, solvedCrimes: 4651 }
];

export const TrendChart: React.FC = () => {
  return (
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none">
      
      {/* Title block */}
      <div className="flex justify-between items-center mb-3 font-mono">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider">
            Crime Trend (Last 6 Months)
          </h4>
        </div>
        <div className="flex items-center gap-3 text-[9px]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-1.5 rounded-full bg-[#6C43CC]" />
            <span className="text-[#A8B4CC] uppercase">Total Crimes</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-1.5 rounded-full bg-[#0E9E78]" />
            <span className="text-[#A8B4CC] uppercase">Solved Crimes</span>
          </div>
        </div>
      </div>

      {/* Chart render core */}
      <div className="flex-grow w-full min-h-[170px] text-[8.5px] font-mono">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={CRIME_TREND_DATA} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="totalCrimesGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6C43CC" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#6C43CC" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="solvedCrimesGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#0E9E78" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#0E9E78" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />

            <XAxis
              dataKey="month"
              stroke="#6A7A96"
              tickLine={false}
              axisLine={false}
              dy={6}
              style={{ fill: '#6A7A96' }}
            />
            <YAxis
              stroke="#6A7A96"
              tickLine={false}
              axisLine={false}
              dx={-6}
              domain={[0, 9000]}
              style={{ fill: '#6A7A96' }}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: 'rgba(11, 20, 38, 0.95)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '6px',
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '9px',
                color: '#fff',
              }}
              cursor={{ stroke: 'rgba(255,255,255,0.08)' }}
            />

            {/* Total Crimes (Purple Area) */}
            <Area
              type="monotone"
              dataKey="totalCrimes"
              stroke="#6C43CC"
              fillOpacity={1}
              fill="url(#totalCrimesGrad)"
              strokeWidth={2}
              dot={{ r: 3, fill: '#6C43CC', strokeWidth: 0 }}
              activeDot={{ r: 5, strokeWidth: 0 }}
              name="Total Crimes"
            />

            {/* Solved Crimes (Green Area) */}
            <Area
              type="monotone"
              dataKey="solvedCrimes"
              stroke="#0E9E78"
              fillOpacity={1}
              fill="url(#solvedCrimesGrad)"
              strokeWidth={2}
              dot={{ r: 3, fill: '#0E9E78', strokeWidth: 0 }}
              activeDot={{ r: 5, strokeWidth: 0 }}
              name="Solved Crimes"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default TrendChart;
