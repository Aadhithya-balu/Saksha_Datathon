import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface PieDataPoint {
  name: string;
  value: number;
  percent: string;
}

const COLORS = ['#1E6FD9', '#C94A2A', '#0E9E78', '#6C43CC', '#D4820A', '#80b3ff'];

interface DonutChartProps {
  data?: PieDataPoint[];
}

export const DonutChart: React.FC<DonutChartProps> = ({ data = [] }) => {
  const totalCrimes = data.reduce((a, b) => a + b.value, 0);

  return (
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none relative">
      <div className="flex justify-between items-center mb-2 font-mono">
        <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider">Top Crime Categories</h4>
      </div>

      <div className="flex-grow flex items-center justify-between font-mono text-[9px] min-h-[170px]">
        {data.length ? (
          <>
            <div className="w-1/2 h-[95%] relative">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data} cx="50%" cy="50%" innerRadius={45} outerRadius={68} paddingAngle={3} dataKey="value">
                    {data.map((entry, index) => (
                      <Cell key={`cell-${entry.name}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(11, 20, 38, 0.95)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      borderRadius: '6px',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '9px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none">
                <span className="text-[14px] font-mono font-extrabold text-white">{totalCrimes.toLocaleString()}</span>
                <span className="text-[7.5px] text-[#6A7A96] uppercase font-semibold">Total Crimes</span>
              </div>
            </div>

            <div className="w-1/2 flex flex-col gap-1.5 pl-3 pr-1 text-[8.5px]">
              {data.map((item, index) => (
                <div key={item.name} className="flex items-center justify-between border-b border-white/5 pb-1">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                    <span className="text-[#A8B4CC] truncate max-w-[80px] uppercase font-semibold">{item.name}</span>
                  </div>
                  <span className="text-white font-bold">{item.percent}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[10px] text-[#6A7A96] uppercase tracking-wider border border-dashed border-slate-800 rounded">
            No backend category rows available
          </div>
        )}
      </div>
    </div>
  );
};

export default DonutChart;
