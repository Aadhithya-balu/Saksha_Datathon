import React, { useEffect, useState } from 'react';
import KarnatakaMap from '../components/map/KarnatakaMap';
import { Compass, Download, Loader2 } from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { getDistrictComparison, getHotspots, getRiskScores, type DistrictComparisonPoint, type HotspotPoint, type RiskScoresResponse } from '../services/api';
import type { DistrictInfo } from '../store/mapStore';
import { PageSkeleton } from '../components/ui/Skeleton';

export const Hotspots: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const [hotspots, setHotspots] = useState<HotspotPoint[]>([]);
  const [districtMetrics, setDistrictMetrics] = useState<Record<string, DistrictInfo>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    void Promise.all([getHotspots(), getDistrictComparison(), getRiskScores()])
      .then(([hotspotResponse, districtResponse, riskResponse]) => {
        if (isMounted) {
          setHotspots(hotspotResponse.hotspots);
          setDistrictMetrics(buildDistrictMetrics(districtResponse, riskResponse, hotspotResponse.hotspots));
        }
      })
      .catch(() => {
        if (isMounted) {
          setHotspots([]);
          setDistrictMetrics({});
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handleExportGeoJSON = () => {
    const exportHotspots = hotspots;

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

  if (loading) {
    return (
      <div className="h-[84vh] flex flex-col gap-4 p-1 md:p-3 select-none bg-[var(--bg-primary)]">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3">
          <div>
            <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
              <Compass className="w-4 h-4 text-[#1E6FD9] animate-pulse" />
              District Hotspot Analysis Map
            </h2>
            <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
              Loading geospatial telemetry...
            </p>
          </div>
        </div>
        <PageSkeleton />
      </div>
    );
  }

  return (
    <div className="h-[84vh] flex flex-col gap-4 p-1 md:p-3 select-none bg-[var(--bg-primary)]">
      
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-[var(--border-muted)] pb-3">
        <div>
          <h2 className="text-md font-mono font-bold text-[var(--text-primary)] uppercase tracking-wider flex items-center gap-2">
            <Compass className="w-4 h-4 text-[#1E6FD9] animate-pulse" />
            District Hotspot Analysis Map
          </h2>
          <p className="text-[9.5px] font-mono text-[var(--text-muted)] mt-0.5">
            GEOSPATIAL INCIDENT GRID OVERLAY — MAPBOX DUST COORDS & DECK.GL SCATTER PLOTS
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-[9px] uppercase">
          <button
            onClick={handleExportGeoJSON}
            className="px-2.5 py-1.5 bg-[var(--bg-tertiary)] hover:bg-[#1E6FD9]/15 border border-border-color hover:border-[#1E6FD9]/30 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-btn transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <Download className="w-3 h-3" />
            GEOJSON Export
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 text-[9px] font-mono">
        {hotspots.slice(0, 3).map((hotspot) => (
          <div key={`${hotspot.name}-${hotspot.district_id}`} className="bg-[var(--bg-secondary)]/80 border border-[var(--border-muted)] rounded-lg p-3 flex items-start justify-between gap-3">
            <div>
              <p className="text-[var(--text-primary)] font-semibold uppercase tracking-wide">{hotspot.name}</p>
              <p className="text-[var(--text-muted)] mt-1">{hotspot.district_id} • {hotspot.category}</p>
            </div>
            <div className={`font-bold ${hotspot.score >= 80 ? 'text-[#C94A2A]' : hotspot.score >= 70 ? 'text-[#D4820A]' : 'text-[#0E9E78]'}`}>
              {hotspot.score}%
            </div>
          </div>
        ))}
      </div>

      {/* Map viewport */}
      <div className="flex-grow w-full relative">
        <KarnatakaMap hotspots={hotspots} districtDataOverride={districtMetrics} />
      </div>

    </div>
  );
};

export default Hotspots;

const buildDistrictMetrics = (
  districtRows: DistrictComparisonPoint[],
  riskScores: RiskScoresResponse,
  hotspots: HotspotPoint[]
): Record<string, DistrictInfo> => {
  const risks = new Map(riskScores.grid_predictions.map((item) => [item.district, item.risk_score]));
  return districtRows.reduce<Record<string, DistrictInfo>>((acc, row) => {
    const districtHotspots = hotspots.filter((hotspot) => hotspot.district_id === row.district);
    const topHotspot = districtHotspots[0];
    const avgRisk = risks.get(row.district) ?? Math.round(districtHotspots.reduce((sum, hotspot) => sum + hotspot.score, 0) / Math.max(districtHotspots.length, 1));
    acc[row.district] = {
      name: row.district,
      crimeCount: row.count,
      riskScore: Number.isFinite(avgRisk) ? avgRisk : 0,
      beatRatio: Math.max(35, 100 - (Number.isFinite(avgRisk) ? avgRisk : 0)),
      topCrimeType: topHotspot?.category ?? 'No active category',
      weeklyTrend: topHotspot?.trend === 'up' ? 'up' : topHotspot?.trend === 'down' ? 'down' : 'stable',
    };
    return acc;
  }, {});
};
