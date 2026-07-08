import React from 'react';
import KarnatakaMap from '../components/map/KarnatakaMap';
import { Compass, Download, ShieldAlert } from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';

export const Hotspots: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  const handleExportGeoJSON = () => {
    const geojsonData = {
      type: 'FeatureCollection',
      features: [
        { type: 'Feature', geometry: { type: 'Point', coordinates: [77.5946, 12.9716] }, properties: { name: 'Bengaluru Urban', threat: '88%' } },
        { type: 'Feature', geometry: { type: 'Point', coordinates: [76.6394, 12.2958] }, properties: { name: 'Mysuru', threat: '54%' } },
        { type: 'Feature', geometry: { type: 'Point', coordinates: [76.8343, 17.3297] }, properties: { name: 'Kalaburagi', threat: '72%' } }
      ]
    };

    downloadSecureDossier(
      'Statewide Hotspots GeoJSON', 
      geojsonData, 
      user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE'
    );

    if (user) {
      addLog(
        user.name,
        user.badgeId,
        'EXPORT',
        'Exported statewide incident hotspots overlay database (GEOJSON)'
      );
    }
  };

  return (
    <div className="h-[84vh] flex flex-col gap-4 p-1 md:p-3 select-none bg-[#060b13]">
      
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-white/5 pb-3">
        <div>
          <h2 className="text-md font-mono font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Compass className="w-4 h-4 text-[#1E6FD9] animate-pulse" />
            District Hotspot Analysis Map
          </h2>
          <p className="text-[9.5px] font-mono text-[#6A7A96] mt-0.5">
            GEOSPATIAL INCIDENT GRID OVERLAY — MAPBOX DUST COORDS & DECK.GL SCATTER PLOTS
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-[9px] uppercase">
          <button
            onClick={handleExportGeoJSON}
            className="px-2.5 py-1.5 bg-[#111D35] hover:bg-[#1E6FD9]/15 border border-border-color hover:border-[#1E6FD9]/30 text-[#A8B4CC] hover:text-white rounded-btn transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Download className="w-3 h-3" />
            GEOJSON Export
          </button>
        </div>
      </div>

      {/* Map viewport */}
      <div className="flex-grow w-full relative">
        <KarnatakaMap />
      </div>

    </div>
  );
};

export default Hotspots;
