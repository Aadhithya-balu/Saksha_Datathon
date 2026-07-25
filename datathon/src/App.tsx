import React, { useEffect } from 'react';
import { useAuthStore } from './store/authStore';
import { useAuditStore } from './store/auditStore';
import { useAppStore } from './store/appStore';
import Login from './pages/Login';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import CommandPalette from './components/ui/CommandPalette';
import Overview from './pages/Overview';
import Hotspots from './pages/Hotspots';
import Network from './pages/Network';
import Predictions from './pages/Predictions';
import Anomalies from './pages/Anomalies';
import Offenders from './pages/Offenders';
import Reports from './pages/Reports';
import AIChat from './pages/AIChat';
import CrimeCases from './pages/CrimeCases';
import RoleGuard from './components/layout/RoleGuard';
import FIRPage from './pages/FIR';
import Criminals from './pages/Criminals';
import Victims from './pages/Victims';
import OfficersPage from './pages/Officers';
import EvidencePage from './pages/Evidence';
import InvestigationPage from './pages/Investigation';
import NotificationsPage from './pages/Notifications';
import SociologicalPage from './pages/Sociological';
import StrategicPage from './pages/Strategic';
import GlobalAIAssistant from './components/ai/GlobalAIAssistant';
import DocsPage from './pages/Docs';
import SettingsHelp from './pages/SettingsHelp';
import Admin from './pages/Admin';

function App() {
  const { isAuthenticated, user, isHydrating, initializeSession } = useAuthStore();
  const { addLog } = useAuditStore();
  const { activeTab, setActiveTab, sidebarCollapsed, setSidebarCollapsed, theme } = useAppStore();

  useEffect(() => {
    void initializeSession();
  }, [initializeSession]);

  // Initialize theme from store on mount
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Listen for navigation requests (cross-tab links)
  useEffect(() => {
    const handleNavigate = (e: Event) => {
      const customEvent = e as CustomEvent<{ tab: string; targetId?: string }>;
      if (customEvent.detail?.tab) {
        setActiveTab(customEvent.detail.tab);
        if (customEvent.detail.targetId) {
          sessionStorage.setItem('selected_entity_id', customEvent.detail.targetId);
        }
      }
    };
    window.addEventListener('navigate-tab', handleNavigate);
    return () => window.removeEventListener('navigate-tab', handleNavigate);
  }, [setActiveTab]);

  // Log page views
  useEffect(() => {
    if (!isAuthenticated || !user) return;
    const tabLabels: Record<string, string> = {
      dashboard: 'Overview Dashboard',
      fir: 'FIR Registry',
      hotspot: 'Hotspot Map',
      network: 'Network Graph',
      predictive: 'Predictive AI',
      anomaly: 'Anomaly Feed',
      crime_cases: 'Crime Cases',
      investigation: 'Investigation',
      notifications: 'Intelligence Center',
      sociological: 'Sociological Intelligence',
      strategic: 'Strategic Intelligence',
      offenders: 'Offender Registry',
      criminals: 'Criminal Dossiers',
      victims: 'Victims Registry',
      reports: 'Reports Center',
      settings_help: 'Settings',
      admin: 'Admin Panel',
      ai_chat: 'AI Assistant',
      officers: 'Officer Management',
      evidence: 'Evidence Handling',
      docs: 'Documentation',
    };
    addLog(user.name, user.badgeId, 'PAGE_VIEW', `Accessed ${tabLabels[activeTab] || activeTab}`);
  }, [activeTab, isAuthenticated, user, addLog]);

  // Loading screen
  if (isHydrating) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] text-[var(--text-primary)]">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-[var(--accent-blue-subtle)] border border-[var(--accent-blue)]/20 flex items-center justify-center mx-auto">
            <svg className="w-6 h-6 text-[var(--accent-blue)] animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">Initializing Saksha</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">Establishing secure session...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login />;
  }

  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard': return <Overview />;
      case 'fir': return <RoleGuard path="/firs"><FIRPage /></RoleGuard>;
      case 'hotspot': return <RoleGuard path="/hotspots"><Hotspots /></RoleGuard>;
      case 'network': return <RoleGuard path="/network"><Network /></RoleGuard>;
      case 'predictive': return <RoleGuard path="/predictions"><Predictions /></RoleGuard>;
      case 'anomaly': return <RoleGuard path="/anomalies"><Anomalies /></RoleGuard>;
      case 'offenders': return <RoleGuard path="/offenders"><Offenders /></RoleGuard>;
      case 'criminals': return <RoleGuard path="/offenders"><Criminals /></RoleGuard>;
      case 'victims': return <RoleGuard path="/offenders"><Victims /></RoleGuard>;
      case 'reports': return <RoleGuard path="/reports"><Reports /></RoleGuard>;
      case 'settings_help': return <RoleGuard path="/settings"><SettingsHelp /></RoleGuard>;
      case 'admin': return <RoleGuard path="/admin"><Admin /></RoleGuard>;
      case 'crime_cases': return <RoleGuard path="/crime-cases"><CrimeCases /></RoleGuard>;
      case 'investigation': return <RoleGuard path="/crime-cases"><InvestigationPage /></RoleGuard>;
      case 'ai_chat': return <RoleGuard path="/ai-chat"><AIChat /></RoleGuard>;
      case 'officers': return <RoleGuard path="/officers"><OfficersPage /></RoleGuard>;
      case 'evidence': return <RoleGuard path="/evidence"><EvidencePage /></RoleGuard>;
      case 'notifications': return <RoleGuard path="/notifications"><NotificationsPage /></RoleGuard>;
      case 'sociological': return <RoleGuard path="/sociological"><SociologicalPage /></RoleGuard>;
      case 'strategic': return <RoleGuard path="/strategic"><StrategicPage /></RoleGuard>;
      case 'docs': return <DocsPage />;
      default: return <Overview />;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        <Header
          sidebarCollapsed={sidebarCollapsed}
          setSidebarCollapsed={setSidebarCollapsed}
        />

        <main className="flex-1 overflow-y-auto">
          <div className="w-full max-w-[1600px] mx-auto p-4 md:p-6 lg:p-8 sk-page-enter">
            {renderActivePage()}
          </div>
        </main>

        {/* Footer */}
        <footer className="h-9 border-t border-[var(--border-primary)] bg-[var(--bg-secondary)]/50 px-6 flex items-center justify-between text-[10px] font-mono text-[var(--text-muted)] select-none shrink-0 no-print">
          <span>SAKSHA v1.0 &middot; Karnataka State Police</span>
          <span className="hidden sm:inline">CLASSIFIED &middot; STAMP: 2026-SCRB-KSP</span>
        </footer>
      </div>

      {/* Global Command Palette */}
      <CommandPalette />

      {/* Global AI Assistant */}
      <GlobalAIAssistant />
    </div>
  );
}

export default App;
