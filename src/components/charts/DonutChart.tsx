import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

interface PieDataPoint {
  name: string;
  value: number;
  percent: string;
}

const CRIME_CATEGORIES: PieDataPoint[] = [
  { name: 'Theft', value: 3580, percent: '28.5%' },
  { name: 'Assult', value: 2520, percent: '20.1%' },
  { name: 'Cyber Crime', value: 1935, percent: '15.4%' },
  { name: 'Burglarly', value: 1610, percent: '12.8%' },
  { name: 'Fraud', value: 1218, percent: '9.7%' },
  { name: 'Others', value: 1680, percent: '13.5%' }
];

const COLORS = ['#1E6FD9', '#C94A2A', '#0E9E78', '#6C43CC', '#D4820A', '#80b3ff'];

export const DonutChart: React.FC = () => {
  const totalCrimes = CRIME_CATEGORIES.reduce((a, b) => a + b.value, 0);

  return (
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2 font-mono">
        <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider">
          Top Crime Categories
        </h4>
      </div>

      {/* Grid container splitting visual and list */}
      <div className="flex-grow flex items-center justify-between font-mono text-[9px] min-h-[170px]">
        {/* Visual Render */}
        <div className="w-1/2 h-[95%] relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={CRIME_CATEGORIES}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={68}
                paddingAngle={3}
                dataKey="value"
              >
                {CRIME_CATEGORIES.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
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
          
          {/* Centered label */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none">
            <span className="text-[14px] font-mono font-extrabold text-white">12,543</span>
            <span className="text-[7.5px] text-[#6A7A96] uppercase font-semibold">Total Crimes</span>
          </div>
        </div>

        {/* Legend listing */}
        <div className="w-1/2 flex flex-col gap-1.5 pl-3 pr-1 text-[8.5px]">
          {CRIME_CATEGORIES.map((item, index) => (
            <div key={item.name} className="flex items-center justify-between border-b border-white/5 pb-1">
              <div className="flex items-center gap-1.5 min-w-0">
                <span 
                  className="w-2 h-2 rounded-full shrink-0" 
                  style={{ backgroundColor: COLORS[index % COLORS.length] }} 
                />
                <span className="text-[#A8B4CC] truncate max-w-[80px] uppercase font-semibold">
                  {item.name}
                </span>
              </div>
              <span className="text-white font-bold">{item.percent}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default DonutChart;
