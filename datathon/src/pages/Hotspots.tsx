import React, { useEffect, useState } from 'react';
import KarnatakaMap from '../components/map/KarnatakaMap';
import { Compass, Download } from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { getDistrictComparison, getHotspots, getRiskScores, type DistrictComparisonPoint, type HotspotPoint, type RiskScoresResponse } from '../services/api';
import type { DistrictInfo } from '../store/mapStore';
import { PageHeader } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';

export const Hotspots: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const [hotspots, setHotspots] = useState<HotspotPoint[]>([]);
  const [districtMetrics, setDistrictMetrics] = useState<Record<string, DistrictInfo>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
          setError('Failed to load hotspot data. Please try again.');
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
      <div className="h-[84vh] flex flex-col gap-4 md:p-1">
        <PageHeader title="Hotspot Map" subtitle="Loading geospatial data…" icon={<Compass className="w-5 h-5" />} />
        <PageSkeleton />
      </div>
    );
  }

  if (error && hotspots.length === 0) {
    return (
      <div className="h-[84vh] flex flex-col gap-4 md:p-1">
        <PageHeader title="Hotspot Map" icon={<Compass className="w-5 h-5" />} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-3">
            <div className="w-12 h-12 rounded-xl bg-[var(--accent-coral-subtle)] border border-[var(--accent-coral)]/20 flex items-center justify-center mx-auto text-[var(--accent-coral)]">
              <Compass className="w-6 h-6" />
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{error}</p>
            <button onClick={() => { setError(null); setLoading(true); window.location.reload(); }} className="sk-btn sk-btn-primary">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[84vh] flex flex-col gap-4 md:p-1">

      {/* Page header */}
      <PageHeader
        title="Hotspot Map"
        subtitle="Geospatial incident density across Karnataka districts"
        icon={<Compass className="w-5 h-5" />}
        actions={
          <button onClick={handleExportGeoJSON} className="sk-btn sk-btn-secondary">
            <Download className="w-4 h-4" />
            GeoJSON Export
          </button>
        }
      />

      {/* Top hotspots strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {hotspots.slice(0, 3).map((hotspot) => (
          <div key={`${hotspot.name}-${hotspot.district_id}`} className="sk-panel px-4 py-3 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-[var(--text-primary)] truncate">{hotspot.name}</p>
              <p className="text-xs text-[var(--text-muted)] truncate">{hotspot.district_id} · {hotspot.category}</p>
            </div>
            <span
              className={`sk-chip shrink-0 ${hotspot.score >= 80 ? 'sk-chip-error' : hotspot.score >= 70 ? 'sk-chip-warning' : 'sk-chip-success'}`}
            >
              {hotspot.score}%
            </span>
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
