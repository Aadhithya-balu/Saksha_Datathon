import React, { useState } from 'react';
import { ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts';
import { CloudRain, Sun, Calendar, Sparkles } from 'lucide-react';

interface WeatherCorrelationData {
  factor: string;
  probability: number;
  crimeType: string;
  icon: string;
}

const CORRELATION_DATA: WeatherCorrelationData[] = [
  { factor: 'Rainy Night', probability: 78, crimeType: 'Burglary & Break-ins', icon: 'rain' },
  { factor: 'Festival Season', probability: 86, crimeType: 'Theft & Pickpocketing', icon: 'calendar' },
  { factor: 'Summer Peak', probability: 64, crimeType: 'Assault & Disputes', icon: 'sun' },
  { factor: 'New Year Peak', probability: 89, crimeType: 'Cyber Scam & Fraud', icon: 'sparkles' },
  { factor: 'Monsoon Flooding', probability: 42, crimeType: 'Property Looting', icon: 'rain' }
];

const COLORS = ['#1E6FD9', '#6C43CC', '#C94A2A', '#D4820A', '#0E9E78'];

export const WeatherCorrelationChart: React.FC = () => {
  const [selectedFactor, setSelectedFactor] = useState<string | null>(null);

  const activeDetail = CORRELATION_DATA.find(d => d.factor === selectedFactor) || CORRELATION_DATA[0];

  return (
    <div className="w-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none font-mono">
      
      {/* Title block */}
      <div className="flex justify-between items-center mb-3">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider">
            Weather & Seasonal Crime Correlation
          </h4>
          <span className="text-[8px] text-slate-500 uppercase">AI Multi-factor Environmental Probability Mapping</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
        
        {/* Left Chart (8 cols) */}
        <div className="md:col-span-8 h-[200px] text-[8.5px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart 
              data={CORRELATION_DATA} 
              margin={{ top: 5, right: 5, left: -25, bottom: 5 }}
              onMouseMove={(state) => {
                if (state && state.activeLabel) {
                  setSelectedFactor(state.activeLabel);
                }
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis 
                dataKey="factor" 
                stroke="#A8B4CC" 
                tickLine={false} 
                axisLine={false} 
                style={{ fill: '#E8EDF5', fontSize: '11px', fontWeight: 'bold' }}
              />
              <YAxis 
                stroke="#A8B4CC" 
                tickLine={false} 
                axisLine={false} 
                domain={[0, 100]}
                unit="%"
                style={{ fill: '#E8EDF5', fontSize: '11px', fontWeight: 'bold' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(11, 20, 38, 0.95)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  borderRadius: '6px',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '11px',
                }}
              />
              <Bar dataKey="probability" radius={[4, 4, 0, 0]}>
                {CORRELATION_DATA.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={COLORS[index % COLORS.length]} 
                    fillOpacity={selectedFactor === entry.factor ? 0.95 : 0.65}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Right Details (4 cols) */}
        <div className="md:col-span-4 p-3 bg-slate-950/50 border border-slate-900 rounded-lg flex flex-col gap-2.5 text-[9px] text-left">
          <span className="text-[#6A7A96] uppercase text-[8px] font-bold block">
            Environmental Risk Detail
          </span>

          <div>
            <span className="text-white font-extrabold block uppercase tracking-wide">
              {activeDetail.factor} Correlation
            </span>
            <span className="text-red-400 font-bold block mt-0.5 text-[10.5px]">
              {activeDetail.probability}% Spike Probability
            </span>
          </div>

          <div className="border-t border-slate-900 pt-2 text-[#A8B4CC]">
            <span className="text-[8px] text-slate-500 block uppercase">Primary Crime Spikes</span>
            <span className="text-white font-semibold mt-0.5 block">{activeDetail.crimeType}</span>
          </div>

          <p className="text-[8px] text-slate-500 leading-normal uppercase">
            Correlation index computed over 5-year historical weather patterns.
          </p>
        </div>

      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default WeatherCorrelationChart;
