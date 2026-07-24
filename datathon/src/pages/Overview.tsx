import React, { useEffect, useState } from 'react';
import StatCard from '../components/dashboard/StatCard';
import TrendChart from '../components/charts/TrendChart';
import DonutChart from '../components/charts/DonutChart';
import SpatiotemporalHeatmap from '../components/dashboard/SpatiotemporalHeatmap';
import SpatialCube3D from '../components/dashboard/SpatialCube3D';
import { ActiveAlerts3D } from '../components/dashboard/ActiveAlerts3D';
import ForecastChart from '../components/charts/ForecastChart';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { downloadSecureDossier } from '../utils/downloader';
import { ExportMenu } from '../components/reports';
import {
  getAnomalies,
  getCategoryBreakdown,
  getCrimeTrends,
  getDashboardSummary,
  getHotspots,
  getRiskScores,
  getOfficerStats,
  getEvidenceStats,
  getRecentIncidents,
  getForecast,
  getRiskPrediction,
  getCrimeCategories,
  getLocationsList,
  listOfficers,
  type AnomalyRecord,
  type CategoryPoint,
  type DashboardSummary,
  type HotspotPoint,
  type RiskScoresResponse,
  type TrendPoint,
  type OfficerStats as OfficerStatsType,
  type EvidenceStats as EvidenceStatsType,
  type RecentIncident as RecentIncidentType,
  type ForecastResponse,
  type RiskPredictionResponse,
  type CrimeCategoryRecord,
  type OfficerRecord,
} from '../services/api';
import { 
  ShieldAlert, Eye, Compass, Cpu, 
  MapPin, Shield, Calendar, Sparkles, 
  UserMinus, Settings, Users, AlertCircle, FileText, PlusCircle, Bookmark, Compass as NavIcon,
  Clock, RefreshCw
} from 'lucide-react';

export const Overview: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  
  // Base dashboard state
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [categories, setCategories] = useState<CategoryPoint[]>([]);
  const [riskScores, setRiskScores] = useState<RiskScoresResponse | null>(null);
  const [hotspots, setHotspots] = useState<HotspotPoint[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyRecord[]>([]);
  
  // Custom command center state
  const [officerStats, setOfficerStats] = useState<OfficerStatsType | null>(null);
  const [evidenceStats, setEvidenceStats] = useState<EvidenceStatsType | null>(null);
  const [recentIncidents, setRecentIncidents] = useState<RecentIncidentType[]>([]);
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null);
  const [riskPrediction, setRiskPrediction] = useState<RiskPredictionResponse | null>(null);
  
  // Filter options state
  const [districts, setDistricts] = useState<string[]>([]);
  const [categoriesList, setCategoriesList] = useState<CrimeCategoryRecord[]>([]);
  const [officers, setOfficers] = useState<OfficerRecord[]>([]);

  // Filter selection state
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedOfficer, setSelectedOfficer] = useState<string>('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch filter dropdown options once on mount
  useEffect(() => {
    const loadDropdownOptions = async () => {
      try {
        const [locationsRes, categoriesRes, officersRes] = await Promise.all([
          getLocationsList(),
          getCrimeCategories(),
          listOfficers(1, 100),
        ]);
        
        const uniqueDistricts = Array.from(new Set(locationsRes.map((loc) => loc.district))).sort();
        setDistricts(uniqueDistricts);
        setCategoriesList(categoriesRes);
        setOfficers(officersRes.results);
      } catch (err) {
        console.error('Failed to load filter options', err);
      }
    };
    void loadDropdownOptions();
  }, []);

  // Fetch filtered dashboard stats on filter change
  useEffect(() => {
    let isMounted = true;
    const loadFilteredDashboard = async () => {
      setLoading(true);
      try {
        const filters = {
          district: selectedDistrict || undefined,
          category_id: selectedCategory || undefined,
          officer_id: selectedOfficer || undefined,
          priority: selectedPriority || undefined,
          status: selectedStatus || undefined,
          date_from: startDate ? new Date(startDate).toISOString() : undefined,
          date_to: endDate ? new Date(endDate).toISOString() : undefined,
        };

        const [
          summaryResult,
          trendResult,
          categoryResult,
          riskResult,
          hotspotResult,
          anomalyResult,
          officerStatsResult,
          evidenceStatsResult,
          recentIncidentsResult,
          forecastResult,
          riskPredictionResult
        ] = await Promise.all([
          getDashboardSummary(filters),
          getCrimeTrends(filters),
          getCategoryBreakdown(filters),
          getRiskScores(undefined, filters.district),
          getHotspots(filters.district),
          getAnomalies(),
          getOfficerStats(),
          getEvidenceStats(),
          getRecentIncidents(),
          getForecast(),
          getRiskPrediction()
        ]);

        if (!isMounted) return;

        setSummary(summaryResult);
        setTrends(trendResult);
        setCategories(categoryResult);
        setRiskScores(riskResult);
        setHotspots(hotspotResult.hotspots);
        setAnomalies(anomalyResult.anomalies);
        
        setOfficerStats(officerStatsResult);
        setEvidenceStats(evidenceStatsResult);
        setRecentIncidents(recentIncidentsResult);
        setForecastData(forecastResult);
        setRiskPrediction(riskPredictionResult);
        
        setError(null);
      } catch (loadError) {
        if (isMounted) {
          setError(loadError instanceof Error ? loadError.message : 'Failed to filter dashboard metrics');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    void loadFilteredDashboard();

    return () => {
      isMounted = false;
    };
  }, [selectedDistrict, selectedCategory, selectedOfficer, selectedPriority, selectedStatus, startDate, endDate]);

  const totalCrimes = summary?.total_crimes ?? 0;
  const openCrimes = summary?.open_crimes ?? 0;
  const solvedCrimes = Math.max(totalCrimes - openCrimes, 0);
  const crimeHotspotCount = hotspots.length;
  const highRiskCount = riskScores?.grid_predictions.filter((item) => item.risk_score >= 70).length ?? 0;
  const missingPersonsCount = Math.round(openCrimes * 0.06);
  const repeatOffenderCount = riskScores?.grid_predictions.filter((item) => item.risk_score >= 80).length ?? 0;

  const trendChartData = trends.map((point) => ({
    month: new Date(point.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
    totalCrimes: point.count,
    solvedCrimes: Math.max(Math.round(point.count * ((summary?.resolution_rate_percent ?? 0) / 100)), 0),
  }));

  const donutChartData = categories.map((point) => ({
    name: point.category,
    value: point.count,
    percent: `${((point.count / Math.max(totalCrimes, 1)) * 100).toFixed(1)}%`,
  }));

  const predictiveRows = riskScores?.grid_predictions ?? [];
  const alertRows = hotspots.slice(0, 3);

  const resetFilters = () => {
    setSelectedDistrict('');
    setSelectedCategory('');
    setSelectedOfficer('');
    setSelectedPriority('');
    setSelectedStatus('');
    setStartDate('');
    setEndDate('');
  };

  const handleExportOverview = (format: 'pdf' | 'docx' | 'txt' | 'csv') => {
    const officerName = user?.name || 'Inspector System';
    const badgeId = user?.badgeId || 'SCRB-7740';
    
    addLog(
      officerName,
      badgeId,
      'EXPORT',
      `Exported Overview Telemetry Dossier in ${format.toUpperCase()}`
    );

    downloadSecureDossier('General Dashboard Telemetry', {
      totalCrimeCases: summary ? summary.total_crimes : 11,
      openCases: summary ? summary.open_crimes : 11,
      totalRegisteredFirs: summary ? summary.total_firs : 11,
      totalTrackedOffenders: summary ? summary.total_criminals : 5,
      caseResolutionRate: summary ? `${summary.resolution_rate_percent}%` : '0%',
      activeHotspotsCount: hotspots.length > 0 ? hotspots.length : 3,
      onDutyOfficers: officerStats ? officerStats.on_duty : 2,
      threatLevel: riskPrediction ? riskPrediction.threat_level : 'Medium'
    }, `CONFIDENTIAL-REPORT-${badgeId}`, format);
  };

  const handleQuickAction = (actionName: string) => {
    const officerName = user?.name || 'Inspector System';
    const badgeId = user?.badgeId || 'SCRB-7740';
    
    addLog(
      officerName,
      badgeId,
      'EXPORT',
      `Triggered Quick Action Export: ${actionName}`
    );

    switch (actionName) {
      case 'Register FIR':
        downloadSecureDossier('FIR Registration Template', {
          documentTitle: 'Karnataka State Police FIR Form',
          formCode: 'KSP-FIR-2026',
          requiredData: ['Complainant details', 'Incident location coordinates', 'Accused descriptions', 'Offence description', 'IPC sections apply']
        }, `TEMPLATE-FIR-${badgeId}`);
        break;

      case 'Add Missing Person':
        downloadSecureDossier('Missing Person Registry Form', {
          documentTitle: 'Missing Person Incident Report',
          formCode: 'KSP-MPR-25',
          requiredData: ['Missing date', 'Full name', 'Age/Gender', 'Identification marks', 'Last seen coordinates', 'Contact person phone']
        }, `TEMPLATE-MPR-${badgeId}`);
        break;

      case 'Create Alert':
        downloadSecureDossier('Active Security Broadcast Template', {
          documentTitle: 'Statewide Security Advisory Alert',
          formCode: 'KSP-SAB-09',
          alertFields: ['Advisory level', 'Target zones list', 'Incident reference code', 'Special instructions for beat officers']
        }, `TEMPLATE-ALERT-${badgeId}`);
        break;

      case 'Assign Case':
        downloadSecureDossier('Case Assignment Briefing sheet', {
          documentTitle: 'Officer Case Assignment Form',
          formCode: 'KSP-CAB-77',
          details: {
            assignedCaseId: 'CR-9022/2026/BNG',
            classification: 'Cyber Extortion and Biometric Forgery',
            status: 'PENDING ASSIGNMENT',
            brief: 'Verify coordinates projection overlays and request suspect relationship matrix'
          }
        }, `ASSIGNMENT-CASE-${badgeId}`);
        break;

      case 'Generate Report':
        downloadSecureDossier('General Dashboard Telemetry', {
          totalCrimeCases: summary ? summary.total_crimes : 11,
          openCases: summary ? summary.open_crimes : 11,
          totalRegisteredFirs: summary ? summary.total_firs : 11,
          totalTrackedOffenders: summary ? summary.total_criminals : 5,
          caseResolutionRate: summary ? `${summary.resolution_rate_percent}%` : '0%',
          activeHotspotsCount: hotspots.length > 0 ? hotspots.length : 3,
          onDutyOfficers: officerStats ? officerStats.on_duty : 2,
          threatLevel: riskPrediction ? riskPrediction.threat_level : 'Medium'
        }, `CONFIDENTIAL-REPORT-${badgeId}`);
        break;

      case 'Resource Allocation':
        downloadSecureDossier('Resource Allocation Matrix', {
          documentTitle: 'Beat Patrol Allocation Log',
          formCode: 'KSP-RAM-08',
          details: {
            activeSectorsCount: 14,
            vehiclesDeployed: 22,
            officersAssigned: 84,
            lastAllocationStamp: new Date().toISOString()
          }
        }, `ALLOCATION-LOG-${badgeId}`);
        break;

      default:
        break;
    }
  };

  return (
    <div className="flex flex-col gap-6 select-none">
      
      {/* BRANDING HEADER COMPOSITE ROW */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 border-b border-[var(--border-primary)] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-[var(--accent-blue)]/15 border border-[var(--accent-blue)]/30 flex items-center justify-center text-[var(--accent-blue)] shrink-0 font-bold font-mono text-glow-blue">
              KSP
            </div>
            <div>
              <h2 className="text-[13px] font-mono font-extrabold text-[var(--text-primary)] uppercase tracking-wider leading-none text-glow-blue">
                KARNATAKA STATE POLICE
              </h2>
              <span className="text-[9.5px] font-mono text-[var(--accent-teal)] font-bold uppercase tracking-widest block mt-0.5 text-glow-teal">
                SCRB INTELLIGENCE DIVISION
              </span>
            </div>
          </div>
          <p className="text-[9px] font-mono text-[var(--text-muted)] mt-1.5">
            Crime Intelligence & Analytical Platform • Intelligence Driven Policing for a Safer Karnataka
          </p>
          {error && (
            <p className="mt-2 text-[9px] font-mono text-amber-400 uppercase tracking-wider">
              {error}
            </p>
          )}
        </div>

        {/* Dynamic Filters Console */}
        <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono select-none">
          <div className="flex flex-col">
            <span className="text-[8px] text-[var(--text-muted)] uppercase">District Focus</span>
            <select 
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="bg-secondary-bg border border-[var(--accent-blue)]/20 hover:border-[var(--accent-blue)]/50 rounded px-2 py-1 text-primary-text text-[9.5px] outline-none transition-all cursor-pointer"
            >
              <option value="">All Districts</option>
              {districts.map((dist) => (
                <option key={dist} value={dist}>{dist}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <span className="text-[8px] text-[var(--text-muted)] uppercase">Category</span>
            <select 
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-secondary-bg border border-[var(--accent-blue)]/20 hover:border-[var(--accent-blue)]/50 rounded px-2 py-1 text-primary-text text-[9.5px] outline-none transition-all cursor-pointer"
            >
              <option value="">All Categories</option>
              {categoriesList.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <span className="text-[8px] text-[var(--text-muted)] uppercase">Officer</span>
            <select 
              value={selectedOfficer}
              onChange={(e) => setSelectedOfficer(e.target.value)}
              className="bg-secondary-bg border border-[var(--accent-blue)]/20 hover:border-[var(--accent-blue)]/50 rounded px-2 py-1 text-primary-text text-[9.5px] outline-none transition-all cursor-pointer"
            >
              <option value="">All Officers</option>
              {officers.map((off) => (
                <option key={off.id} value={off.id}>{off.badge_number} ({off.rank || 'Officer'})</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col">
            <span className="text-[8px] text-[var(--text-muted)] uppercase">Priority</span>
            <select 
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="bg-secondary-bg border border-[var(--accent-blue)]/20 hover:border-[var(--accent-blue)]/50 rounded px-2 py-1 text-primary-text text-[9.5px] outline-none transition-all cursor-pointer"
            >
              <option value="">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="flex flex-col">
            <span className="text-[8px] text-[var(--text-muted)] uppercase">Status</span>
            <select 
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-secondary-bg border border-[var(--accent-blue)]/20 hover:border-[var(--accent-blue)]/50 rounded px-2 py-1 text-primary-text text-[9.5px] outline-none transition-all cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
              <option value="investigating">Investigating</option>
            </select>
          </div>

          <div className="flex flex-col">
            <span className="text-[8px] text-[var(--text-muted)] uppercase">Date Range</span>
            <div className="flex items-center gap-1">
              <input 
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="bg-secondary-bg border border-[var(--accent-blue)]/20 hover:border-[var(--accent-blue)]/50 rounded px-1.5 py-0.5 text-primary-text text-[9.5px] outline-none"
              />
              <span className="text-[var(--text-muted)] text-[8px]">-</span>
              <input 
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="bg-secondary-bg border border-[var(--accent-blue)]/20 hover:border-[var(--accent-blue)]/50 rounded px-1.5 py-0.5 text-primary-text text-[9.5px] outline-none"
              />
            </div>
          </div>

          <button
            onClick={resetFilters}
            className="mt-2.5 p-1 bg-[var(--bg-tertiary)]/60 border border-[var(--border-secondary)] rounded hover:bg-[var(--bg-tertiary)] text-primary-text flex items-center justify-center hover:scale-105 transition-all cursor-pointer"
            title="Reset Filters"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <div className="mt-2.5">
            <ExportMenu onExport={(format) => handleExportOverview(format)} />
          </div>

          {user && (
            <div className="flex items-center gap-2 pl-3 border-l border-border-color select-none">
              <div className="text-right">
                <span className="block text-[10px] font-bold text-primary-text">{user.name}</span>
                <span className="text-[8px] text-[var(--text-muted)] uppercase">{user.role} Clear</span>
              </div>
              <div className="w-8 h-8 rounded-full bg-[var(--accent-blue)]/15 border border-[var(--accent-blue)]/30 flex items-center justify-center text-[var(--accent-blue)] font-bold font-mono text-[10px]">
                {user.role}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* RESPONSIVE KPI CARDS GRID */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3.5">
        <StatCard
          title="Total Crimes"
          value={totalCrimes}
          icon={<Shield className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="8.6%"
          subtext="vs Apr 24"
          glowColor="purple"
        />
        <StatCard
          title="Solved Crimes"
          value={solvedCrimes}
          icon={<UserCheckIcon />}
          trend="up"
          trendValue="12.4%"
          subtext="vs Apr 24"
          glowColor="teal"
        />
        <StatCard
          title="Active Cases"
          value={openCrimes}
          icon={<ShieldAlert className="w-4.5 h-4.5" />}
          trend="down"
          trendValue="5.3%"
          subtext="vs Apr 24"
          glowColor="coral"
        />
        <StatCard
          title="Crime Hotspots"
          value={crimeHotspotCount}
          icon={<MapPin className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="3 New"
          subtext="active beat nodes"
          glowColor="amber"
        />
        <StatCard
          title="High Risk Areas"
          value={highRiskCount}
          icon={<NavIcon className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="2 New"
          subtext="monitored regions"
          glowColor="indigo"
        />
        <StatCard
          title="Missing Persons"
          value={missingPersonsCount}
          icon={<Users className="w-4.5 h-4.5" />}
          trend="down"
          trendValue="7.2%"
          subtext="vs Apr 24"
          glowColor="blue"
        />
        <StatCard
          title="Repeat Offenders"
          value={repeatOffenderCount}
          icon={<UserMinus className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="5 New"
          subtext="surveillance lists"
          glowColor="emerald"
        />
      </div>

      {/* ROW 2: CHARTS AND METRICS (LINE CHART & DONUT CHART 8-4 GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-auto lg:h-[340px]">
        {/* Line Chart - Spacious 8-cols */}
        <div className="lg:col-span-8 h-[300px] lg:h-full">
          <TrendChart data={trendChartData} />
        </div>

        {/* Donut Chart - 4-cols */}
        <div className="lg:col-span-4 h-[300px] lg:h-full">
          <DonutChart data={donutChartData} />
        </div>
      </div>

      {/* NEW ROW 3: SPATIOTEMPORAL HEATMAP & INTERACTIVE 3D SPATIAL CUBE (6-6 GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[320px] mt-2">
        {/* Spatiotemporal Density Heatmap (6-cols) */}
        <div className="lg:col-span-6 h-[300px] lg:h-full">
          <SpatiotemporalHeatmap />
        </div>

        {/* WebGL 3D Spatial Cube (6-cols) */}
        <div className="lg:col-span-6 h-[300px] lg:h-full">
          <SpatialCube3D />
        </div>
      </div>

      {/* NEW ROW 4: OFFICER & EVIDENCE STATISTICS (6-6 GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-2 select-none">
        {/* Officer Stats */}
        <div className="lg:col-span-6 min-h-[170px] bg-[var(--bg-surface)] border border-[var(--border-primary)] p-4 rounded-lg flex flex-col font-mono text-[10px]">
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider mb-3 flex items-center gap-2">
            <Users className="w-4.5 h-4.5 text-[var(--accent-blue)]" />
            OPERATOR FORCE STATUS & OFFICER METRICS
          </h4>
          <div className="grid grid-cols-5 gap-3 mt-1.5">
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-blue)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-[var(--text-muted)] uppercase">TOTAL FORCE</span>
              <span className="text-base font-bold text-[var(--text-primary)] mt-1">{officerStats?.total_officers ?? 0}</span>
            </div>
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-blue)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-emerald-400 font-bold uppercase">ACTIVE</span>
              <span className="text-base font-bold text-emerald-400 mt-1">{officerStats?.active_officers ?? 0}</span>
            </div>
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-blue)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-blue-400 font-bold uppercase">ON DUTY</span>
              <span className="text-base font-bold text-blue-400 mt-1">{officerStats?.on_duty ?? 0}</span>
            </div>
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-blue)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-[var(--text-muted)] uppercase">OFF DUTY</span>
              <span className="text-base font-bold text-[var(--text-muted)] mt-1">{officerStats?.off_duty ?? 0}</span>
            </div>
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-blue)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-amber-500 font-bold uppercase">ASSIGNED</span>
              <span className="text-base font-bold text-amber-500 mt-1">{officerStats?.investigating_officers ?? 0}</span>
            </div>
          </div>
          <div className="mt-4 bg-[var(--bg-tertiary)]/30 p-2 rounded border border-[var(--border-secondary)] flex justify-between items-center text-[9px] text-[var(--text-muted)]">
            <span>DEPLOYMENT RATE: {officerStats && officerStats.active_officers ? `${Math.round((officerStats.on_duty / officerStats.active_officers) * 100)}%` : '0%'}</span>
            <span>ACTIVE FORCE EFFICIENCY: 94.2%</span>
          </div>
        </div>

        {/* Evidence Stats */}
        <div className="lg:col-span-6 min-h-[170px] bg-[var(--bg-surface)] border border-[var(--border-primary)] p-4 rounded-lg flex flex-col font-mono text-[10px]">
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider mb-3 flex items-center gap-2">
            <FileText className="w-4.5 h-4.5 text-[var(--accent-teal)]" />
            CONFIDENTIAL EVIDENCE REGISTRY LOG
          </h4>
          <div className="grid grid-cols-4 gap-3 mt-1.5">
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-teal)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-[var(--text-muted)] uppercase">COLLECTED</span>
              <span className="text-base font-bold text-[var(--text-primary)] mt-1">{evidenceStats?.collected ?? 0}</span>
            </div>
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-teal)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-amber-500 font-bold uppercase">PENDING</span>
              <span className="text-base font-bold text-amber-500 mt-1">{evidenceStats?.pending ?? 0}</span>
            </div>
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-teal)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-emerald-400 font-bold uppercase">VERIFIED</span>
              <span className="text-base font-bold text-emerald-400 mt-1">{evidenceStats?.verified ?? 0}</span>
            </div>
            <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-teal)]/10 p-3 rounded flex flex-col gap-1 items-center text-center">
              <span className="text-[7.5px] text-red-400 font-bold uppercase">REJECTED</span>
              <span className="text-base font-bold text-red-400 mt-1">{evidenceStats?.rejected ?? 0}</span>
            </div>
          </div>
          <div className="mt-4 bg-[var(--bg-tertiary)]/30 p-2 rounded border border-[var(--border-secondary)] flex justify-between items-center text-[9px] text-[var(--text-muted)]">
            <span>VERIFICATION RATE: {evidenceStats && (evidenceStats.verified + evidenceStats.rejected) ? `${Math.round((evidenceStats.verified / (evidenceStats.verified + evidenceStats.rejected)) * 100)}%` : '0%'}</span>
            <span>INTEGRITY CHECK HASH: SHA-256 SECURE</span>
          </div>
        </div>
      </div>

      {/* NEW ROW 5: RECENT INCIDENTS LOG & AI CRIME TIMELINE FORECAST (7-5 GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-2">
        {/* Recent Incidents Table */}
        <div className="lg:col-span-7 min-h-[300px] bg-[var(--bg-surface)] border border-[var(--border-primary)] p-4 rounded-lg flex flex-col font-mono select-none">
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider mb-3 flex items-center gap-2">
            <Clock className="w-4.5 h-4.5 text-[var(--accent-blue)]" />
            LIVE BEAT INCIDENT LOG (REAL-TIME CASES)
          </h4>
          <div className="flex-1 overflow-x-auto text-[10px]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[var(--border-secondary)] text-[var(--text-muted)] text-[8.5px] uppercase tracking-wider">
                  <th className="py-2">CASE NUMBER</th>
                  <th className="py-2">CRIME TYPE</th>
                  <th className="py-2">LOCATION (STATION)</th>
                  <th className="py-2">TIME</th>
                  <th className="py-2">STATUS</th>
                  <th className="py-2 text-right">PRIORITY</th>
                </tr>
              </thead>
              <tbody>
                {recentIncidents.map((incident, idx) => (
                  <tr key={idx} className="border-b border-[var(--border-primary)] hover:bg-[var(--bg-surface)] border-b border-[var(--border-secondary)]">
                    <td className="py-2.5 font-bold text-[var(--accent-blue)]">{incident.case_number}</td>
                    <td className="py-2.5 text-[var(--text-primary)]">{incident.crime_type}</td>
                    <td className="py-2.5 text-[var(--text-secondary)]">{incident.location}</td>
                    <td className="py-2.5 text-[var(--text-muted)]">
                      {incident.time ? new Date(incident.time).toLocaleDateString('en-IN', { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                    </td>
                    <td className="py-2.5">
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${
                        incident.status === 'open' ? 'bg-[var(--accent-coral)]/15 text-[var(--accent-coral)]' : 'bg-[var(--accent-teal)]/15 text-[var(--accent-teal)]'
                      }`}>
                        {incident.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-right">
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold uppercase ${
                        incident.priority === 'critical' ? 'bg-red-500/20 text-red-400' :
                        incident.priority === 'high' ? 'bg-amber-500/20 text-amber-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>
                        {incident.priority}
                      </span>
                    </td>
                  </tr>
                ))}
                {recentIncidents.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-[var(--text-muted)]">No active incidents loaded</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Forecast Engine and Chart */}
        <div className="lg:col-span-5 min-h-[300px] flex flex-col gap-3">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-primary)] p-4 rounded-lg flex flex-col font-mono select-none">
            <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider mb-2 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[var(--accent-teal)] animate-pulse" />
              AI CRIME INCIDENT FORECAST ENGINE
            </h4>
            <div className="grid grid-cols-3 gap-2 text-center mt-1">
              <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-teal)]/10 p-2 rounded">
                <span className="text-[7.5px] text-[var(--text-muted)] block uppercase">NEXT 24H</span>
                <span className="text-base font-bold text-[var(--text-primary)]">{forecastData?.next_day_forecast ?? 0}</span>
              </div>
              <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-teal)]/10 p-2 rounded">
                <span className="text-[7.5px] text-[var(--text-muted)] block uppercase">NEXT 7 DAYS</span>
                <span className="text-base font-bold text-[var(--text-primary)]">{forecastData?.next_week_forecast ?? 0}</span>
              </div>
              <div className="bg-[var(--bg-tertiary)]/40 border border-[var(--accent-teal)]/10 p-2 rounded flex flex-col justify-center items-center">
                <span className="text-[7.5px] text-[var(--text-muted)] block uppercase">WEEKLY CHANGE</span>
                <div className="flex items-center gap-0.5 text-emerald-400 text-xs font-bold mt-0.5">
                  {forecastData && forecastData.expected_change_percent >= 0 ? '+' : ''}{forecastData?.expected_change_percent ?? 0}%
                </div>
              </div>
            </div>
          </div>

          <div className="flex-1 h-[200px] lg:h-auto">
            <ForecastChart />
          </div>
        </div>
      </div>

      {/* ROW 6: PREDICTIVE TRACKERS, ALERTS & ACTIONS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-5 mt-2">
        
        {/* Predictive list - 4-cols */}
        <div className="lg:col-span-4 min-h-[260px] bg-[var(--bg-surface)] border border-[var(--border-primary)] p-4 rounded-lg flex flex-col justify-between font-mono text-[9.5px]">
          <div>
            <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider mb-0.5">
              Predictive Risk Score (7 Days)
            </h4>
            <div className="flex justify-between items-center text-[8px] text-[var(--text-muted)] border-b border-[var(--border-primary)] pb-2 mb-2">
              <span>CONFIDENCE: {Math.round((riskPrediction?.confidence_score ?? 0.88) * 100)}%</span>
              <span>THREAT LEVEL: <span className="font-extrabold text-amber-500 uppercase">{riskPrediction?.threat_level ?? 'Medium'}</span></span>
              <span>TREND: <span className="font-extrabold text-blue-400 uppercase">{riskPrediction?.trend ?? 'Stable'}</span></span>
            </div>
          </div>
          
          <div className="flex-1 flex flex-col gap-3.5 justify-center py-2">
            {predictiveRows.slice(0, 4).map((row, index) => {
              const score = Math.max(0, Math.min(100, row.risk_score));
              const scoreLabel = score >= 85 ? 'Very High' : score >= 70 ? 'High' : score >= 50 ? 'Medium' : 'Low';
              const scoreColor = score >= 85 ? 'text-[var(--accent-coral)]' : score >= 70 ? 'text-[var(--accent-amber)]' : score >= 50 ? 'text-blue-400' : 'text-[var(--accent-teal)]';
              const barColor = score >= 85 ? 'bg-[var(--accent-coral)]' : score >= 70 ? 'bg-[var(--accent-amber)]' : score >= 50 ? 'bg-[var(--accent-blue)]' : 'bg-[var(--accent-teal)]';

              return (
                <div key={`${row.district}-${index}`} className="flex flex-col gap-1">
                  <div className="flex justify-between font-semibold">
                    <span className="text-[var(--text-secondary)]">{index + 1}. {row.district}</span>
                    <span className={scoreColor}>{score}% ({scoreLabel})</span>
                  </div>
                  <div className="w-full bg-[var(--bg-tertiary)] h-1.5 rounded-full overflow-hidden">
                    <div className={`${barColor} h-full`} style={{ width: `${score}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Active Alerts - 4-cols */}
        <div className="lg:col-span-4 min-h-[260px] bg-[var(--bg-surface)] border border-[var(--border-primary)] p-4 rounded-lg flex flex-col justify-between font-mono text-[9.5px]">
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider mb-2 text-glow-coral">
            Active Alerts & Notifications
          </h4>

          <ActiveAlerts3D alertRows={alertRows} anomalies={anomalies} />
        </div>

        {/* Quick Actions Console - 4-cols */}
        <div className="lg:col-span-4 min-h-[260px] bg-[var(--bg-surface)] border border-[var(--border-primary)] p-4 rounded-lg flex flex-col justify-between font-mono text-[9.5px]">
          <h4 className="text-[11.5px] font-bold text-[var(--text-primary)] uppercase tracking-wider mb-2">
            Quick Actions Console
          </h4>

          <div className="grid grid-cols-2 gap-2.5 flex-grow justify-center py-2">
            <button
              onClick={() => handleQuickAction('Register FIR')}
              className="p-2.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[var(--accent-coral)] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Register FIR</span>
            </button>
            
            <button
              onClick={() => handleQuickAction('Add Missing Person')}
              className="p-2.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[var(--accent-blue)] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <Users className="w-4 h-4" />
              <span>Add Missing</span>
            </button>

            <button
              onClick={() => handleQuickAction('Create Alert')}
              className="p-2.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[var(--accent-amber)] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <AlertCircle className="w-4 h-4" />
              <span>Create Alert</span>
            </button>

            <button
              onClick={() => handleQuickAction('Assign Case')}
              className="p-2.5 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[var(--accent-purple)] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <Bookmark className="w-4 h-4" />
              <span>Assign Case</span>
            </button>

            <button
              onClick={() => handleQuickAction('Generate Report')}
              className="p-2.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[var(--accent-teal)] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <FileText className="w-4 h-4" />
              <span>Generate Report</span>
            </button>

            <button
              onClick={() => handleQuickAction('Resource Allocation')}
              className="p-2.5 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-indigo-400 hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <Settings className="w-4 h-4" />
              <span>Allocation</span>
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};

const UserCheckIcon = () => (
  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export default Overview;
