import React, { useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { useAppStore } from '../../store/appStore';
import { useThemePalettes, tooltipStyle } from '../../theme';
import type { SeasonData } from '../../services/api';

interface WeatherCorrelationChartProps {
  seasons?: SeasonData[];
}

export const WeatherCorrelationChart: React.FC<WeatherCorrelationChartProps> = ({ seasons = [] }) => {
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const theme = useAppStore((s) => s.theme);
  const palette = useThemePalettes();
  const COLORS = palette.chart.series;

  if (seasons.length === 0) {
    return (
      <div className="sk-panel sk-panel-pad w-full select-none">
        <div className="mb-3">
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider">
            Seasonal Crime Distribution
          </h4>
          <span className="text-[8px] text-[var(--text-muted)] uppercase">Computed from recorded case dates</span>
        </div>
        <div className="h-[200px] flex items-center justify-center text-[10px] font-mono text-[var(--text-muted)] uppercase border border-dashed border-[var(--border-muted)] rounded-lg">
          No seasonal case data available yet — record cases with occurrence dates to populate this view.
        </div>
      </div>
    );
  }

  const totalCases = seasons.reduce((sum, s) => sum + s.count, 0);
  const activeDetail =
    seasons.find((s) => s.season === selectedSeason) ??
    [...seasons].sort((a, b) => b.count - a.count)[0];

  return (
    <div className="sk-panel sk-panel-pad w-full flex flex-col justify-between select-none">

      {/* Title block */}
      <div className="flex justify-between items-center mb-3">
        <div>
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider">
            Seasonal Crime Distribution
          </h4>
          <span className="text-[8px] text-[var(--text-muted)] uppercase">
            Case counts by Karnataka season · {totalCases} cases analysed
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">

        {/* Left Chart (8 cols) */}
        <div className="md:col-span-8 h-[200px] text-[8.5px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={seasons}
              margin={{ top: 5, right: 5, left: -25, bottom: 5 }}
              onMouseMove={(state) => {
                if (state && state.activeLabel) {
                  setSelectedSeason(state.activeLabel);
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={palette.chart.grid} vertical={false} />
              <XAxis
                dataKey="season"
                stroke={palette.chart.axis}
                tickLine={false}
                axisLine={false}
                tick={{ fill: palette.chart.axis, fontSize: 11.5 }}
              />
              <YAxis
                stroke={palette.chart.axis}
                tickLine={false}
                axisLine={false}
                allowDecimals={false}
                tick={{ fill: palette.chart.axis, fontSize: 11.5 }}
              />
              <Tooltip contentStyle={tooltipStyle(theme)} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {seasons.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                    fillOpacity={activeDetail?.season === entry.season ? 0.95 : 0.65}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Right Details (4 cols) */}
        <div className="md:col-span-4 p-3 bg-[var(--bg-secondary)]/50 border border-[var(--border-primary)] rounded-lg flex flex-col gap-2.5 text-[9px] text-left">
          <span className="text-[var(--text-muted)] uppercase text-[8px] font-bold block">
            Season Detail
          </span>

          <div>
            <span className="text-[var(--text-primary)] font-extrabold block uppercase tracking-wide">
              {activeDetail?.season ?? '—'}
            </span>
            <span className="text-red-400 font-bold block mt-0.5 text-[10.5px]">
              {activeDetail?.count ?? 0} cases ({activeDetail?.percentage ?? 0}% of total)
            </span>
          </div>

          {activeDetail?.top_district && (
            <div className="border-t border-[var(--border-primary)] pt-2 text-[var(--text-secondary)]">
              <span className="text-[8px] text-[var(--text-muted)] block uppercase">Highest-volume district</span>
              <span className="text-[var(--text-primary)] font-semibold mt-0.5 block">{activeDetail.top_district}</span>
            </div>
          )}

          <p className="text-[8px] text-[var(--text-muted)] leading-normal uppercase">
            Seasons derived from each case's occurrence month using the Karnataka meteorological calendar.
          </p>
        </div>

      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default WeatherCorrelationChart;
