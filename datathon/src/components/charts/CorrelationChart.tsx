import React, { useState } from 'react';
import * as d3 from 'd3';

interface ScatterPoint {
  district: string;
  unemployment: number; // in percentage
  riskScore: number;     // 0-100%
  populationDensity: number; // size factor
}

const CORRELATION_DATA: ScatterPoint[] = [
  { district: 'Bengaluru Urban', unemployment: 4.2, riskScore: 88, populationDensity: 4380 },
  { district: 'Mysuru', unemployment: 5.8, riskScore: 54, populationDensity: 485 },
  { district: 'Kalaburagi', unemployment: 8.4, riskScore: 72, populationDensity: 232 },
  { district: 'Belagavi', unemployment: 6.1, riskScore: 61, populationDensity: 356 },
  { district: 'Tumkuru', unemployment: 5.2, riskScore: 49, populationDensity: 280 },
  { district: 'Dharwad', unemployment: 6.5, riskScore: 58, populationDensity: 412 },
  { district: 'Ballari', unemployment: 7.8, riskScore: 69, populationDensity: 300 },
  { district: 'Hassan', unemployment: 4.8, riskScore: 42, populationDensity: 260 },
  { district: 'Mangaluru', unemployment: 5.0, riskScore: 66, populationDensity: 388 }
];

export const CorrelationChart: React.FC = () => {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; data: ScatterPoint } | null>(null);

  // Chart Dimensions
  const width = 500;
  const height = 300;
  const padding = { top: 30, right: 30, bottom: 50, left: 55 };

  // D3 Scales Setup
  const xScale = d3.scaleLinear()
    .domain([3.5, 9.0]) // unemployment range
    .range([padding.left, width - padding.right]);

  const yScale = d3.scaleLinear()
    .domain([30, 95]) // risk score range
    .range([height - padding.bottom, padding.top]);

  const sizeScale = d3.scaleLinear()
    .domain([200, 4500]) // density range
    .range([4.5, 14]);

  // Tick generator
  const xTicks = xScale.ticks(6);
  const yTicks = yScale.ticks(6);

  // Compute best-fit linear regression values (Y = mX + c) for the trendline
  const calculateRegressionLine = () => {
    const xVals = CORRELATION_DATA.map(d => d.unemployment);
    const yVals = CORRELATION_DATA.map(d => d.riskScore);
    const sumX = xVals.reduce((a, b) => a + b, 0);
    const sumY = yVals.reduce((a, b) => a + b, 0);
    const sumXY = xVals.reduce((sum, x, idx) => sum + x * yVals[idx], 0);
    const sumXX = xVals.reduce((sum, x) => sum + x * x, 0);
    const count = CORRELATION_DATA.length;

    const slope = (count * sumXY - sumX * sumY) / (count * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / count;

    // Line start & end projection coordinates
    const startX = 3.8;
    const endX = 8.6;
    
    return {
      x1: xScale(startX),
      y1: yScale(slope * startX + intercept),
      x2: xScale(endX),
      y2: yScale(slope * endX + intercept)
    };
  };

  const regression = calculateRegressionLine();

  return (
    <div className="w-full bg-[var(--bg-tertiary)]/40 border border-border-color p-4 rounded-card relative select-none">
      
      {/* Chart Title */}
      <div className="flex justify-between items-center mb-3">
        <span className="text-[10px] font-mono text-[var(--accent-teal)] uppercase font-bold tracking-wider">
          AI CORRELATION PROJECTION
        </span>
        <span className="text-[9px] font-mono text-[var(--text-muted)] uppercase select-none">
          Unemployment Vs Risk Index
        </span>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto overflow-visible">
          {/* Geodesic dashed grid coordinates */}
          <g stroke="rgba(255,255,255,0.03)" strokeWidth="0.5" strokeDasharray="3 3">
            {xTicks.map((tick, i) => (
              <line key={i} x1={xScale(tick)} y1={padding.top} x2={xScale(tick)} y2={height - padding.bottom} />
            ))}
            {yTicks.map((tick, i) => (
              <line key={i} x1={padding.left} y1={yScale(tick)} x2={width - padding.right} y2={yScale(tick)} />
            ))}
          </g>

          {/* Axes outlines */}
          <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
          <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="rgba(255,255,255,0.15)" strokeWidth="1" />

          {/* Axis Labels */}
          {xTicks.map((tick, i) => (
            <text key={i} x={xScale(tick)} y={height - padding.bottom + 16} className="text-[10px] font-mono font-bold fill-[var(--text-primary)] text-center" textAnchor="middle">
              {tick}%
            </text>
          ))}
          {yTicks.map((tick, i) => (
            <text key={i} x={padding.left - 10} y={yScale(tick) + 3} className="text-[10px] font-mono font-bold fill-[var(--text-primary)] text-right" textAnchor="end">
              {tick}
            </text>
          ))}

          {/* X Axis Name */}
          <text x={width / 2} y={height - 10} className="text-[10.5px] font-mono font-bold fill-[var(--text-primary)] uppercase text-center" textAnchor="middle">
            Socio-Economic Unemployment Index (%)
          </text>
          
          {/* Y Axis Name */}
          <text x={15} y={height / 2} className="text-[10.5px] font-mono font-bold fill-[var(--text-primary)] uppercase text-center" textAnchor="middle" transform={`rotate(-90 15 ${height / 2})`}>
            Crime Risk Score (0-100)
          </text>

          {/* Linear regression best-fit slope path */}
          <line 
            x1={regression.x1} 
            y1={regression.y1} 
            x2={regression.x2} 
            y2={regression.y2} 
            stroke="#1E6FD9" 
            strokeWidth="1.5" 
            strokeDasharray="4 4"
            opacity="0.75"
          />

          {/* Data Points */}
          {CORRELATION_DATA.map((pt, i) => {
            const x = xScale(pt.unemployment);
            const y = yScale(pt.riskScore);
            const r = sizeScale(pt.populationDensity);
            const isHovered = tooltip?.data.district === pt.district;

            return (
              <g 
                key={i}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  setTooltip({
                    x: x + 10,
                    y: y - 25,
                    data: pt
                  });
                }}
                onMouseLeave={() => setTooltip(null)}
                className="cursor-pointer"
              >
                {/* Outer halo */}
                <circle 
                  cx={x} 
                  cy={y} 
                  r={r + 3} 
                  fill={isHovered ? 'rgba(30,111,217,0.18)' : 'rgba(30,111,217,0.06)'} 
                  stroke={isHovered ? '#1E6FD9' : 'rgba(30,111,217,0.2)'}
                  strokeWidth="0.5"
                  className="transition-all duration-200"
                />
                {/* Core Dot node */}
                <circle 
                  cx={x} 
                  cy={y} 
                  r={r} 
                  fill={pt.riskScore >= 70 ? '#C94A2A' : pt.riskScore >= 55 ? '#D4820A' : '#0e9e78'} 
                  opacity="0.85"
                />
              </g>
            );
          })}
        </svg>

        {/* Custom D3 Tooltip card floating */}
        {tooltip && (
          <div 
            className="absolute z-30 p-2.5 bg-[#0c1424] border border-[#1a2744] text-[9.5px] font-mono rounded max-w-[190px] shadow-2xl pointer-events-none"
            style={{ 
              left: `${(tooltip.x / width) * 100}%`, 
              top: `${(tooltip.y / height) * 100}%` 
            }}
          >
            <span className="text-[#E8EDF5] font-bold block uppercase">{tooltip.data.district}</span>
            <div className="h-[1px] bg-[#1a2744] my-1" />
            <div className="flex justify-between gap-3 text-[#a8b4cc]">
              <span>UNEMPLOYMENT:</span>
              <span className="text-[#E8EDF5]">{tooltip.data.unemployment}%</span>
            </div>
            <div className="flex justify-between gap-3 text-[#a8b4cc] mt-0.5">
              <span>CRIME THREAT:</span>
              <span className="text-[#C94A2A] font-bold">{tooltip.data.riskScore}/100</span>
            </div>
            <div className="flex justify-between gap-3 text-[#a8b4cc] mt-0.5">
              <span>POP DENSITY:</span>
              <span className="text-[#1E6FD9]">{tooltip.data.populationDensity}/sq.km</span>
            </div>
          </div>
        )}
      </div>

    </div>
  );
};

export default CorrelationChart;
