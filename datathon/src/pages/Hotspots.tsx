import React, { useEffect, useState, useMemo } from 'react';
import KarnatakaMap, { type EmergingTrendItem } from '../components/map/KarnatakaMap';
import SpatiotemporalHeatmap from '../components/dashboard/SpatiotemporalHeatmap';
import { 
  Compass, Download, Flame, TrendingUp,
  BarChart3, Map as MapIcon, ChevronRight
} from 'lucide-react';
import { downloadSecureDossier } from '../utils/downloader';
import { useAuditStore } from '../store/auditStore';
import { useAuthStore } from '../store/authStore';
import { useMapStore } from '../store/mapStore';
import { useNotificationStore } from '../store/notificationStore';
import { 
  getDistrictComparison, getHotspots, getRiskScores, getEmergingTrends, getRecentIncidents, getCrimeCases,
  getSociologicalSocioeconomic, getAnomalies,
  type DistrictComparisonPoint, type HotspotPoint, type RiskScoresResponse
} from '../services/api';
import type { DistrictInfo } from '../store/mapStore';
import { PageHeader } from '../components/ui/PageHeader';
import { PageSkeleton } from '../components/ui/Skeleton';

const BASELINE_HOTSPOTS: HotspotPoint[] = [
  { district_id: 'Ballari', name: 'City Police Station', lat: 15.14, lng: 76.91, score: 96, category: 'Domestic Violence', trend: 'up' },
  { district_id: 'Bengaluru Urban', name: 'Whitefield Police Station', lat: 12.9698, lng: 77.75, score: 94, category: 'Cyber Crime & Online Fraud', trend: 'stable' },
  { district_id: 'Bengaluru Urban', name: 'Jayanagar Police Station', lat: 12.926, lng: 77.583, score: 92, category: 'Narcotics Smuggling Services', trend: 'down' },
  { district_id: 'Mysuru', name: 'Devaraja Police Station', lat: 12.305, lng: 76.648, score: 88, category: 'Theft & Burglaries', trend: 'up' },
  { district_id: 'Dakshina Kannada', name: 'Surathkal Police Station', lat: 12.98, lng: 74.86, score: 85, category: 'Cyber Crime & Online Fraud', trend: 'stable' },
  { district_id: 'Belagavi', name: 'Khade Bazar Police Station', lat: 15.85, lng: 74.51, score: 82, category: 'Smuggling & Excise Violations', trend: 'down' },
  { district_id: 'Kalaburagi', name: 'Brahmapur Police Station', lat: 17.33, lng: 76.84, score: 80, category: 'Property Disputes', trend: 'up' },
  { district_id: 'Hassan', name: 'Hassan City Police Station', lat: 13.01, lng: 76.10, score: 76, category: 'Domestic Violence', trend: 'down' },
];

export const Hotspots: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const { selectedDistrict, setSelectedDistrict, setSelectedStation, setTimeOfDay, timeOfDay } = useMapStore();

  const [hotspots, setHotspots] = useState<HotspotPoint[]>(BASELINE_HOTSPOTS);
  const [districtMetrics, setDistrictMetrics] = useState<Record<string, DistrictInfo>>({});
  const [emergingTrends, setEmergingTrends] = useState<EmergingTrendItem[]>([]);
  const [recentCases, setRecentCases] = useState<any[]>([]);
  const [socioEconomicData, setSocioEconomicData] = useState<any[]>([]);
  const [anomaliesList, setAnomaliesList] = useState<any[]>([]);
  const [viewMode, setViewMode] = useState<'map' | 'matrix'>('map');
  const [selectedCategoryFilter] = useState<string>('ALL');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    // Check if navigating from Anomaly "Locate on Map"
    const override = sessionStorage.getItem('selected_district_override');
    if (override) {
      sessionStorage.removeItem('selected_district_override');
      setSelectedDistrict(override);
      setSelectedStation(null);
    }

    // 1. Primary fast load: Hotspots + District Comparison
    void Promise.allSettled([
      getHotspots(),
      getDistrictComparison(),
    ]).then(([hotspotRes, districtRes]) => {
      if (!isMounted) return;
      const hsList = hotspotRes.status === 'fulfilled' && hotspotRes.value.hotspots?.length > 0 ? hotspotRes.value.hotspots : BASELINE_HOTSPOTS;
      const distList = districtRes.status === 'fulfilled' ? districtRes.value : [];
      setHotspots(hsList);
      setDistrictMetrics(prev => ({
        ...prev,
        ...buildDistrictMetrics(distList, { district_id: null, window: 'next_7d', grid_predictions: [], model_version: '' }, hsList)
      }));
    }).catch(() => undefined);

    // 2. Secondary progressive load: Emerging Trends, Recent Cases, Socio-Economic, & Anomalies
    void getEmergingTrends().then(trendsData => {
      if (isMounted && Array.isArray(trendsData)) {
        setEmergingTrends(trendsData);
        // Automatically dispatch spike notifications for significant surging categories (>10%)
        const surges = trendsData.filter((t: any) => t.direction === 'increasing' && t.change_percentage > 10);
        if (surges.length > 0) {
          surges.slice(0, 2).forEach((surge: any) => {
            void useNotificationStore.getState().sendNotification({
              subject: `CRIME SURGE ALERT: ${surge.category}`,
              title: `Trend Spike in ${surge.category}`,
              message: `Telemetry detected a +${surge.change_percentage}% spike (${surge.recent_count} recent vs ${surge.historical_count} baseline). Red-zone map monitoring activated.`,
              category: 'SPIKE_ALERT',
              priority: 'urgent',
              severity: 'critical',
              is_broadcast: true,
            }).catch(() => undefined);
          });
        }
      }
    }).catch(() => undefined);

    void getSociologicalSocioeconomic().then(socioRes => {
      if (isMounted && Array.isArray(socioRes?.districts)) {
        setSocioEconomicData(socioRes.districts);
      }
    }).catch(() => undefined);

    void getAnomalies().then(anomRes => {
      if (isMounted && Array.isArray(anomRes?.anomalies)) {
        setAnomaliesList(anomRes.anomalies);
      }
    }).catch(() => undefined);

    void Promise.allSettled([
      getRecentIncidents(),
      getCrimeCases('', undefined, 1, 50),
    ]).then(([recentRes, casesRes]) => {
      if (!isMounted) return;
      const recentList = recentRes.status === 'fulfilled' ? recentRes.value : [];
      const paginatedList = casesRes.status === 'fulfilled' ? (casesRes.value?.results || []) : [];
      
      // Combine and normalize cases
      const map = new Map<string, any>();
      [...recentList, ...paginatedList].forEach((c: any) => {
        const id = c.case_number || c.id;
        if (id && !map.has(id)) {
          map.set(id, {
            ...c,
            crime_type: c.crime_type || c.category || 'Incident Offense',
            location: c.location || c.station || '',
            priority: c.priority || 'medium',
            status: c.status || 'Active',
            time: c.time || c.occurred_at || c.created_at,
          });
        }
      });
      setRecentCases(Array.from(map.values()));
    }).catch(() => undefined);

    // 3. Background AI risk predictions (non-blocking)
    void getRiskScores().then(riskData => {
      if (isMounted && riskData?.grid_predictions) {
        setDistrictMetrics(prev => {
          const updated = { ...prev };
          riskData.grid_predictions.forEach(item => {
            if (updated[item.district]) {
              updated[item.district] = {
                ...updated[item.district],
                riskScore: Math.round(item.risk_score),
              };
            }
          });
          return updated;
        });
      }
    }).catch(() => undefined);

    return () => {
      isMounted = false;
    };
  }, []);

  // Filtered hotspots by category if specified
  const filteredHotspots = useMemo(() => {
    if (selectedCategoryFilter === 'ALL') return hotspots;
    return hotspots.filter(h => (h.category || '').toLowerCase().includes(selectedCategoryFilter.toLowerCase()));
  }, [hotspots, selectedCategoryFilter]);

  // High priority emerging trend alerts (increasing by >10%)
  const activeAlertSurges = useMemo(() => {
    return emergingTrends.filter(t => t.direction === 'increasing' && t.change_percentage > 10);
  }, [emergingTrends]);

  // Top telemetry cards: Show active district's stations if selected, otherwise statewide top 3
  const displayedTopHotspots = useMemo(() => {
    if (selectedDistrict) {
      const targetDist = (selectedDistrict || '').toLowerCase();
      const districtHotspots = filteredHotspots.filter(
        h => (h.district_id || '').toLowerCase() === targetDist
      );
      if (districtHotspots.length > 0) {
        return districtHotspots.slice(0, 3);
      }
    }
    return filteredHotspots.slice(0, 3);
  }, [filteredHotspots, selectedDistrict]);

  const handleExportGeoJSON = () => {
    const geojsonData = {
      type: 'FeatureCollection',
      features: filteredHotspots.map((hotspot) => ({
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
        <PageHeader title="Spatiotemporal Hotspots" subtitle="Loading geospatial data & temporal telemetry…" icon={<Compass className="w-5 h-5" />} />
        <PageSkeleton />
      </div>
    );
  }

  if (error && hotspots.length === 0) {
    return (
      <div className="h-[84vh] flex flex-col gap-4 md:p-1">
        <PageHeader title="Spatiotemporal Hotspots" icon={<Compass className="w-5 h-5" />} />
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
        title="Spatiotemporal Crime Cluster & Hotspots"
        subtitle="Geospatial incident density & interactive temporal shift analysis across Karnataka"
        icon={<Compass className="w-5 h-5" />}
        actions={
          <div className="flex items-center gap-2">
            {/* View Mode Toggle */}
            <div className="flex bg-[var(--bg-secondary)] border border-[var(--border-primary)] rounded p-0.5">
              <button
                onClick={() => setViewMode('map')}
                className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer ${
                  viewMode === 'map' ? 'bg-[var(--accent-blue)] text-white shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <MapIcon className="w-3.5 h-3.5" />
                Vector Map
              </button>
              <button
                onClick={() => setViewMode('matrix')}
                className={`px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1 transition-colors cursor-pointer ${
                  viewMode === 'matrix' ? 'bg-[var(--accent-blue)] text-white shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Spatiotemporal Matrix
              </button>
            </div>

            <button onClick={handleExportGeoJSON} className="sk-btn sk-btn-secondary">
              <Download className="w-4 h-4" />
              GeoJSON Export
            </button>
          </div>
        }
      />

      {/* EMERGING TREND ALERTS REAL-TIME TICKER (Surge alerts > 10%) */}
      {activeAlertSurges.length > 0 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 flex flex-col md:flex-row md:items-center justify-between gap-2 font-mono text-[9px]">
          <div className="flex items-center gap-2 shrink-0">
            <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 font-bold uppercase flex items-center gap-1 animate-pulse border border-red-500/40">
              <Flame className="w-3 h-3 text-red-400" />
              Emerging Trend Alerts
            </span>
            <span className="text-[var(--text-secondary)] hidden lg:inline">
              Crime categories exhibiting significant surge vs 30-day baseline:
            </span>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto no-scrollbar">
            {activeAlertSurges.slice(0, 3).map((trend) => (
              <button
                key={trend.category}
                onClick={() => {
                  // Find a district associated with this top category or default to Bengaluru Urban
                  const matchingDist = Object.values(districtMetrics).find(d => d.topCrimeType.toLowerCase().includes(trend.category.toLowerCase()))?.name || 'Bengaluru Urban';
                  setSelectedDistrict(matchingDist);
                  setSelectedStation(null);
                }}
                className="px-2 py-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/40 rounded flex items-center gap-1.5 cursor-pointer text-left transition-colors shrink-0"
                title={`Click to focus map on districts experiencing ${trend.category} surge`}
              >
                <span className="font-bold text-red-300">{trend.category}:</span>
                <span className="text-red-400 font-extrabold flex items-center gap-0.5">
                  <TrendingUp className="w-3 h-3" />
                  +{trend.change_percentage}%
                </span>
                <span className="text-[8px] text-[var(--text-muted)] hidden sm:inline">
                  ({trend.recent_count} vs {trend.historical_count} baseline)
                </span>
                <ChevronRight className="w-2.5 h-2.5 text-red-400" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* TOP SUMMARY TELEMETRY CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {displayedTopHotspots.map((hotspot) => (
          <div 
            key={`${hotspot.name}-${hotspot.district_id}`} 
            onClick={() => {
              setSelectedDistrict(hotspot.district_id);
              setSelectedStation(hotspot.name);
            }}
            className="sk-panel px-4 py-3 flex items-center justify-between gap-3 cursor-pointer hover:border-[var(--accent-blue)]/60 transition-all shadow-sm"
          >
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

      {/* MAIN VISUALIZATION VIEWPORT */}
      <div className="w-full relative min-h-[580px] h-[620px]">
        {viewMode === 'map' ? (
          <KarnatakaMap 
            hotspots={filteredHotspots} 
            districtDataOverride={districtMetrics}
            emergingTrends={emergingTrends}
            crimeCases={recentCases}
            socioEconomicData={socioEconomicData}
            anomaliesList={anomaliesList}
          />
        ) : (
          <div className="w-full h-full">
            <SpatiotemporalHeatmap 
              selectedHour={timeOfDay} 
              onCellClick={(_day, hour) => {
                const h = parseInt(hour.split(':')[0], 10);
                setTimeOfDay(h);
                setViewMode('map');
              }}
            />
          </div>
        )}
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
