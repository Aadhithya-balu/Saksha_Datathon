import React from 'react';
import StatCard from '../components/dashboard/StatCard';
import TrendChart from '../components/charts/TrendChart';
import DonutChart from '../components/charts/DonutChart';
import SpatiotemporalHeatmap from '../components/dashboard/SpatiotemporalHeatmap';
import SpatialCube3D from '../components/dashboard/SpatialCube3D';
import PredictiveTubes3D from '../components/dashboard/PredictiveTubes3D';
import AlertRadar3D from '../components/dashboard/AlertRadar3D';
import { useAuthStore } from '../store/authStore';
import { useAuditStore } from '../store/auditStore';
import { downloadSecureDossier } from '../utils/downloader';
import { 
  ShieldAlert, Eye, Compass, Cpu, 
  MapPin, Shield, Calendar, Sparkles, 
  UserMinus, Settings, Users, AlertCircle, FileText, PlusCircle, Bookmark, Compass as NavIcon
} from 'lucide-react';

export const Overview: React.FC = () => {
  const { user } = useAuthStore();
  const { addLog } = useAuditStore();

  const handleQuickAction = (actionName: string) => {
    const officerName = user?.name || 'Inspector System';
    const badgeId = user?.badgeId || 'SCRB-7740';
    
    // Log the audit event
    addLog(
      officerName,
      badgeId,
      'EXPORT',
      `Triggered Quick Action Export: ${actionName}`
    );

    // Dynamic downloader based on button role
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
          totalCrimes: '12,543 (▲ 8.6% vs Apr 2024)',
          solvedCrimes: '7,892 (▲ 12.4% vs Apr 2024)',
          activeCases: '4,651 (▼ 5.3% vs Apr 2024)',
          crimeHotspots: '32 Active Nodes',
          highRiskAreas: '17 Monitored Districts',
          missingPersons: '287 Active Cases',
          repeatOffenders: '153 Under Surveillance',
          topPredictiveSector: 'Whitefield (91% threat score)'
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
    <div className="flex flex-col gap-6 p-1 md:p-3 bg-[#060b13] min-h-screen text-[#E8EDF5] select-none">
      
      {/* BRANDING HEADER COMPOSITE ROW */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 border-b border-white/5 pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-[#1E6FD9]/15 border border-[#1e6fd9]/30 flex items-center justify-center text-[#1E6FD9] shrink-0 font-bold font-mono">
              KSP
            </div>
            <div>
              <h2 className="text-[13px] font-mono font-extrabold text-white uppercase tracking-wider leading-none">
                KARNATAKA STATE POLICE
              </h2>
              <span className="text-[9.5px] font-mono text-[#0E9E78] font-bold uppercase tracking-widest block mt-0.5">
                SCRB INTELLIGENCE DIVISION
              </span>
            </div>
          </div>
          <p className="text-[9px] font-mono text-[#6A7A96] mt-1.5">
            Crime Intelligence & Analytical Platform • Intelligence Driven Policing for a Safer Karnataka
          </p>
        </div>

        {/* Filters and User profiles card dropdowns */}
        <div className="flex flex-wrap items-center gap-3 text-[10px] font-mono select-none">
          <div className="flex flex-col">
            <span className="text-[8px] text-[#6A7A96] uppercase">State Jurisdiction</span>
            <select className="bg-[#111D35] border border-border-color rounded px-2 py-1 text-white text-[9.5px] outline-none">
              <option>Karnataka</option>
            </select>
          </div>
          
          <div className="flex flex-col">
            <span className="text-[8px] text-[#6A7A96] uppercase">District Focus</span>
            <select className="bg-[#111D35] border border-border-color rounded px-2 py-1 text-white text-[9.5px] outline-none">
              <option>Bengaluru Urban</option>
            </select>
          </div>

          <div className="flex flex-col">
            <span className="text-[8px] text-[#6A7A96] uppercase">Time Horizon</span>
            <div className="bg-[#111D35] border border-border-color rounded px-2 py-1 text-white text-[9.5px] flex items-center gap-1.5">
              <Calendar className="w-3 h-3 text-[#1e6fd9]" />
              <span>01 May, 2024 - 31 May, 2024</span>
            </div>
          </div>

          {user && (
            <div className="flex items-center gap-2 pl-3 border-l border-white/10 select-none">
              <div className="text-right">
                <span className="block text-[10px] font-bold text-[#E8EDF5]">{user.name}</span>
                <span className="text-[8px] text-[#6A7A96] uppercase">{user.role} Clear</span>
              </div>
              <div className="w-8 h-8 rounded-full bg-[#1E6FD9]/15 border border-[#1E6FD9]/30 flex items-center justify-center text-[#1E6FD9] font-bold font-mono text-[10px]">
                SP
              </div>
            </div>
          )}
        </div>
      </div>

      {/* RESPONSIVE KPI CARDS GRID */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3.5">
        <StatCard
          title="Total Crimes"
          value={12543}
          icon={<Shield className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="8.6%"
          subtext="vs Apr 24"
          glowColor="purple"
        />
        <StatCard
          title="Solved Crimes"
          value={7892}
          icon={<UserCheckIcon />}
          trend="up"
          trendValue="12.4%"
          subtext="vs Apr 24"
          glowColor="teal"
        />
        <StatCard
          title="Active Cases"
          value={4651}
          icon={<ShieldAlert className="w-4.5 h-4.5" />}
          trend="down"
          trendValue="5.3%"
          subtext="vs Apr 24"
          glowColor="coral"
        />
        <StatCard
          title="Crime Hotspots"
          value={32}
          icon={<MapPin className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="3 New"
          subtext="active beat nodes"
          glowColor="amber"
        />
        <StatCard
          title="High Risk Areas"
          value={17}
          icon={<NavIcon className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="2 New"
          subtext="monitored regions"
          glowColor="indigo"
        />
        <StatCard
          title="Missing Persons"
          value={287}
          icon={<Users className="w-4.5 h-4.5" />}
          trend="down"
          trendValue="7.2%"
          subtext="vs Apr 24"
          glowColor="blue"
        />
        <StatCard
          title="Repeat Offenders"
          value={153}
          icon={<UserMinus className="w-4.5 h-4.5" />}
          trend="up"
          trendValue="5 New"
          subtext="surveillance lists"
          glowColor="emerald"
        />
      </div>

      {/* ROW 2: CHARTS AND METRICS (LINE CHART & DONUT CHART 8-4 GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[340px]">
        {/* Line Chart - Spacious 8-cols */}
        <div className="lg:col-span-8 h-full">
          <TrendChart />
        </div>

        {/* Donut Chart - 4-cols */}
        <div className="lg:col-span-4 h-full">
          <DonutChart />
        </div>
      </div>

      {/* NEW ROW 3: SPATIOTEMPORAL HEATMAP & INTERACTIVE 3D SPATIAL CUBE (6-6 GRID) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-[320px] mt-2">
        {/* Spatiotemporal Density Heatmap (6-cols) */}
        <div className="lg:col-span-6 h-full">
          <SpatiotemporalHeatmap />
        </div>

        {/* WebGL 3D Spatial Cube (6-cols) */}
        <div className="lg:col-span-6 h-full">
          <SpatialCube3D />
        </div>
      </div>

      {/* ROW 4: PREDICTIVE TRACKERS, ALERTS & ACTIONS */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-5 mt-2">
        
        {/* 3D Predictive risk pillars (4-cols) */}
        <div className="lg:col-span-4 min-h-[260px]">
          <PredictiveTubes3D />
        </div>

        {/* 3D Active alerts radar beacon (4-cols) */}
        <div className="lg:col-span-4 min-h-[260px]">
          <AlertRadar3D />
        </div>

        {/* Quick Actions Console - 4-cols */}
        <div className="lg:col-span-4 min-h-[260px] bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between font-mono text-[9.5px]">
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider mb-2">
            Quick Actions Console
          </h4>

          <div className="grid grid-cols-2 gap-2.5 flex-grow justify-center py-2">
            <button
              onClick={() => handleQuickAction('Register FIR')}
              className="p-2.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[#C94A2A] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Register FIR</span>
            </button>
            
            <button
              onClick={() => handleQuickAction('Add Missing Person')}
              className="p-2.5 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[#1E6FD9] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <Users className="w-4 h-4" />
              <span>Add Missing</span>
            </button>

            <button
              onClick={() => handleQuickAction('Create Alert')}
              className="p-2.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[#D4820A] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <AlertCircle className="w-4 h-4" />
              <span>Create Alert</span>
            </button>

            <button
              onClick={() => handleQuickAction('Assign Case')}
              className="p-2.5 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[#6C43CC] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
            >
              <Bookmark className="w-4 h-4" />
              <span>Assign Case</span>
            </button>

            <button
              onClick={() => handleQuickAction('Generate Report')}
              className="p-2.5 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded flex flex-col items-center justify-center text-center gap-1.5 text-[#0E9E78] hover:scale-105 active:scale-95 transition-all cursor-pointer font-bold"
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
