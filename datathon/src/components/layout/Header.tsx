import React, { useEffect } from 'react';
import { useAuthStore } from '../../store/authStore';
import { useAppStore } from '../../store/appStore';
import { SessionTimer } from '../auth/SessionTimer';
import {
  Search,
  Sun,
  Moon,
  Menu,
  Command,
  ChevronRight,
  Wifi,
  WifiOff,
} from 'lucide-react';
import NotificationBell from '../notifications/NotificationBell';
import { isEmulatorActive } from '../../services/api';

interface HeaderProps {
  sidebarCollapsed?: boolean;
  setSidebarCollapsed?: (collapsed: boolean) => void;
}

const pageLabels: Record<string, string> = {
  dashboard: 'Overview',
  fir: 'FIR Registry',
  hotspot: 'Hotspot Map',
  network: 'Network Graph',
  predictive: 'Predictive AI',
  anomaly: 'Anomaly Feed',
  crime_cases: 'Crime Cases',
  investigation: 'Investigation',
  notifications: 'Intelligence Center',
  offenders: 'Offender Registry',
  criminals: 'Criminal Dossiers',
  victims: 'Victims Registry',
  reports: 'Reports Center',
  settings_help: 'Settings',
  ai_chat: 'AI Assistant',
  officers: 'Officer Management',
  evidence: 'Evidence Handling',
  docs: 'Documentation',
};

export const Header: React.FC<HeaderProps> = ({ sidebarCollapsed, setSidebarCollapsed }) => {
  const { user } = useAuthStore();
  const { theme, toggleTheme, activeTab, setCommandPaletteOpen, sidebarCollapsed: storeCollapsed, setSidebarCollapsed: storeSetCollapsed } = useAppStore();
  const [emulatorActive, setEmulatorActive] = React.useState(isEmulatorActive);
  const [systime, setSystime] = React.useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const handler = (e: Event) => setEmulatorActive((e as CustomEvent).detail);
    window.addEventListener('emulator-status-changed', handler);
    return () => window.removeEventListener('emulator-status-changed', handler);
  }, []);

  useEffect(() => {
    const timer = setInterval(() => setSystime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Ctrl+K listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setCommandPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [setCommandPaletteOpen]);

  const currentPage = pageLabels[activeTab] || 'Saksha';

  return (
    <header className="h-16 border-b border-[var(--border-primary)] bg-[var(--bg-secondary)]/80 backdrop-blur-md px-4 md:px-6 flex items-center justify-between shrink-0" style={{ zIndex: 100 }}>
      {/* Left: Mobile menu + Breadcrumbs */}
      <div className="flex items-center gap-3 min-w-0">
        {setSidebarCollapsed && (
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="md:hidden p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Breadcrumbs */}
        <div className="flex items-center gap-1.5 text-sm min-w-0">
          <span className="text-[var(--text-muted)] hidden sm:inline">Saksha</span>
          <ChevronRight className="w-3.5 h-3.5 text-[var(--text-disabled)] hidden sm:block" />
          <span className="text-[var(--text-primary)] font-medium truncate">{currentPage}</span>
        </div>
      </div>

      {/* Center: Search trigger */}
      <button
        onClick={() => setCommandPaletteOpen(true)}
        className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-tertiary)] border border-[var(--border-secondary)] rounded-lg text-[var(--text-muted)] hover:border-[var(--border-focus)] hover:text-[var(--text-secondary)] transition-all cursor-pointer min-w-[200px] max-w-[320px]"
      >
        <Search className="w-4 h-4 shrink-0" />
        <span className="text-sm flex-1 text-left">Search anything...</span>
        <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono bg-[var(--bg-primary)] border border-[var(--border-secondary)] rounded text-[var(--text-muted)]">
          <Command className="w-2.5 h-2.5" />K
        </kbd>
      </button>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Connection Status */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-mono rounded-md border border-[var(--border-secondary)]">
          {emulatorActive ? (
            <>
              <WifiOff className="w-3 h-3 text-[var(--accent-amber)]" />
              <span className="text-[var(--accent-amber)] uppercase tracking-wider">Offline</span>
            </>
          ) : (
            <>
              <Wifi className="w-3 h-3 text-[var(--accent-teal)]" />
              <span className="text-[var(--accent-teal)] uppercase tracking-wider">Online</span>
            </>
          )}
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-[var(--accent-amber)]" />
          ) : (
            <Moon className="w-4 h-4 text-[var(--accent-purple)]" />
          )}
        </button>

        {/* Notifications */}
        <NotificationBell />

        {/* Clock */}
        <div className="hidden sm:flex flex-col items-end">
          <span className="text-xs font-mono font-semibold text-[var(--text-primary)]">{systime}</span>
          <span className="text-[9px] font-mono text-[var(--text-muted)]">IST</span>
        </div>

        {/* Session Timer */}
        <SessionTimer />
      </div>
    </header>
  );
};

export default Header;
