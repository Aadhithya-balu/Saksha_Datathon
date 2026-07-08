import React, { useState, useEffect } from 'react';
import { useMapStore, DISTRICT_COORDS } from '../../store/mapStore';
import type { DistrictInfo } from '../../store/mapStore';
import TimeSlider from './TimeSlider';
import { Shield, MapPin, Eye, Info, X, TrendingUp, TrendingDown, Users, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { downloadSecureDossier } from '../../utils/downloader';
import { useAuditStore } from '../../store/auditStore';
import { useAuthStore } from '../../store/authStore';

// Coordinates projection onto custom 800x600 SVG canvas
const projectLonX = (lon: number) => {
  // Lon 73.8 to 78.8
  return 60 + ((lon - 73.8) / (78.8 - 73.8)) * 680;
};

const projectLatY = (lat: number) => {
  // Lat 11.5 is bottom, Lat 18.6 is top
  return 540 - ((lat - 11.5) / (18.6 - 11.5)) * 480;
};

// District Boundary simplified paths for UI presentation
const DISTRICT_BOUNDARIES: Record<string, [number, number][]> = {
  'Bengaluru Urban': [
    [77.4, 13.2], [77.8, 13.1], [77.8, 12.8], [77.4, 12.7], [77.3, 12.9]
  ],
  'Mysuru': [
    [76.2, 12.5], [76.7, 12.6], [77.0, 12.1], [76.5, 11.8], [76.0, 11.9]
  ],
  'Kalaburagi': [
    [76.5, 17.6], [77.2, 17.7], [77.3, 17.1], [76.7, 16.9], [76.4, 17.2]
  ],
  'Belagavi': [
    [74.2, 16.5], [74.9, 16.6], [75.2, 15.8], [74.5, 15.5], [73.9, 15.8]
  ],
  'Tumkuru': [
    [76.8, 14.1], [77.2, 13.8], [77.4, 13.2], [76.9, 13.0], [76.6, 13.4]
  ],
  'Dharwad': [
    [74.8, 15.6], [75.3, 15.7], [75.4, 15.1], [75.0, 15.0], [74.8, 15.3]
  ],
  'Ballari': [
    [76.4, 15.6], [77.1, 15.4], [77.0, 14.9], [76.5, 14.8], [76.2, 15.1]
  ],
  'Hassan': [
    [75.8, 13.3], [76.3, 13.2], [76.3, 12.7], [75.9, 12.6], [75.6, 12.9]
  ],
  'Mangaluru': [
    [74.7, 13.1], [75.4, 13.0], [75.4, 12.5], [74.8, 12.6], [74.6, 12.9]
  ]
};

// Generates time-dependent hotspots
const getHotspotsForHour = (hour: number) => {
  const baseHotspots = [
    { name: 'Bengaluru Commercial Hub', lat: 12.9716, lng: 77.5946, weight: 85, type: 'Cyber Fraud' },
    { name: 'Bengaluru Tech Corridor', lat: 12.9141, lng: 77.6413, weight: 70, type: 'Online Extortion' },
    { name: 'Mysuru Palace Gate', lat: 12.3021, lng: 76.6531, weight: 45, type: 'Pickpocketing' },
    { name: 'Kalaburagi Outskirts', lat: 17.3350, lng: 76.8380, weight: 72, type: 'Land disputes' },
    { name: 'Belagavi Checkpoint', lat: 15.8600, lng: 74.5100, weight: 62, type: 'Smuggling' },
    { name: 'Ballari Mines Sector B', lat: 15.1480, lng: 76.9250, weight: 80, type: 'Mineral Theft' },
    { name: 'Mangaluru Harbor Port', lat: 12.9050, lng: 74.8350, weight: 68, type: 'Narcotics Transit' }
  ];

  // Adjust hotspot weights depending on the hour (crime spikes late evening & night)
  return baseHotspots.map(hs => {
    let multiplier = 1.0;
    if (hour >= 18 || hour <= 2) {
      // Night surge
      multiplier = hs.type === 'Cyber Fraud' ? 0.7 : 1.35;
    } else if (hour >= 8 && hour <= 16) {
      // Daytime cyber surge
      multiplier = hs.type === 'Cyber Fraud' ? 1.4 : 0.6;
    }
    return {
      ...hs,
      weight: Math.min(100, Math.round(hs.weight * multiplier))
    };
  });
};

export const KarnatakaMap: React.FC = () => {
  const {
    viewState,
    selectedDistrict,
    timeOfDay,
    layers,
    districtData,
    setSelectedDistrict,
    toggleLayer,
    flyToDistrict
  } = useMapStore();

  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  const [panelOpen, setPanelOpen] = useState(false);
  const [mapZoom, setMapZoom] = useState(1);
  const [mapOffset, setMapOffset] = useState({ x: 0, y: 0 });

  // Open details panel when a district is selected
  useEffect(() => {
    if (selectedDistrict) {
      setPanelOpen(true);
    } else {
      setPanelOpen(false);
    }
  }, [selectedDistrict]);

  const activeHotspots = getHotspotsForHour(timeOfDay);
  const activeDistrictInfo = selectedDistrict ? districtData[selectedDistrict] : null;

  // Handle zooming of vector view representation on selection
  useEffect(() => {
    if (selectedDistrict) {
      const coords = DISTRICT_COORDS[selectedDistrict];
      if (coords) {
        // Project to canvas coordinates
        const x = projectLonX(coords.lng);
        const y = projectLatY(coords.lat);
        setMapZoom(1.85);
        setMapOffset({ x: 400 - x * 1.85, y: 300 - y * 1.85 });
      }
    } else {
      setMapZoom(1);
      setMapOffset({ x: 0, y: 0 });
    }
  }, [selectedDistrict]);

  return (
    <div className="w-full h-full relative overflow-hidden flex flex-col justify-between bg-[#080E1B] rounded-card border border-border-color">
      
      {/* MAP HEADER PANELS */}
      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2 max-w-xs pointer-events-none select-none">
        <div className="px-3 py-2 bg-secondary-bg/95 backdrop-blur-md border border-border-color rounded-card pointer-events-auto">
          <span className="text-[10px] font-mono text-[#0E9E78] uppercase font-bold tracking-wider">
            Vector Grid Telemetry
          </span>
          <h3 className="text-[13px] font-mono font-bold text-[#E8EDF5] mt-0.5">
            {selectedDistrict ? `Focus: ${selectedDistrict}` : 'Statewide Overview'}
          </h3>
          <p className="text-[9px] font-mono text-[#6A7A96] mt-1 select-none">
            LAT/LON D3 GEODESIC AUTO-CENTERING
          </p>
        </div>

        {/* LAYER SELECTORS */}
        <div className="px-3 py-2 bg-secondary-bg/95 backdrop-blur-md border border-border-color rounded-card pointer-events-auto flex flex-col gap-1.5">
          <span className="text-[8px] font-mono uppercase tracking-widest text-[#6A7A96] mb-1">
            Display Layers
          </span>
          <button
            onClick={() => toggleLayer('hotspot')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.hotspot 
                ? 'bg-[#1E6FD9]/15 border-[#1E6FD9] text-[#1E6FD9]' 
                : 'bg-transparent border-slate-700 text-[#A8B4CC]'
            }`}
          >
            <span>Hotspots Data</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.hotspot ? 'bg-[#1E6FD9] animate-pulse' : 'bg-slate-600'}`} />
          </button>
          
          <button
            onClick={() => toggleLayer('beatCoverage')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.beatCoverage 
                ? 'bg-[#0E9E78]/15 border-[#0E9E78] text-[#0E9E78]' 
                : 'bg-transparent border-slate-700 text-[#A8B4CC]'
            }`}
          >
            <span>Beat Officer Ratio</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.beatCoverage ? 'bg-[#0E9E78] animate-pulse' : 'bg-slate-600'}`} />
          </button>
          
          <button
            onClick={() => toggleLayer('riskScore')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.riskScore 
                ? 'bg-[#6C43CC]/15 border-[#6C43CC] text-[#6C43CC]' 
                : 'bg-transparent border-slate-700 text-[#A8B4CC]'
            }`}
          >
            <span>Regional Risk Index</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.riskScore ? 'bg-[#6C43CC] animate-pulse' : 'bg-slate-600'}`} />
          </button>
        </div>
      </div>

      {/* RENDER CANVAS CONTAINER */}
      <div className="flex-1 w-full relative cursor-grab active:cursor-grabbing bg-slate-950 overflow-hidden">
        
        {/* GEODESIC BACKGROUND GRID */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-20">
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E6FD9" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#gridPattern)" />
        </svg>

        {/* INTERACTIVE VECTOR GRAPHICS */}
        <svg 
          viewBox="0 0 800 600" 
          className="w-full h-full select-none transform transition-transform duration-1000 ease-out"
          style={{
            transform: `scale(${mapZoom}) translate(${mapOffset.x / mapZoom}px, ${mapOffset.y / mapZoom}px)`,
            transformOrigin: '0 0'
          }}
        >
          {/* Geodesic coordinates lines */}
          <g stroke="rgba(30,111,217,0.1)" strokeWidth="0.5" strokeDasharray="3 3">
            {[74, 75, 76, 77, 78].map((lon) => (
              <line 
                key={lon} 
                x1={projectLonX(lon)} 
                y1={0} 
                x2={projectLonX(lon)} 
                y2={600} 
              />
            ))}
            {[12, 13, 14, 15, 16, 17, 18].map((lat) => (
              <line 
                key={lat} 
                x1={0} 
                y1={projectLatY(lat)} 
                x2={800} 
                y2={projectLatY(lat)} 
              />
            ))}
          </g>

          {/* District boundary shapes polygons */}
          <g>
            {Object.entries(DISTRICT_BOUNDARIES).map(([name, points]) => {
              const projectedPoints = points.map(([lon, lat]) => `${projectLonX(lon)},${projectLatY(lat)}`).join(' ');
              const isSelected = selectedDistrict === name;
              const info = districtData[name];
              
              // Color coding based on active layers
              let fill = 'rgba(30, 111, 217, 0.03)';
              let stroke = 'rgba(255, 255, 255, 0.15)';
              
              if (layers.riskScore && info) {
                // Red for high risk, orange/yellow for middle, blue/slate for low
                const rs = info.riskScore;
                fill = rs >= 80 
                  ? 'rgba(201, 74, 42, 0.35)' 
                  : rs >= 60 
                  ? 'rgba(212, 130, 10, 0.35)' 
                  : 'rgba(14, 158, 120, 0.25)';
              } else if (layers.beatCoverage && info) {
                // Green gradient for high coverage
                const br = info.beatRatio;
                fill = br >= 75 
                  ? 'rgba(14, 158, 120, 0.35)' 
                  : br >= 60 
                  ? 'rgba(30, 111, 217, 0.25)' 
                  : 'rgba(212, 130, 10, 0.25)';
              }

              if (isSelected) {
                fill = 'rgba(30, 111, 217, 0.12)';
                stroke = '#1E6FD9';
              }

              return (
                <polygon
                  key={name}
                  points={projectedPoints}
                  className="transition-all duration-300 hover:fill-slate-800/40 hover:stroke-[#1E6FD9]/80 cursor-pointer"
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={isSelected ? 2 : 1}
                  onClick={() => setSelectedDistrict(isSelected ? null : name)}
                />
              );
            })}
          </g>

          {/* DISTRICT ANCHORS LABELS */}
          <g>
            {Object.entries(DISTRICT_COORDS).map(([name, coords]) => {
              const x = projectLonX(coords.lng);
              const y = projectLatY(coords.lat);
              const isSelected = selectedDistrict === name;

              return (
                <g key={name} className="pointer-events-none select-none">
                  {/* Center pin node */}
                  <circle 
                    cx={x} 
                    cy={y} 
                    r={isSelected ? 4 : 2} 
                    fill={isSelected ? '#1E6FD9' : '#A8B4CC'} 
                  />
                  {/* District text tag */}
                  <text
                    x={x + 6}
                    y={y + 3}
                    className="font-mono text-[9px] fill-[#6A7A96] font-semibold"
                  >
                    {name}
                  </text>
                </g>
              );
            })}
          </g>

          {/* HOTSPOT PULSING RING LAYERS (Deck.gl rendering mock) */}
          {layers.hotspot && (
            <g>
              {activeHotspots.map((hs, index) => {
                const x = projectLonX(hs.lng);
                const y = projectLatY(hs.lat);
                const isHigh = hs.weight >= 80;
                
                // Color mapping
                const color = isHigh ? '#C94A2A' : '#D4820A';

                return (
                  <g key={index} className="pointer-events-none">
                    {/* Concentric pulsing rings using basic anim emulation */}
                    <circle cx={x} cy={y} r={14} fill={color} opacity={0.12} className="animate-ping" style={{ transformOrigin: `${x}px ${y}px`, animationDuration: '2s' }} />
                    <circle cx={x} cy={y} r={28} stroke={color} strokeWidth="0.5" fill="none" opacity={0.06} className="animate-ping" style={{ transformOrigin: `${x}px ${y}px`, animationDuration: '3s' }} />
                    
                    {/* Center Core dot */}
                    <circle cx={x} cy={y} r={isHigh ? 6 : 4.5} fill={color} />
                    <circle cx={x} cy={y} r={isHigh ? 8 : 6.5} stroke={color} strokeWidth="1" fill="none" opacity={0.5} />
                  </g>
                );
              })}
            </g>
          )}
        </svg>

        {/* MAP INFO RESET SELECTOR */}
        {selectedDistrict && (
          <button
            onClick={() => setSelectedDistrict(null)}
            className="absolute bottom-4 left-4 z-20 px-3 py-1.5 bg-[#C94A2A] hover:bg-[#C94A2A]/80 text-white font-mono text-[10px] uppercase rounded-btn flex items-center gap-1 shadow-glow-coral cursor-pointer"
          >
            <span>Reset View Coordinates</span>
          </button>
        )}
      </div>

      {/* DETAILS PANEL DRAWER SLIDING IN (RIGHT SIDE) */}
      <AnimatePresence>
        {panelOpen && activeDistrictInfo && (
          <motion.div
            initial={{ x: 360, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 360, opacity: 0 }}
            transition={{ type: 'spring', damping: 20, stiffness: 100 }}
            className="absolute top-0 right-0 h-full w-80 bg-secondary-bg/95 border-l border-border-color backdrop-blur-md z-30 p-5 flex flex-col justify-between overflow-y-auto select-none"
          >
            <div>
              {/* Header drawer row */}
              <div className="flex justify-between items-center border-b border-border-color pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-[#1E6FD9] shrink-0" />
                  <h3 className="text-sm font-mono font-bold text-white uppercase truncate">
                    {activeDistrictInfo.name}
                  </h3>
                </div>
                <button
                  onClick={() => setPanelOpen(false)}
                  className="p-1 hover:bg-[#1E6FD9]/15 rounded text-[#A8B4CC] hover:text-white cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Data overview block */}
              <div className="flex flex-col gap-4">
                
                {/* Risk gauge card */}
                <div className={`p-4 rounded-card border flex items-center justify-between ${
                  activeDistrictInfo.riskScore >= 75 
                    ? 'bg-[#C94A2A]/5 border-[#C94A2A]/20 text-[#C94A2A]' 
                    : 'bg-[#0E9E78]/5 border-[#0E9E78]/20 text-[#0E9E78]'
                }`}>
                  <div>
                    <span className="text-[9px] font-mono uppercase tracking-widest text-[#627a96] block">
                      Active Threat Score
                    </span>
                    <span className="text-2xl font-mono font-extrabold mt-0.5 block">
                      {activeDistrictInfo.riskScore}/100
                    </span>
                  </div>
                  <div className={`p-2 rounded-full ${
                    activeDistrictInfo.riskScore >= 75 ? 'bg-red-500/10' : 'bg-emerald-500/10'
                  }`}>
                    <AlertTriangle className="w-6 h-6 animate-pulse" />
                  </div>
                </div>

                {/* Primary Stats lists */}
                <div className="space-y-3 font-mono text-xs">
                  <div className="flex justify-between py-1.5 border-b border-slate-900">
                    <span className="text-[#6A7A96]">Monthly FIR Total</span>
                    <span className="text-white font-bold">{activeDistrictInfo.crimeCount} filings</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-900">
                    <span className="text-[#6A7A96]">Beat coverage Ratio</span>
                    <span className="text-white font-bold">{activeDistrictInfo.beatRatio}% efficiency</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-slate-900">
                    <span className="text-[#6A7A96]">Emerging Crime</span>
                    <span className="text-orange-400 font-semibold">{activeDistrictInfo.topCrimeType}</span>
                  </div>
                  
                  <div className="flex justify-between py-1.5 border-b border-slate-900 items-center">
                    <span className="text-[#6A7A96]">Weekly Trend Direction</span>
                    {activeDistrictInfo.weeklyTrend === 'up' ? (
                      <span className="text-red-500 font-bold flex items-center gap-1">
                        <TrendingUp className="w-3.5 h-3.5" />
                        SPIKING (+14%)
                      </span>
                    ) : activeDistrictInfo.weeklyTrend === 'down' ? (
                      <span className="text-emerald-500 font-bold flex items-center gap-1">
                        <TrendingDown className="w-3.5 h-3.5" />
                        DECLINING (-8%)
                      </span>
                    ) : (
                      <span className="text-blue-400 font-bold">STABILIZED</span>
                    )}
                  </div>
                </div>

                {/* Actionable recommendation block */}
                <div className="mt-4 p-3 bg-slate-950/40 border border-slate-800 rounded-btn">
                  <span className="text-[8px] font-bold font-mono text-[#1E6FD9] uppercase tracking-wider block mb-1">
                    SCRB Analyst Notes
                  </span>
                  <p className="text-[10px] leading-relaxed text-[#A8B4CC]">
                    {activeDistrictInfo.name === 'Bengaluru Urban' 
                      ? 'Deploy additional late evening cyber cyber-cell beats. Coordinate forensic units to target card-reading clone operations.'
                      : 'Patrol units suggest minor thefts under control. Proceed holding current shift deployment.'}
                  </p>
                </div>

              </div>
            </div>

            {/* Quick Action bar */}
            <div className="pt-4 border-t border-border-color">
              <button
                onClick={() => {
                  downloadSecureDossier(
                    `${activeDistrictInfo.name} Regional Dossier`, 
                    activeDistrictInfo, 
                    user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE'
                  );
                  if (user) {
                    addLog(
                      user.name,
                      user.badgeId,
                      'EXPORT',
                      `Exported regional dossier for ${activeDistrictInfo.name}`
                    );
                  }
                }}
                className="w-full py-2 bg-[#1E6FD9] hover:bg-[#1E6FD9]/80 text-white font-mono text-[10px] uppercase rounded-btn tracking-wider font-semibold cursor-pointer text-center select-none"
              >
                Export Regional Dossier (PDF)
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* BOTTOM SLIDER */}
      <div className="p-4 z-20">
        <TimeSlider />
      </div>

    </div>
  );
};

export default KarnatakaMap;
export { projectLonX, projectLatY };
