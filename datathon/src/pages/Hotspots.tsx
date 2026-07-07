import React, { useEffect, useState } from 'react';
import KarnatakaMap from '../components/map/KarnatakaMap';
import { Compass, Download, ShieldAlert } from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { getHotspots, type HotspotPoint } from '../services/api';

export const Hotspots: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const [hotspots, setHotspots] = useState<HotspotPoint[]>([]);

  useEffect(() => {
    let isMounted = true;

    void getHotspots()
      .then((response) => {
        if (isMounted) {
          setHotspots(response.hotspots);
        }
      })
      .catch(() => {
        if (isMounted) {
          setHotspots([]);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleExportGeoJSON = () => {
    const exportHotspots = hotspots.length ? hotspots : [
      { district_id: 'Bengaluru Urban', name: 'Whitefield', lat: 12.9698, lng: 77.7500, score: 91, category: 'Cyber Fraud', trend: 'up' },
      { district_id: 'Mysuru', name: 'Mysuru Palace Gate', lat: 12.3021, lng: 76.6531, score: 54, category: 'Pickpocketing', trend: 'stable' },
      { district_id: 'Kalaburagi', name: 'Kalaburagi Outskirts', lat: 17.3350, lng: 76.8380, score: 72, category: 'Land Disputes', trend: 'up' },
    ];

    const geojsonData = {
      type: 'FeatureCollection',
      features: exportHotspots.map((hotspot) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [hotspot.lng, hotspot.lat] },
        properties: {
          name: hotspot.name,
          district: hotspot.district_id,
          threat: `${hotspot.score}%`,
          category: hotspot.category,
          trend: hotspot.trend,
        },
      }))
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 text-[9px] font-mono">
        {(hotspots.length ? hotspots : [
          { district_id: 'Bengaluru Urban', name: 'Whitefield', lat: 12.9698, lng: 77.7500, score: 91, category: 'Cyber Fraud', trend: 'up' },
          { district_id: 'Bengaluru Urban', name: 'KR Puram', lat: 13.0056, lng: 77.6880, score: 78, category: 'Vehicle Theft', trend: 'up' },
          { district_id: 'Mangaluru', name: 'Harbor Port', lat: 12.9050, lng: 74.8350, score: 72, category: 'Narcotics Transit', trend: 'up' },
        ]).slice(0, 3).map((hotspot) => (
          <div key={`${hotspot.name}-${hotspot.district_id}`} className="bg-[#0a1220]/80 border border-white/5 rounded-lg p-3 flex items-start justify-between gap-3">
            <div>
              <p className="text-white font-semibold uppercase tracking-wide">{hotspot.name}</p>
              <p className="text-[#6A7A96] mt-1">{hotspot.district_id} • {hotspot.category}</p>
            </div>
            <div className={`font-bold ${hotspot.score >= 80 ? 'text-[#C94A2A]' : hotspot.score >= 70 ? 'text-[#D4820A]' : 'text-[#0E9E78]'}`}>
              {hotspot.score}%
            </div>
          </div>
        ))}
      </div>

      {/* Map viewport */}
      <div className="flex-grow w-full relative">
        <KarnatakaMap />
      </div>

    </div>
  );
};

export default Hotspots;
