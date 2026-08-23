import React, { useState, useEffect } from 'react';
import { useMapStore, DISTRICT_COORDS } from '../../store/mapStore';
import type { HotspotPoint } from '../../services/api';
import type { DistrictInfo } from '../../store/mapStore';
import TimeSlider from './TimeSlider';
import { Shield, X, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { downloadSecureDossier } from '../../utils/downloader';
import { useAuditStore } from '../../store/auditStore';
import { useAuthStore } from '../../store/authStore';
import { useThemePalettes } from '../../theme';
import { useAppStore } from '../../store/appStore';

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
  'Dakshina Kannada': [
    [74.7, 13.1], [75.4, 13.0], [75.4, 12.5], [74.8, 12.6], [74.6, 12.9]
  ]
};

interface KarnatakaMapProps {
  hotspots?: HotspotPoint[];
  districtDataOverride?: Record<string, DistrictInfo>;
}

export const KarnatakaMap: React.FC<KarnatakaMapProps> = ({ hotspots = [], districtDataOverride }) => {
  const {
    selectedDistrict,
    layers,
    districtData,
    setSelectedDistrict,
    toggleLayer
  } = useMapStore();

  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const theme = useAppStore((s) => s.theme);
  const palette = useThemePalettes();
  const map = palette.map;

  const [panelOpen, setPanelOpen] = useState(false);
  const [mapZoom, setMapZoom] = useState(1);
  const [mapOffset, setMapOffset] = useState({ x: 0, y: 0 });
  const [selectedHotspot, setSelectedHotspot] = useState<any | null>(null);

  // Open details panel when a district is selected
  useEffect(() => {
    if (selectedDistrict) {
      setPanelOpen(true);
    } else {
      setPanelOpen(false);
      setSelectedHotspot(null);
    }
  }, [selectedDistrict]);

  const activeHotspots = hotspots.map((hotspot) => ({
    name: hotspot.name,
    lat: hotspot.lat,
    lng: hotspot.lng,
    weight: hotspot.score,
    type: hotspot.category,
    district_id: hotspot.district_id,
  }));
  const resolvedDistrictData = districtDataOverride ?? districtData;
  const activeDistrictInfo = selectedDistrict ? resolvedDistrictData[selectedDistrict] : null;

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
    <div className="w-full h-full relative overflow-hidden flex flex-col justify-between bg-[var(--bg-surface)] rounded-card border border-border-color">
      
      {/* MAP HEADER PANELS */}
      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2 max-w-xs pointer-events-none select-none">
        <div className="px-3 py-2 bg-secondary-bg/95 backdrop-blur-md border border-border-color rounded-card pointer-events-auto">
          <span className="text-[10px] font-mono text-[var(--accent-teal)] uppercase font-bold tracking-wider">
            Vector Grid Telemetry
          </span>
          <h3 className="text-[13px] font-mono font-bold text-[var(--text-primary)] mt-0.5">
            {selectedDistrict ? `Focus: ${selectedDistrict}` : 'Statewide Overview'}
          </h3>
          <p className="text-[9px] font-mono text-[var(--text-muted)] mt-1 select-none">
            LAT/LON D3 GEODESIC AUTO-CENTERING
          </p>
        </div>

        {/* LAYER SELECTORS */}
        <div className="px-3 py-2 bg-secondary-bg/95 backdrop-blur-md border border-border-color rounded-card pointer-events-auto flex flex-col gap-1.5">
          <span className="text-[8px] font-mono uppercase tracking-widest text-[var(--text-muted)] mb-1">
            Display Layers
          </span>
          <button
            onClick={() => toggleLayer('hotspot')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.hotspot 
                ? 'bg-[var(--accent-blue)]/15 border-[var(--accent-blue)] text-[var(--accent-blue)]' 
                : 'bg-transparent border-[var(--border-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            <span>Hotspots Data</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.hotspot ? 'bg-[var(--accent-blue)] animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          </button>
          
          <button
            onClick={() => toggleLayer('beatCoverage')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.beatCoverage 
                ? 'bg-[var(--accent-teal)]/15 border-[var(--accent-teal)] text-[var(--accent-teal)]' 
                : 'bg-transparent border-[var(--border-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            <span>Beat Officer Ratio</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.beatCoverage ? 'bg-[var(--accent-teal)] animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          </button>
          
          <button
            onClick={() => toggleLayer('riskScore')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.riskScore 
                ? 'bg-[var(--accent-purple)]/15 border-[var(--accent-purple)] text-[var(--accent-purple)]' 
                : 'bg-transparent border-[var(--border-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            <span>Regional Risk Index</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.riskScore ? 'bg-[var(--accent-purple)] animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          </button>
        </div>
      </div>

      {/* RENDER CANVAS CONTAINER */}
      <div className="flex-1 w-full relative cursor-grab active:cursor-grabbing overflow-hidden" style={{ backgroundColor: map.bg }}>

        {/* GEODESIC BACKGROUND GRID */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke={map.grid} strokeWidth="0.5" />
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
          <g stroke={map.graticule} strokeWidth="0.5" strokeDasharray="3 3">
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
              const info = resolvedDistrictData[name];

              // Color coding based on active layers — theme-aware palette
              let fill = map.districtFill;
              let stroke = map.boundary;

              if (layers.riskScore && info) {
                const rs = info.riskScore;
                fill = rs >= 80
                  ? `rgba(217, 52, 20, ${theme === 'dark' ? 0.35 : 0.28})`
                  : rs >= 60
                  ? `rgba(181, 110, 7, ${theme === 'dark' ? 0.35 : 0.30})`
                  : `rgba(13, 122, 91, ${theme === 'dark' ? 0.25 : 0.22})`;
              } else if (layers.beatCoverage && info) {
                const br = info.beatRatio;
                fill = br >= 75
                  ? theme === 'dark' ? 'rgba(20, 201, 151, 0.30)' : 'rgba(5, 150, 105, 0.26)'
                  : br >= 60
                  ? theme === 'dark' ? 'rgba(61, 138, 240, 0.25)' : 'rgba(37, 99, 235, 0.20)'
                  : theme === 'dark' ? 'rgba(240, 156, 46, 0.25)' : 'rgba(217, 119, 6, 0.24)';
              }

              if (isSelected) {
                fill = map.districtSelected;
                stroke = map.boundaryHover;
              }

              return (
                <polygon
                  key={name}
                  points={projectedPoints}
                  className="transition-all duration-300 cursor-pointer"
                  style={{ fill }}
                  stroke={stroke}
                  strokeWidth={isSelected ? 2.25 : 1.25}
                  onMouseEnter={(e) => { if (!isSelected) { e.currentTarget.style.fill = map.districtSelected; e.currentTarget.style.stroke = map.boundaryHover; } }}
                  onMouseLeave={(e) => { e.currentTarget.style.fill = fill; e.currentTarget.style.stroke = stroke; }}
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
                    r={isSelected ? 4 : 2.4}
                    fill={isSelected ? map.boundaryHover : map.anchor}
                  />
                  {/* District text tag — bg-stroked for legibility in both themes */}
                  <text
                    x={x + 6.5}
                    y={y + 3.5}
                    className="font-mono text-[9px] font-semibold"
                    style={{ paintOrder: 'stroke', stroke: map.bg, strokeWidth: 3, strokeLinejoin: 'round' }}
                    fill={isSelected ? map.label : map.label}
                    opacity={isSelected ? 1 : 0.9}
                  >
                    {name}
                  </text>
                </g>
              );
            })}
          </g>

          {/* HOTSPOT PULSING RING LAYERS */}
          {layers.hotspot && (
            <g>
              {activeHotspots.map((hs, index) => {
                const x = projectLonX(hs.lng);
                const y = projectLatY(hs.lat);
                const isHigh = hs.weight >= 80;

                // Theme-aware severity colors with white core outline so the
                // marker never disappears against either background.
                const color = isHigh ? map.hotspotHigh : hs.weight >= 65 ? map.hotspotMedium : map.hotspotLow;
                const isSelected = selectedHotspot && selectedHotspot.name === hs.name;

                return (
                  <g
                    key={index}
                    className="cursor-pointer pointer-events-auto"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (hs.district_id) {
                        setSelectedDistrict(hs.district_id);
                      }
                      setSelectedHotspot(hs);
                    }}
                  >
                    {/* Concentric pulsing rings */}
                    <circle cx={x} cy={y} r={14} fill={color} opacity={map.haloOpacity} className="animate-ping" style={{ transformOrigin: `${x}px ${y}px`, animationDuration: '2s' }} />
                    <circle cx={x} cy={y} r={28} stroke={color} strokeWidth="1" fill="none" opacity={map.haloOpacity * 0.6} className="animate-ping" style={{ transformOrigin: `${x}px ${y}px`, animationDuration: '3s' }} />

                    {/* Center Core dot — outlined for contrast on any surface */}
                    <circle cx={x} cy={y} r={isHigh ? 8.5 : 7} fill={map.bg} />
                    <circle cx={x} cy={y} r={isHigh ? 6 : 4.5} fill={color} stroke={map.bg} strokeWidth="1.5" />
                    <circle cx={x} cy={y} r={isHigh ? 9.5 : 8} stroke={color} strokeWidth="1.25" fill="none" opacity={0.75} />

                    {/* Popover Tooltip inside foreignObject so it scales with map view zoom & pan */}
                    {isSelected && (
                      <foreignObject x={x - 90} y={y - 120} width="180" height="110" className="z-50 pointer-events-auto">
                        <div
                          className="p-2.5 rounded-lg text-left flex flex-col gap-1.5 font-mono text-[10px] leading-tight relative shadow-lg"
                          style={{ backgroundColor: palette.chart.tooltipBg, border: `1px solid ${palette.chart.tooltipBorder}`, color: palette.chart.tooltipText }}
                        >
                          <div className="flex justify-between items-center pb-1" style={{ borderColor: palette.chart.tooltipBorder, borderBottomWidth: 1 }}>
                            <span className="font-bold uppercase text-[9px]" style={{ color: map.hotspotMedium }}>Hotspot Details</span>
                            <button
                              onClick={(e) => { e.stopPropagation(); setSelectedHotspot(null); }}
                              className="cursor-pointer font-bold text-xs"
                              style={{ color: palette.chart.axis }}
                            >
                              ×
                            </button>
                          </div>
                          <div>
                            <p className="font-bold uppercase truncate">{hs.name}</p>
                            <p className="opacity-70 mt-0.5 truncate">Sector: {hs.district_id}</p>
                            <p className="opacity-85 mt-0.5 truncate">Category: {hs.type}</p>
                            <p className="font-bold mt-0.5" style={{ color: color }}>Threat Level: {hs.weight}%</p>
                          </div>
                        </div>
                      </foreignObject>
                    )}
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
            className="absolute bottom-4 left-4 z-20 px-3 py-1.5 bg-[var(--accent-coral)] hover:opacity-90 text-white font-medium text-xs rounded-md flex items-center gap-1 shadow-sm cursor-pointer"
          >
            <span>Reset View</span>
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
                  <Shield className="w-5 h-5 text-[var(--accent-blue)] shrink-0" />
                  <h3 className="text-sm font-mono font-bold text-[var(--text-primary)] uppercase truncate">
                    {activeDistrictInfo.name}
                  </h3>
                </div>
                <button
                  onClick={() => setPanelOpen(false)}
                  className="p-1 hover:bg-[var(--accent-blue)]/15 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Data overview block */}
              <div className="flex flex-col gap-4">
                
                {/* Risk gauge card */}
                <div className={`p-4 rounded-card border flex items-center justify-between ${
                  activeDistrictInfo.riskScore >= 75 
                    ? 'bg-[var(--accent-coral)]/5 border-[var(--accent-coral)]/20 text-[var(--accent-coral)]' 
                    : 'bg-[var(--accent-teal)]/5 border-[var(--accent-teal)]/20 text-[var(--accent-teal)]'
                }`}>
                  <div>
                    <span className="text-[9px] font-mono uppercase tracking-widest text-[var(--text-muted)] block">
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
                  <div className="flex justify-between py-1.5 border-b border-[var(--border-primary)]">
                    <span className="text-[var(--text-muted)]">Monthly FIR Total</span>
                    <span className="text-[var(--text-primary)] font-bold">{activeDistrictInfo.crimeCount} filings</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[var(--border-primary)]">
                    <span className="text-[var(--text-muted)]">Beat coverage Ratio</span>
                    <span className="text-[var(--text-primary)] font-bold">{activeDistrictInfo.beatRatio}% efficiency</span>
                  </div>
                  <div className="flex justify-between py-1.5 border-b border-[var(--border-primary)]">
                    <span className="text-[var(--text-muted)]">Emerging Crime</span>
                    <span className="text-orange-400 font-semibold">{activeDistrictInfo.topCrimeType}</span>
                  </div>
                  
                  <div className="flex justify-between py-1.5 border-b border-[var(--border-primary)] items-center">
                    <span className="text-[var(--text-muted)]">Weekly Trend Direction</span>
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
                <div className="mt-4 p-3 bg-[var(--bg-secondary)]/40 border border-[var(--border-primary)] rounded-btn">
                  <span className="text-[8px] font-bold font-mono text-[var(--accent-blue)] uppercase tracking-wider block mb-1">
                    SCRB Analyst Notes
                  </span>
                  <p className="text-[10px] leading-relaxed text-[var(--text-secondary)]">
                    Backend-derived from active FIRs, linked crime cases, risk scores, and dominant category for this district.
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
                className="w-full py-2.5 bg-[var(--accent-blue)] hover:bg-[var(--accent-blue-light)] text-white font-semibold text-[13px] rounded-md cursor-pointer text-center select-none transition-colors"
              >
                Export Regional Dossier
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

