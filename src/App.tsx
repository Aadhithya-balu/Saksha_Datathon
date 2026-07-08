import React, { useState, useEffect } from 'react';
import { useAuthStore } from './store/authStore';
import { useAuditStore } from './store/auditStore';
import Login from './pages/Login';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import Overview from './pages/Overview';
import Hotspots from './pages/Hotspots';
import Network from './pages/Network';
import Predictions from './pages/Predictions';
import Anomalies from './pages/Anomalies';
import Offenders from './pages/Offenders';
import Reports from './pages/Reports';
import SettingsHelp from './pages/SettingsHelp';
import RoleGuard from './components/layout/RoleGuard';

function App() {
  const { isAuthenticated, user } = useAuthStore();
  const { addLog } = useAuditStore();
  
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);

  // Automatically log PAGE_VIEW transitions
  useEffect(() => {
    if (!isAuthenticated || !user) return;

    const tabLabels: Record<string, string> = {
      dashboard: 'Overview Dashboard',
      hotspot: 'Hotspot Map Analysis',
      network: 'Criminal Network Graph Workspace',
      predictive: 'AI Predictive Intelligence',
      anomaly: 'Anomaly Alert Feed',
      offenders: 'Offender Dossiers Registry',
      reports: 'Reports & Downloads Center',
      settings_help: 'Settings & Operator Help'
    };

    const label = tabLabels[activeTab] || activeTab;
    addLog(
      user.name,
      user.badgeId,
      'PAGE_VIEW',
      `Accessed ${label}`
    );
  }, [activeTab, isAuthenticated, user, addLog]);

  if (!isAuthenticated) {
    return <Login />;
  }

  // Active page selector
  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Overview />;
      case 'hotspot':
        return (
          <RoleGuard path="/hotspots">
            <Hotspots />
          </RoleGuard>
        );
      case 'network':
        return (
          <RoleGuard path="/network">
            <Network />
          </RoleGuard>
        );
      case 'predictive':
        return (
          <RoleGuard path="/predictions">
            <Predictions />
          </RoleGuard>
        );
      case 'anomaly':
        return (
          <RoleGuard path="/anomalies">
            <Anomalies />
          </RoleGuard>
        );
      case 'offenders':
        return (
          <RoleGuard path="/offenders">
            <Offenders />
          </RoleGuard>
        );
      case 'reports':
        return (
          <RoleGuard path="/reports">
            <Reports />
          </RoleGuard>
        );
      case 'settings_help':
        return (
          <RoleGuard path="/settings">
            <SettingsHelp />
          </RoleGuard>
        );
      default:
        return <Overview />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-primary-bg text-[#E8EDF5]">
      
      {/* 3D-styled Collapsible Sidebar Drawer */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
      />

      {/* Main Console display workspace */}
      <div className="flex-grow flex flex-col min-w-0 h-full relative">
        <Header />
        
        {/* Dynamic page container viewport scrollable */}
        <main className="flex-grow p-4 md:p-6 overflow-y-auto custom-scrollbar relative">
          
          {/* Cyber grid aesthetic background indicators */}
          <div className="absolute inset-0 bg-[#080E1B] pointer-events-none -z-20 opacity-90" />
          
          {/* Main layout contents */}
          <div className="w-full max-w-[1600px] mx-auto animate-[fadeIn_0.5s_ease-out]">
            {renderActivePage()}
          </div>

        </main>
        
        {/* Global telemetry footer confidentiality stamp */}
        <footer className="h-6 bg-slate-950 border-t border-border-color text-[8px] font-mono text-[#6A7A96] flex items-center justify-between px-6 select-none shrink-0">
          <span>CLASSIFIED TELEMETRY DATABASES LOCK</span>
          <span>STAMP CODE: 2026-SCRB-KSP</span>
        </footer>
      </div>

    </div>
  );
}

export default App;
