import React from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Sparkles, HelpCircle } from 'lucide-react';
import { useAppStore } from '../../store/appStore';
import { useThemePalettes, tooltipStyle } from '../../theme';

interface ForecastDataPoint {
  day: string;
  value: number;
  type: 'historical' | 'predicted' | 'today';
}

const FORECAST_SERIES: ForecastDataPoint[] = [
  { day: 'T-10d', value: 145, type: 'historical' },
  { day: 'T-8d', value: 152, type: 'historical' },
  { day: 'T-6d', value: 148, type: 'historical' },
  { day: 'T-4d', value: 160, type: 'historical' },
  { day: 'T-2d', value: 172, type: 'historical' },
  { day: 'Today', value: 185, type: 'today' },
  { day: 'P+2d', value: 191, type: 'predicted' },
  { day: 'P+4d', value: 198, type: 'predicted' },
  { day: 'P+6d', value: 215, type: 'predicted' },
  { day: 'P+8d', value: 202, type: 'predicted' },
  { day: 'P+10d', value: 210, type: 'predicted' },
  { day: 'P+12d', value: 226, type: 'predicted' },
  { day: 'P+14d', value: 238, type: 'predicted' },
];

export const ForecastChart: React.FC = () => {
  const theme = useAppStore((s) => s.theme);
  const palette = useThemePalettes();
  const c = palette.chart;
  const histColor = c.series[0];
  const todayColor = c.series[1];
  const predColor = c.series[5];

  return (
    <div className="w-full bg-[var(--bg-tertiary)]/40 border border-border-color p-4 rounded-card relative overflow-hidden flex flex-col justify-between h-[360px] select-none">
      <div className="flex justify-between items-center mb-1">
        <div>
          <span className="text-[10px] font-mono font-bold text-[var(--accent-purple)] uppercase flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            AI Predictive Timeline
          </span>
          <h4 className="text-xs font-semibold text-[var(--text-primary)] mt-0.5">14-Day Forecast Projection</h4>
        </div>
      </div>

      <div className="flex-1 w-full min-h-[200px] my-auto">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={FORECAST_SERIES} margin={{ top: 10, right: 10, left: -18, bottom: 0 }}>
            <defs>
              <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={predColor} stopOpacity={0.25} />
                <stop offset="95%" stopColor={predColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="day" tickLine={false} axisLine={false} dy={6} tick={{ fill: c.axis, fontSize: 10.5 }} interval={1} />
            <YAxis tickLine={false} axisLine={false} dx={-4} tick={{ fill: c.axis, fontSize: 10.5 }} />
            <Tooltip
              contentStyle={tooltipStyle(theme)}
              formatter={(value: number) => [`${value} incidents`, 'Forecast']}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={predColor}
              fillOpacity={1}
              fill="url(#forecastGrad)"
              strokeWidth={2}
              dot={(props: any) => {
                const { cx, cy, payload } = props;
                const fillColor =
                  payload.type === 'today' ? todayColor : payload.type === 'predicted' ? predColor : histColor;
                return <circle key={payload.day} cx={cx} cy={cy} r={3} fill={fillColor} stroke="none" />;
              }}
              activeDot={{ r: 5, strokeWidth: 2 }}
              name="Incidents"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-[10px] font-mono text-[var(--text-muted)] pt-2 border-t border-[var(--border-muted)] mt-1">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: histColor }} /> Historical</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: todayColor }} /> Today</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: predColor }} /> AI Predicted</span>
        <span className="ml-auto flex items-center gap-1">
          <HelpCircle className="w-3 h-3" />
          Confidence: 94.6%
        </span>
      </div>
    </div>
  );
};

export default ForecastChart;
