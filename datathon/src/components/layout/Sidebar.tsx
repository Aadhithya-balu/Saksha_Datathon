import React from 'react';
import { useRBAC } from '../../hooks/useRBAC';
import { useAuthStore } from '../../store/authStore';
import { ShieldCheck, LogOut, ChevronLeft, ChevronRight, User } from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  collapsed: boolean;
  setCollapsed: (collapsed: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  collapsed,
  setCollapsed
}) => {
  const { user } = useAuthStore();
  const { checkPermission } = useRBAC();

  const handleLogout = () => {
    useAuthStore.getState().logout();
  };

  // Nav Items
  const navItems = [
    {
      id: 'dashboard',
      label: 'Overview Dashboard',
      path: '/dashboard',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="dbGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#1E6FD9" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#6C43CC" : "#A8B4CC"} />
            </linearGradient>
            <filter id="dbGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1E6FD9" floodOpacity="0.5" />
            </filter>
          </defs>
          {/* Isometric 3D block representation */}
          <path d="M12 2L2 7l10 5 10-5-10-5z" fill="url(#dbGrad)" filter={isActive ? "url(#dbGlow)" : undefined} />
          <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke={isActive ? "#1E6FD9" : "#6A7A96"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    },
    {
      id: 'hotspot',
      label: 'Hotspot Map',
      path: '/hotspots',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="mapGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#0E9E78" : "#6A7A96"} stopOpacity="1" />
              <stop offset="100%" stopColor={isActive ? "#1E6FD9" : "#A8B4CC"} stopOpacity="1" />
            </linearGradient>
            <filter id="mapGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0E9E78" floodOpacity="0.5" />
            </filter>
          </defs>
          {/* 3D Folded Map isometric grid */}
          <path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3V6z" fill="none" stroke="url(#mapGrad)" strokeWidth="1.5" filter={isActive ? "url(#mapGlow)" : undefined} />
          <path d="M9 3v15M15 6v15" stroke={isActive ? "#0E9E78" : "#6A7A96"} strokeWidth="1" strokeDasharray="2 2" />
          <circle cx="12" cy="11" r="2.5" fill={isActive ? "#C94A2A" : "#6A7A96"} className={isActive ? "animate-pulse" : ""} />
        </svg>
      )
    },
    {
      id: 'network',
      label: 'Network Graph',
      path: '/network',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="netGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#6C43CC" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#C94A2A" : "#A8B4CC"} />
            </linearGradient>
            <filter id="netGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#6C43CC" floodOpacity="0.6" />
            </filter>
          </defs>
          {/* 3D nodes connected schema */}
          <circle cx="12" cy="5" r="3" fill="url(#netGrad)" filter={isActive ? "url(#netGlow)" : undefined} />
          <circle cx="6" cy="17" r="3" fill={isActive ? "#C94A2A" : "#6A7A96"} />
          <circle cx="18" cy="17" r="3" fill={isActive ? "#1E6FD9" : "#6A7A96"} />
          <line x1="12" y1="8" x2="6" y2="14" stroke={isActive ? "#6c43cc" : "#6a7a96"} strokeWidth="1.5" />
          <line x1="12" y1="8" x2="18" y2="14" stroke={isActive ? "#6c43cc" : "#6a7a96"} strokeWidth="1.5" />
          <line x1="9" y1="17" x2="15" y2="17" stroke={isActive ? "#6A7A96" : "#6a7a96"} strokeWidth="1" strokeDasharray="2 2" />
        </svg>
      )
    },
    {
      id: 'predictive',
      label: 'Predictive AI',
      path: '/predictions',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="aiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#1E6FD9" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#0E9E78" : "#A8B4CC"} />
            </linearGradient>
            <filter id="aiGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1E6FD9" floodOpacity="0.5" />
            </filter>
          </defs>
          {/* 3D Diamond Brain structure */}
          <path d="M12 2l8 6-8 14-8-14 8-6z" fill="none" stroke="url(#aiGrad)" strokeWidth="1.5" filter={isActive ? "url(#aiGlow)" : undefined} />
          <path d="M12 2v20M4 8h16" stroke={isActive ? "#0E9E78" : "#6A7A96"} strokeWidth="1" />
        </svg>
      )
    },
    {
      id: 'crime_cases',
      label: 'Crime Cases',
      path: '/crime-cases',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="caseGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#1E6FD9" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#0E9E78" : "#A8B4CC"} />
            </linearGradient>
            <filter id="caseGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1E6FD9" floodOpacity="0.5" />
            </filter>
          </defs>
          <rect x="3" y="6" width="18" height="13" rx="2" stroke="url(#caseGrad)" strokeWidth="1.5" filter={isActive ? "url(#caseGlow)" : undefined} />
          <path d="M9 6V4a2 2 0 012-2h2a2 2 0 012 2v2" stroke={isActive ? "#1E6FD9" : "#6A7A96"} strokeWidth="1.5" />
          <circle cx="12" cy="12" r="2" stroke={isActive ? "#0E9E78" : "#6A7A96"} strokeWidth="1.5" />
        </svg>
      )
    },
    {
      id: 'anomaly',
      label: 'Anomaly Feed',
      path: '/anomalies',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="anomGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#C94A2A" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#D4820A" : "#A8B4CC"} />
            </linearGradient>
            <filter id="anomGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#C94A2A" floodOpacity="0.6" />
            </filter>
          </defs>
          {/* 3D Warning Beacon rings */}
          <path d="M12 3l9 16H3L12 3z" fill="none" stroke="url(#anomGrad)" strokeWidth="1.5" filter={isActive ? "url(#anomGlow)" : undefined} />
          <path d="M12 9v5" stroke={isActive ? "#C94A2A" : "#6A7A96"} strokeWidth="2" strokeLinecap="round" />
          <circle cx="12" cy="17" r="1" fill={isActive ? "#C94A2A" : "#A8B4CC"} />
        </svg>
      )
    },
    {
      id: 'offenders',
      label: 'Offender Registry',
      path: '/offenders',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="offGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#1E6FD9" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#6C43CC" : "#A8B4CC"} />
            </linearGradient>
            <filter id="offGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1E6FD9" floodOpacity="0.5" />
            </filter>
          </defs>
          {/* 3D badge dossier */}
          <rect x="4" y="4" width="16" height="16" rx="2" stroke="url(#offGrad)" strokeWidth="1.5" filter={isActive ? "url(#offGlow)" : undefined} />
          <circle cx="12" cy="10" r="2.5" stroke={isActive ? "#1E6FD9" : "#6A7A96"} strokeWidth="1.5" />
          <path d="M8 16c0-2 2.5-3 4-3s4 1 4 3" stroke={isActive ? "#1E6FD9" : "#6A7A96"} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      )
    },
    {
      id: 'reports',
      label: 'Reports Center',
      path: '/reports',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="repGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#1E6FD9" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#6C43CC" : "#A8B4CC"} />
            </linearGradient>
            <filter id="repGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#1E6FD9" floodOpacity="0.5" />
            </filter>
          </defs>
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" fill="none" stroke="url(#repGrad)" strokeWidth="1.5" filter={isActive ? "url(#repGlow)" : undefined} />
          <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" stroke={isActive ? "#1E6FD9" : "#6A7A96"} strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      )
    },
    {
      id: 'ai_chat',
      label: 'AI Chat Assistant',
      path: '/ai-chat',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="chatGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#0E9E78" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#6C43CC" : "#A8B4CC"} />
            </linearGradient>
            <filter id="chatGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0E9E78" floodOpacity="0.5" />
            </filter>
          </defs>
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" fill="none" stroke="url(#chatGrad)" strokeWidth="1.5" filter={isActive ? "url(#chatGlow)" : undefined} />
        </svg>
      )
    },
    {
      id: 'settings_help',
      label: 'Settings & Help',
      path: '/settings',
      icon: (isActive: boolean) => (
        <svg className="w-6 h-6 transition-all duration-300 pointer-events-none" viewBox="0 0 24 24" fill="none">
          <defs>
            <linearGradient id="setGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={isActive ? "#0E9E78" : "#6A7A96"} />
              <stop offset="100%" stopColor={isActive ? "#1E6FD9" : "#A8B4CC"} />
            </linearGradient>
            <filter id="setGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0E9E78" floodOpacity="0.5" />
            </filter>
          </defs>
          <circle cx="12" cy="12" r="3" stroke="url(#setGrad)" strokeWidth="1.5" filter={isActive ? "url(#setGlow)" : undefined} />
          <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" stroke={isActive ? "#0E9E78" : "#6A7A96"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    }
  ];

  return (
    <div
      className={`h-screen flex flex-col justify-between bg-secondary-bg border-r border-border-color transition-all duration-300 z-40 select-none ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Top Banner logo */}
      <div className="flex items-center justify-between p-4 border-b border-border-color">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="p-1 bg-[#1E6FD9]/15 rounded text-[#1E6FD9] shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="font-mono font-bold text-xs uppercase tracking-wider text-[#E8EDF5]">KSP INTEL</span>
              <span className="text-[8px] font-mono text-[#0E9E78] uppercase font-semibold">UNIT SECURE</span>
            </div>
          )}
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden md:flex p-1 hover:bg-[#1E6FD9]/10 rounded border border-border-color hover:border-[#1E6FD9]/30 text-[#A8B4CC] cursor-pointer"
        >
          {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Nav List */}
      <div className="flex-1 py-6 flex flex-col gap-1.5 px-3 overflow-y-auto">
        {navItems.map((item) => {
          const isAllowed = checkPermission(item.path);
          const isActive = activeTab === item.id;

          // If not allowed, we don't render or show locked state
          return (
            <button
              key={item.id}
              onClick={() => isAllowed && setActiveTab(item.id)}
              className={`relative flex items-center gap-3.5 p-3 rounded-btn text-xs font-mono font-medium transition-all duration-200 group cursor-pointer ${
                !isAllowed 
                  ? 'opacity-30 cursor-not-allowed text-[#6A7A96]' 
                  : isActive
                  ? 'bg-[#1E6FD9]/10 text-white border border-[#1E6FD9]/20 shadow-glow-blue'
                  : 'text-[#A8B4CC] hover:text-white hover:bg-white/5 border border-transparent hover:translate-y-[-2px]'
              }`}
            >
              {/* Float-glow icon hook */}
              <div className="shrink-0 transition-transform duration-200 group-hover:scale-110">
                {item.icon(isActive && isAllowed)}
              </div>
              
              {/* Collapsed label */}
              {!collapsed && (
                <span className="truncate uppercase tracking-wider">{item.label}</span>
              )}

              {/* Locked overlay tag */}
              {!isAllowed && !collapsed && (
                <span className="absolute right-3 px-1.5 py-0.5 bg-[#C94A2A]/20 text-[#C94A2A] text-[7.5px] rounded font-bold uppercase select-none border border-[#C94A2A]/40">
                  LOCKED
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer Profile info */}
      {user && (
        <div className="p-3 border-t border-border-color bg-slate-950/20 flex flex-col gap-3">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-[#1E6FD9]/15 border border-[#1E6FD9]/30 flex items-center justify-center text-[#1E6FD9] shrink-0 font-bold font-mono text-xs">
              {user.name.split(' ').pop()?.charAt(0) || <User className="w-4 h-4" />}
            </div>
            {!collapsed && (
              <div className="flex flex-col truncate">
                <span className="text-[10px] font-bold text-[#E8EDF5] truncate">{user.name}</span>
                <span className="text-[8px] font-mono text-[#6A7A96]">{user.badgeId} • {user.role}</span>
              </div>
            )}
          </div>
          {!collapsed && (
            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-[#C94A2A]/10 hover:bg-[#C94A2A]/20 border border-[#C94A2A]/20 hover:border-[#C94A2A]/40 text-[#C94A2A] font-mono text-[9px] uppercase tracking-wider rounded-btn cursor-pointer transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              Terminate Session
            </button>
          )}
        </div>
      )}
    </div>
  );
};
export default Sidebar;
