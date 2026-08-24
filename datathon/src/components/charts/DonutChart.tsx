import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { LayoutGrid } from 'lucide-react';

interface PieDataPoint {
  name: string;
  value: number;
  percent: string;
}

const COLORS = ['#1E6FD9', '#C94A2A', '#0E9E78', '#6C43CC', '#D4820A', '#80b3ff'];

interface DonutChartProps {
  data?: PieDataPoint[];
  onCategoryClick?: (categoryName: string) => void;
}

export const DonutChart: React.FC<DonutChartProps> = ({ data = [], onCategoryClick }) => {
  const totalCrimes = data.reduce((a, b) => a + b.value, 0);

  return (
    <div className="w-full h-full bg-[var(--bg-secondary)]/80 border border-[var(--border-primary)] p-4 rounded-lg flex flex-col justify-between select-none relative font-mono overflow-hidden">
      {/* Title */}
      <div className="flex justify-between items-center mb-2 select-none">
        <div>
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-1.5">
            <LayoutGrid className="w-4 h-4 text-[var(--accent-blue)]" />
            Crime Category Distribution
          </h4>
          <span className="text-[9px] text-[var(--text-secondary)] uppercase font-semibold">Radial Segment Breakdown (Click to filter)</span>
        </div>
      </div>

      {/* Pie Chart */}
      <div className="flex-grow w-full min-h-[170px]">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius="45%"
                outerRadius="75%"
                dataKey="value"
                stroke="rgba(8,14,27,0.8)"
                strokeWidth={2}
                cursor={onCategoryClick ? 'pointer' : 'default'}
                onClick={(entry) => entry?.name && onCategoryClick?.(entry.name)}
              >
                {data.map((_entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} opacity={0.85} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(11, 20, 38, 0.96)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '11px',
                  color: '#E8EDF5',
                }}
                formatter={(value: number, name: string) => [`${value.toLocaleString()} Cases`, name]}
              />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-[10px] text-[var(--text-muted)] uppercase tracking-wider border border-dashed border-[var(--border-primary)] rounded">
            No category rows available
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[8.5px] text-[var(--text-secondary)] font-semibold uppercase tracking-wider pt-2 border-t border-[var(--border-primary)]">
        {data.slice(0, 6).map((item, index) => (
          <div 
            key={item.name} 
            onClick={() => onCategoryClick?.(item.name)}
            className={`flex items-center gap-1.5 ${onCategoryClick ? 'cursor-pointer hover:text-white transition-colors' : ''}`}
            title={`Filter by ${item.name}`}
          >
            <span className="w-2 h-2 rounded-sm shrink-0" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
            <span className="truncate">{item.name}</span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flex justify-between text-[9px] text-[var(--text-primary)] font-bold uppercase tracking-widest pt-2 border-t border-[var(--border-primary)] select-none">
        <span>Distribution Matrix</span>
        <span>Total: {totalCrimes.toLocaleString()} Cases</span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default DonutChart;
