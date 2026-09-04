import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, TrendingUp, TrendingDown, AlertTriangle, Shield, Flame } from 'lucide-react';
import { useMapStore } from '../../store/mapStore';
import type { HotspotPoint } from '../../services/api';
import type { DistrictInfo } from '../../store/mapStore';
import type { EmergingTrendItem } from './KarnatakaMap';

// Real Karnataka district SVG paths — viewBox "0 0 800 900"
// Paths derived from actual Karnataka GeoJSON district boundaries
const DISTRICT_PATHS: Record<string, { d: string; labelX: number; labelY: number }> = {
  'Bidar': {
    d: 'M 390,28 L 430,22 L 490,30 L 530,45 L 545,70 L 520,90 L 490,95 L 455,85 L 420,90 L 395,75 L 380,55 Z',
    labelX: 462, labelY: 60,
  },
  'Kalaburagi': {
    d: 'M 395,75 L 420,90 L 455,85 L 490,95 L 520,90 L 545,70 L 560,100 L 570,130 L 555,160 L 520,170 L 490,165 L 455,155 L 420,160 L 390,150 L 370,125 L 375,100 Z',
    labelX: 470, labelY: 125,
  },
  'Yadgir': {
    d: 'M 420,160 L 455,155 L 490,165 L 510,185 L 500,210 L 470,220 L 440,215 L 415,200 L 410,180 Z',
    labelX: 460, labelY: 190,
  },
  'Raichur': {
    d: 'M 370,125 L 390,150 L 420,160 L 410,180 L 415,200 L 390,215 L 360,220 L 330,210 L 310,190 L 305,165 L 320,145 L 345,130 Z',
    labelX: 360, labelY: 175,
  },
  'Koppal': {
    d: 'M 305,165 L 330,210 L 310,230 L 285,240 L 260,230 L 245,210 L 255,185 L 275,170 Z',
    labelX: 287, labelY: 205,
  },
  'Ballari': {
    d: 'M 310,190 L 330,210 L 310,230 L 285,240 L 260,230 L 255,250 L 265,275 L 290,285 L 320,280 L 350,265 L 370,245 L 380,220 L 360,220 L 330,210 L 310,190 Z',
    labelX: 315, labelY: 255,
  },
  'Vijayanagara': {
    d: 'M 245,210 L 260,230 L 255,250 L 240,265 L 215,270 L 195,255 L 190,235 L 205,215 L 225,205 Z',
    labelX: 222, labelY: 240,
  },
  'Belagavi': {
    d: 'M 115,55 L 160,45 L 200,50 L 235,65 L 255,90 L 260,120 L 245,145 L 220,155 L 190,150 L 160,140 L 135,125 L 115,105 L 100,80 Z',
    labelX: 182, labelY: 100,
  },
  'Vijayapura': {
    d: 'M 255,90 L 290,85 L 330,90 L 360,105 L 375,130 L 370,125 L 345,130 L 320,145 L 305,165 L 275,170 L 255,155 L 245,145 L 260,120 Z',
    labelX: 312, labelY: 125,
  },
  'Bagalkot': {
    d: 'M 190,150 L 220,155 L 245,145 L 255,155 L 275,170 L 255,185 L 245,210 L 225,205 L 205,215 L 185,205 L 170,185 L 165,165 Z',
    labelX: 215, labelY: 180,
  },
  'Gadag': {
    d: 'M 160,140 L 190,150 L 165,165 L 155,185 L 135,190 L 115,180 L 110,160 L 120,145 Z',
    labelX: 150, labelY: 165,
  },
  'Dharwad': {
    d: 'M 115,105 L 135,125 L 160,140 L 120,145 L 110,160 L 90,155 L 75,140 L 80,120 L 95,108 Z',
    labelX: 112, labelY: 132,
  },
  'Haveri': {
    d: 'M 135,190 L 155,185 L 170,185 L 185,205 L 175,225 L 155,235 L 130,230 L 115,215 L 118,198 Z',
    labelX: 150, labelY: 212,
  },
  'Uttara Kannada': {
    d: 'M 60,100 L 80,90 L 95,108 L 80,120 L 75,140 L 60,155 L 45,165 L 35,185 L 30,210 L 40,235 L 55,250 L 50,270 L 38,285 L 28,265 L 20,240 L 22,210 L 30,185 L 38,160 L 42,135 L 48,115 Z',
    labelX: 52, labelY: 185,
  },
  'Shivamogga': {
    d: 'M 90,155 L 110,160 L 115,180 L 135,190 L 118,198 L 115,215 L 100,225 L 80,230 L 65,220 L 55,205 L 55,250 L 40,235 L 30,210 L 35,185 L 45,165 L 60,155 L 75,140 Z',
    labelX: 82, labelY: 200,
  },
  'Davanagere': {
    d: 'M 155,235 L 175,225 L 185,205 L 205,215 L 195,255 L 185,270 L 165,275 L 145,265 L 135,248 L 140,235 Z',
    labelX: 170, labelY: 248,
  },
  'Chitradurga': {
    d: 'M 195,255 L 215,270 L 240,265 L 255,250 L 265,275 L 260,300 L 245,315 L 220,320 L 195,310 L 175,295 L 165,275 L 185,270 Z',
    labelX: 215, labelY: 290,
  },
  'Tumkuru': {
    d: 'M 265,275 L 290,285 L 320,280 L 340,295 L 335,320 L 315,335 L 290,340 L 265,330 L 245,315 L 260,300 Z',
    labelX: 292, labelY: 308,
  },
  'Chikkaballapur': {
    d: 'M 340,295 L 370,285 L 400,290 L 415,310 L 405,330 L 380,340 L 355,335 L 335,320 Z',
    labelX: 375, labelY: 315,
  },
  'Kolar': {
    d: 'M 400,290 L 430,285 L 460,295 L 470,320 L 455,340 L 430,345 L 405,335 L 405,330 L 415,310 Z',
    labelX: 432, labelY: 315,
  },
  'Bengaluru Rural': {
    d: 'M 315,335 L 335,320 L 355,335 L 380,340 L 375,360 L 355,370 L 330,368 L 310,355 Z',
    labelX: 345, labelY: 350,
  },
  'Bengaluru Urban': {
    d: 'M 355,335 L 380,340 L 405,335 L 430,345 L 425,368 L 400,378 L 375,375 L 355,370 L 375,360 Z',
    labelX: 392, labelY: 358,
  },
  'Ramanagara': {
    d: 'M 310,355 L 330,368 L 355,370 L 375,375 L 368,395 L 345,405 L 318,400 L 300,385 L 302,368 Z',
    labelX: 335, labelY: 382,
  },
  'Mandya': {
    d: 'M 265,330 L 290,340 L 310,355 L 302,368 L 300,385 L 280,395 L 255,390 L 238,375 L 240,355 L 252,340 Z',
    labelX: 272, labelY: 365,
  },
  'Hassan': {
    d: 'M 145,265 L 165,275 L 175,295 L 195,310 L 185,330 L 165,345 L 140,345 L 118,330 L 112,310 L 120,290 L 132,275 Z',
    labelX: 152, labelY: 308,
  },
  'Chikkamagaluru': {
    d: 'M 80,230 L 100,225 L 115,215 L 130,230 L 140,235 L 135,248 L 145,265 L 132,275 L 120,290 L 100,285 L 80,270 L 68,252 L 65,235 Z',
    labelX: 105, labelY: 258,
  },
  'Udupi': {
    d: 'M 28,265 L 38,285 L 50,270 L 55,250 L 65,220 L 55,205 L 42,215 L 32,235 L 25,252 Z',
    labelX: 43, labelY: 248,
  },
  'Dakshina Kannada': {
    d: 'M 25,252 L 32,235 L 42,215 L 55,205 L 65,220 L 68,252 L 60,270 L 48,285 L 35,290 L 22,278 Z',
    labelX: 46, labelY: 265,
  },
  'Kodagu': {
    d: 'M 80,270 L 100,285 L 120,290 L 112,310 L 100,325 L 80,328 L 62,315 L 55,295 L 60,278 Z',
    labelX: 87, labelY: 300,
  },
  'Mysuru': {
    d: 'M 118,330 L 140,345 L 165,345 L 185,330 L 195,310 L 220,320 L 245,315 L 240,355 L 238,375 L 215,385 L 190,390 L 165,382 L 140,370 L 118,355 L 105,338 Z',
    labelX: 175, labelY: 355,
  },
  'Chamarajanagar': {
    d: 'M 165,382 L 190,390 L 215,385 L 238,375 L 255,390 L 248,412 L 225,422 L 198,418 L 172,408 L 158,395 Z',
    labelX: 205, labelY: 400,
  },
};

interface Props {
  hotspots: HotspotPoint[];
  districtDataOverride?: Record<string, DistrictInfo>;
  emergingTrends?: EmergingTrendItem[];
}

const KarnatakaDistrictMap: React.FC<Props> = ({
  hotspots,
  districtDataOverride = {},
  emergingTrends = [],
}) => {
  const { selectedDistrict, setSelectedDistrict, setSelectedStation } = useMapStore();
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; name: string } | null>(null);

  const surgingSet = useMemo(
    () => new Set(emergingTrends.filter(t => t.direction === 'increasing' && t.change_percentage > 10).map(t => t.category)),
    [emergingTrends]
  );

  const districtHotspotMap = useMemo(() => {
    const m: Record<string, { maxScore: number; category: string; trend: string }> = {};
    hotspots.forEach(h => {
      if (!h.district_id) return;
      if (!m[h.district_id] || h.score > m[h.district_id].maxScore)
        m[h.district_id] = { maxScore: h.score, category: h.category || '', trend: h.trend || 'stable' };
    });
    return m;
  }, [hotspots]);

  const getFill = (name: string) => {
    if (selectedDistrict === name) return 'rgba(30,111,217,0.75)';
    if (hovered === name) return 'rgba(30,111,217,0.40)';
    const info = districtDataOverride[name];
    const hs = districtHotspotMap[name];
    const isSurging = hs?.trend === 'up' || (hs && surgingSet.has(hs.category));
    if (info?.riskScore != null) {
      if (info.riskScore >= 75) return 'rgba(239,68,68,0.55)';
      if (info.riskScore >= 50) return 'rgba(245,158,11,0.50)';
      return 'rgba(16,185,129,0.40)';
    }
    if (isSurging) return 'rgba(239,68,68,0.45)';
    if (hs) {
      if (hs.maxScore >= 70) return 'rgba(239,68,68,0.38)';
      if (hs.maxScore >= 45) return 'rgba(245,158,11,0.38)';
      return 'rgba(16,185,129,0.32)';
    }
    return 'rgba(30,111,217,0.18)';
  };

  const getStroke = (name: string) => {
    if (selectedDistrict === name) return '#93C5FD';
    if (districtHotspotMap[name]?.trend === 'up') return 'rgba(239,68,68,0.8)';
    return 'rgba(148,163,200,0.6)';
  };

  const dotColor = (score: number, trend: string) => {
    if (trend === 'up' || score >= 70) return '#EF4444';
    if (score >= 45) return '#F59E0B';
    return '#10B981';
  };

  const info = selectedDistrict ? districtDataOverride[selectedDistrict] : null;
  const hs = selectedDistrict ? districtHotspotMap[selectedDistrict] : null;
  const districtHotspots = selectedDistrict
    ? hotspots.filter(h => h.district_id === selectedDistrict)
    : [];
  const districtTrends = selectedDistrict
    ? emergingTrends.filter(t => t.direction === 'increasing' && t.change_percentage > 10)
    : [];

  return (
    <div className="w-full h-full relative bg-[var(--bg-surface)] rounded-xl overflow-hidden flex">
      {/* MAP AREA */}
      <div className={`h-full transition-all duration-300 ${selectedDistrict ? 'w-[60%]' : 'w-full'}`}>
      <svg
        viewBox="0 0 800 450"
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <filter id="glow-red">
            <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#EF4444" floodOpacity="0.7" />
          </filter>
          <filter id="glow-amber">
            <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#F59E0B" floodOpacity="0.7" />
          </filter>
          <filter id="glow-green">
            <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#10B981" floodOpacity="0.7" />
          </filter>
          <filter id="label-shadow">
            <feDropShadow dx="0" dy="0" stdDeviation="2" floodColor="#000" floodOpacity="0.8" />
          </filter>
          <radialGradient id="halo-red" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#EF4444" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#EF4444" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="halo-amber" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.40" />
            <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="halo-green" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#10B981" stopOpacity="0.40" />
            <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Scale the inner map to fit nicely — original paths are ~0-500x0-430 */}
        <g transform="translate(150, 10) scale(1.0)">

          {/* District fills */}
          {Object.entries(DISTRICT_PATHS).map(([name, { d }]) => {
            const isSurging = districtHotspotMap[name]?.trend === 'up';
            return (
              <path
                key={name}
                d={d}
                fill={getFill(name)}
                stroke={getStroke(name)}
                strokeWidth={selectedDistrict === name ? 2 : isSurging ? 1.5 : 1}
                strokeDasharray={isSurging && selectedDistrict !== name ? '4 2' : undefined}
                className="transition-all duration-200 cursor-pointer"
                onMouseEnter={(e) => {
                  setHovered(name);
                  const rect = e.currentTarget.getBoundingClientRect();
                  setTooltip({ x: rect.left + rect.width / 2, y: rect.top, name });
                }}
                onMouseLeave={() => { setHovered(null); setTooltip(null); }}
                onClick={() => {
                  setSelectedDistrict(selectedDistrict === name ? null : name);
                  setSelectedStation(null);
                }}
              />
            );
          })}

          {/* Hotspot halos */}
          {hotspots.map((h, i) => {
            const dp = DISTRICT_PATHS[h.district_id];
            if (!dp) return null;
            const isSurging = h.trend === 'up' || h.score >= 70;
            const gradId = isSurging ? 'halo-red' : h.score >= 45 ? 'halo-amber' : 'halo-green';
            return (
              <circle
                key={`halo-${i}`}
                cx={dp.labelX} cy={dp.labelY}
                r={isSurging ? 20 : 14}
                fill={`url(#${gradId})`}
                pointerEvents="none"
              />
            );
          })}

          {/* Pulsing hotspot dots */}
          {hotspots.map((h, i) => {
            const dp = DISTRICT_PATHS[h.district_id];
            if (!dp) return null;
            const color = dotColor(h.score, h.trend);
            const isSurging = h.trend === 'up' || h.score >= 70;
            const filterId = isSurging ? 'glow-red' : h.score >= 45 ? 'glow-amber' : 'glow-green';
            return (
              <g key={`dot-${i}`} pointerEvents="none">
                {isSurging && (
                  <circle
                    cx={dp.labelX} cy={dp.labelY} r={12}
                    fill={color} opacity={0.18}
                    className="animate-ping"
                    style={{ transformOrigin: `${dp.labelX}px ${dp.labelY}px`, animationDuration: '1.2s' }}
                  />
                )}
                <circle cx={dp.labelX} cy={dp.labelY} r={isSurging ? 5 : 3.5}
                  fill={color} stroke="rgba(0,0,0,0.5)" strokeWidth="0.8"
                  filter={`url(#${filterId})`}
                />
                <circle cx={dp.labelX} cy={dp.labelY} r={isSurging ? 8 : 6}
                  fill="none" stroke={color} strokeWidth="0.8" opacity={0.5}
                />
              </g>
            );
          })}

          {/* District labels */}
          {Object.entries(DISTRICT_PATHS).map(([name, { labelX, labelY }]) => {
            const isSelected = selectedDistrict === name;
            const isSurging = districtHotspotMap[name]?.trend === 'up';
            const short = name
              .replace('Bengaluru ', 'B.')
              .replace('Dakshina Kannada', 'DK')
              .replace('Uttara Kannada', 'UK')
              .replace('Chamarajanagar', 'Chamraj.')
              .replace('Chikkamagaluru', 'Chikkamagal.')
              .replace('Chikkaballapur', 'Chikkaballa.');
            return (
              <text
                key={name}
                x={labelX} y={labelY}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={isSelected ? 8 : 6.5}
                fontWeight={isSelected || isSurging ? 'bold' : 'normal'}
                fill={isSelected ? '#fff' : isSurging ? '#FCA5A5' : 'rgba(220,230,255,0.9)'}
                filter="url(#label-shadow)"
                pointerEvents="none"
                className="select-none"
                style={{ fontFamily: 'monospace' }}
              >
                {short}
              </text>
            );
          })}

          {/* Selected district ring */}
          {selectedDistrict && DISTRICT_PATHS[selectedDistrict] && (
            <circle
              cx={DISTRICT_PATHS[selectedDistrict].labelX}
              cy={DISTRICT_PATHS[selectedDistrict].labelY}
              r={22} fill="none"
              stroke="#60A5FA" strokeWidth="1.5" strokeDasharray="4 3"
              opacity={0.8} pointerEvents="none"
              className="animate-pulse"
            />
          )}
        </g>
      </svg>

      {/* Hover tooltip */}
      {tooltip && (() => {
        const tHs = districtHotspotMap[tooltip.name];
        const tInfo = districtDataOverride[tooltip.name];
        return (
          <div
            className="fixed z-50 pointer-events-none px-3 py-2 rounded-lg bg-[var(--bg-secondary)]/95 border border-[var(--border-primary)] backdrop-blur-sm shadow-xl font-mono text-[10px] min-w-[140px]"
            style={{ left: tooltip.x + 10, top: tooltip.y - 60 }}
          >
            <p className="font-bold text-[var(--text-primary)] text-[11px] mb-1">{tooltip.name}</p>
            {tHs ? (
              <>
                <p className="text-[var(--text-muted)]">Crime: <span className="text-orange-400 font-semibold">{tHs.category}</span></p>
                <p className="text-[var(--text-muted)]">Threat: <span className={tHs.maxScore >= 70 ? 'text-red-400 font-bold' : tHs.maxScore >= 45 ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>{tHs.maxScore}%</span></p>
              </>
            ) : (
              <p className="text-[var(--text-muted)]">No active hotspot</p>
            )}
            {tInfo?.riskScore != null && (
              <p className="text-[var(--text-muted)]">Risk: <span className="text-[var(--text-primary)] font-bold">{tInfo.riskScore}/100</span></p>
            )}
          </div>
        );
      })()}
      </div>{/* end map area */}

      {/* DETAILS PANEL */}
      <AnimatePresence>
        {selectedDistrict && (
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 22, stiffness: 120 }}
            className="w-[40%] h-full border-l border-[var(--border-primary)] bg-[var(--bg-secondary)]/95 backdrop-blur-md flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="px-4 py-3 border-b border-[var(--border-primary)] flex items-start justify-between shrink-0">
              <div>
                <div className="flex items-center gap-1.5 text-[9px] font-mono uppercase text-[var(--accent-teal)] font-bold tracking-wider mb-0.5">
                  <Shield className="w-3 h-3" />
                  District Intelligence
                </div>
                <h3 className="text-sm font-bold text-[var(--text-primary)] font-mono uppercase">{selectedDistrict}</h3>
              </div>
              <button
                onClick={() => { setSelectedDistrict(null); setSelectedStation(null); }}
                className="p-1 rounded hover:bg-[var(--bg-primary)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors cursor-pointer mt-0.5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono text-xs">

              {/* Risk score card */}
              {info?.riskScore != null ? (
                <div className={`p-3 rounded-lg border flex items-center justify-between ${
                  info.riskScore >= 75
                    ? 'bg-red-500/10 border-red-500/30 text-red-400'
                    : info.riskScore >= 50
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                    : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                }`}>
                  <div>
                    <p className="text-[8px] uppercase tracking-widest text-[var(--text-muted)] mb-0.5">District Risk Score</p>
                    <p className="text-2xl font-extrabold">{info.riskScore}<span className="text-sm font-normal">/100</span></p>
                  </div>
                  <AlertTriangle className="w-7 h-7 opacity-70" />
                </div>
              ) : (
                <div className="p-3 rounded-lg border border-dashed border-[var(--border-primary)] text-[var(--text-muted)] text-[10px]">
                  No backend risk score available for this district.
                </div>
              )}

              {/* Surge alert */}
              {districtTrends.length > 0 && (
                <div className="p-2.5 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <div className="flex items-center gap-1.5 text-[9px] font-bold text-red-400 uppercase mb-1">
                    <Flame className="w-3 h-3 animate-pulse" />
                    Emerging Surge
                  </div>
                  <p className="text-[10px] text-[var(--text-primary)] font-semibold">
                    {districtTrends[0].category}: +{districtTrends[0].change_percentage}%
                  </p>
                  <p className="text-[9px] text-[var(--text-muted)] mt-0.5">
                    {districtTrends[0].recent_count} recent vs {districtTrends[0].historical_count} baseline
                  </p>
                </div>
              )}

              {/* Stats */}
              <div className="space-y-0 border border-[var(--border-primary)] rounded-lg overflow-hidden">
                {[
                  { label: 'Monthly FIRs', value: info?.crimeCount != null ? `${info.crimeCount} filings` : '—' },
                  { label: 'Top Crime', value: hs?.category || info?.topCrimeType || '—', highlight: true },
                  { label: 'Threat Score', value: hs ? `${hs.maxScore}%` : '—' },
                  { label: 'Beat Coverage', value: info?.beatRatio != null ? `${info.beatRatio}% est.` : '—' },
                ].map(({ label, value, highlight }, i) => (
                  <div key={label} className={`flex justify-between items-center px-3 py-2 text-[10px] ${
                    i % 2 === 0 ? 'bg-[var(--bg-primary)]/40' : ''
                  }`}>
                    <span className="text-[var(--text-muted)]">{label}</span>
                    <span className={`font-semibold ${
                      highlight ? 'text-orange-400' : 'text-[var(--text-primary)]'
                    }`}>{value}</span>
                  </div>
                ))}
                <div className="flex justify-between items-center px-3 py-2 text-[10px]">
                  <span className="text-[var(--text-muted)]">Weekly Trend</span>
                  {info?.weeklyTrend === 'up' ? (
                    <span className="text-red-400 font-bold flex items-center gap-1"><TrendingUp className="w-3 h-3" />Rising</span>
                  ) : info?.weeklyTrend === 'down' ? (
                    <span className="text-emerald-400 font-bold flex items-center gap-1"><TrendingDown className="w-3 h-3" />Declining</span>
                  ) : (
                    <span className="text-blue-400 font-bold">Stable</span>
                  )}
                </div>
              </div>

              {/* Active hotspot stations */}
              {districtHotspots.length > 0 && (
                <div>
                  <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold mb-2">Active Hotspot Stations ({districtHotspots.length})</p>
                  <div className="space-y-1.5">
                    {districtHotspots.map(h => (
                      <div
                        key={h.name}
                        onClick={() => setSelectedStation(h.name)}
                        className="flex items-center justify-between px-3 py-2 rounded-lg bg-[var(--bg-primary)]/60 border border-[var(--border-primary)] hover:border-[var(--accent-blue)]/50 cursor-pointer transition-all group"
                      >
                        <div className="min-w-0">
                          <p className="text-[10px] font-bold text-[var(--text-primary)] truncate group-hover:text-[var(--accent-blue)]">{h.name}</p>
                          <p className="text-[8px] text-[var(--text-muted)] truncate">{h.category}</p>
                        </div>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded shrink-0 ml-2 ${
                          h.score >= 70 ? 'bg-red-500/20 text-red-400' :
                          h.score >= 45 ? 'bg-amber-500/20 text-amber-400' :
                          'bg-emerald-500/20 text-emerald-400'
                        }`}>{h.score}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!info && !hs && (
                <p className="text-[10px] text-[var(--text-muted)] text-center py-4">No intelligence data available for this district.</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default KarnatakaDistrictMap;
