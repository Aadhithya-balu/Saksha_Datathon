import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useAppStore } from '../../store/appStore';
import { useThemePalettes, tooltipStyle } from '../../theme';

interface TrendDataPoint {
  month: string;
  totalCrimes: number;
  solvedCrimes: number;
}

interface TrendChartProps {
  data?: TrendDataPoint[];
}

export const TrendChart: React.FC<TrendChartProps> = ({ data = [] }) => {
  const theme = useAppStore((s) => s.theme);
  const palette = useThemePalettes();
  const c = palette.chart;
  const maxY = Math.max(...data.map((item) => item.totalCrimes), 1);

  return (
    <div className="sk-panel sk-panel-pad w-full h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h4 className="sk-panel-title">Crime Trend</h4>
        <div className="flex items-center gap-4 text-xs text-[var(--text-secondary)]">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-[3px] rounded-full" style={{ backgroundColor: c.series[4] }} />
            <span>Total Cases</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-[3px] rounded-full" style={{ backgroundColor: c.series[1] }} />
            <span>Solved</span>
          </div>
        </div>
      </div>

      <div className="flex-grow w-full min-h-[170px]">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="totalCrimesGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={c.series[4]} stopOpacity={0.22} />
                  <stop offset="95%" stopColor={c.series[4]} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="solvedCrimesGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={c.series[1]} stopOpacity={0.22} />
                  <stop offset="95%" stopColor={c.series[1]} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={c.grid} vertical={false} />
              <XAxis dataKey="month" tickLine={false} axisLine={false} dy={6} tick={{ fill: c.axis, fontSize: 11.5 }} />
              <YAxis
                tickLine={false}
                axisLine={false}
                dx={-4}
                domain={[0, Math.ceil(maxY * 1.2)]}
                tick={{ fill: c.axis, fontSize: 11.5 }}
              />
              <Tooltip contentStyle={tooltipStyle(theme)} cursor={{ stroke: c.axis, strokeDasharray: '3 3', opacity: 0.4 }} />
              <Area type="monotone" dataKey="totalCrimes" stroke={c.series[4]} fill="url(#totalCrimesGrad)" strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2 }} name="Total Cases" />
              <Area type="monotone" dataKey="solvedCrimes" stroke={c.series[1]} fill="url(#solvedCrimesGrad)" strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2 }} name="Solved" />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-[var(--text-muted)] border border-dashed border-[var(--border-primary)] rounded-lg">
            No trend data available for the selected filters
          </div>
        )}
      </div>
    </div>
  );
};

export default TrendChart;
