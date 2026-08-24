import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useAppStore } from '../../store/appStore';
import { useThemePalettes, tooltipStyle } from '../../theme';
import { LayoutGrid } from 'lucide-react';

interface PieDataPoint {
  name: string;
  value: number;
  percent?: string;
}

interface DonutChartProps {
  data?: PieDataPoint[];
  onCategoryClick?: (categoryName: string) => void;
}

export const DonutChart: React.FC<DonutChartProps> = ({ data = [], onCategoryClick }) => {
  const theme = useAppStore((s) => s.theme);
  const palette = useThemePalettes();
  const COLORS = palette.chart.series;
  const totalCrimes = data.reduce((a, b) => a + b.value, 0);

  return (
    <div className="sk-panel sk-panel-pad w-full h-full flex flex-col">
      <div className="flex justify-between items-center mb-2">
        <h4 className="sk-panel-title flex items-center gap-1.5">
          <LayoutGrid className="w-4 h-4 text-[var(--accent-blue)]" />
          Category Distribution
        </h4>
        <span className="text-xs text-[var(--text-muted)]">{totalCrimes.toLocaleString()} total</span>
      </div>

      <div className="flex-grow w-full min-h-[170px] relative">
        {data.length ? (
          <>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius="52%"
                  outerRadius="78%"
                  dataKey="value"
                  stroke="none"
                  paddingAngle={1.5}
                  cursor={onCategoryClick ? 'pointer' : 'default'}
                  onClick={(entry) => entry?.name && onCategoryClick?.(entry.name)}
                >
                  {data.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={tooltipStyle(theme)}
                  formatter={(value: number, name: string) => [`${value.toLocaleString()} cases`, name]}
                />
              </PieChart>
            </ResponsiveContainer>
            {/* Center total */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center" style={{ marginTop: '-8%' }}>
                <div className="text-xl font-bold text-[var(--text-primary)]">{totalCrimes.toLocaleString()}</div>
                <div className="text-[11px] text-[var(--text-muted)]">cases</div>
              </div>
            </div>
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-[var(--text-muted)] border border-dashed border-[var(--border-primary)] rounded-lg">
            No category data available
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11.5px] text-[var(--text-secondary)] pt-3 border-t border-[var(--border-primary)] mt-2">
        {data.slice(0, 6).map((item, index) => (
          <div 
            key={item.name} 
            onClick={() => onCategoryClick?.(item.name)}
            className={`flex items-center gap-1.5 min-w-0 ${onCategoryClick ? 'cursor-pointer hover:text-[var(--text-primary)] transition-colors' : ''}`}
            title={onCategoryClick ? `Filter by ${item.name}` : undefined}
          >
            <span className="w-2 h-2 rounded-sm shrink-0" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
            <span className="truncate">{item.name}</span>
            <span className="ml-auto text-[var(--text-muted)]">{item.percent ?? `${Math.round((item.value / Math.max(totalCrimes, 1)) * 100)}%`}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default DonutChart;

