import React from 'react';
import { useRBAC } from '../../hooks/useRBAC';
import { useNotificationStore } from '../../store/notificationStore';
import { useAppStore } from '../../store/appStore';
import {
  LayoutDashboard,
  Map,
  FileText,
  MessageSquare,
  Menu,
} from 'lucide-react';

interface MobileBottomBarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenDrawer: () => void;
}

interface TabItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const primaryTabs: TabItem[] = [
  { id: 'dashboard', label: 'Home', icon: <LayoutDashboard className="w-5 h-5" /> },
  { id: 'hotspot', label: 'Hotspots', icon: <Map className="w-5 h-5" /> },
  { id: 'fir', label: 'FIR', icon: <FileText className="w-5 h-5" /> },
  { id: 'ai_chat', label: 'AI', icon: <MessageSquare className="w-5 h-5" /> },
];

export const MobileBottomBar: React.FC<MobileBottomBarProps> = ({
  activeTab,
  setActiveTab,
  onOpenDrawer,
}) => {
  const { checkPermission } = useRBAC();
  const unread = useNotificationStore((s) => s.counts.unread);
  const setMobileMenuOpen = useAppStore((s) => s.setMobileMenuOpen);

  const handleTab = (id: string) => {
    setActiveTab(id);
  };

  const items = primaryTabs.filter((t) => checkPermission('/' + t.id) || t.id === 'ai_chat');

  return (
    <nav
      aria-label="Mobile navigation"
      className="md:hidden fixed bottom-0 inset-x-0 z-[210] flex items-stretch justify-around h-16
        bg-[var(--bg-secondary)]/90 backdrop-blur-xl border-t border-[var(--border-primary)]
        shadow-[0_-8px_24px_rgba(0,0,0,0.18)] select-none"
    >
      {items.map((item) => {
        const isActive = activeTab === item.id;
        return (
          <button
            key={item.id}
            onClick={() => handleTab(item.id)}
            className={`relative flex-1 flex flex-col items-center justify-center gap-1 px-1
              transition-colors duration-150 cursor-pointer ${isActive ? 'text-[var(--accent-blue)]' : 'text-[var(--text-muted)]'}`}
            title={item.label}
          >
            <span className="relative">
              {item.icon}
              {item.id === 'ai_chat' && unread > 0 && (
                <span className="absolute -top-1 -right-1 w-2 h-2 bg-[var(--accent-coral)] rounded-full" />
              )}
            </span>
            <span className="text-[10px] font-medium uppercase tracking-wide">{item.label}</span>
            {isActive && (
              <span className="absolute top-0 w-8 h-0.5 rounded-full bg-[var(--accent-blue)]" />
            )}
          </button>
        );
      })}

      <button
        onClick={() => {
          setMobileMenuOpen(true);
          onOpenDrawer();
        }}
        className="flex-1 flex flex-col items-center justify-center gap-1 px-1 text-[var(--text-muted)] cursor-pointer"
        title="More"
      >
        <span className="relative">
          <Menu className="w-5 h-5" />
          {unread > 0 && (
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-[var(--accent-coral)] rounded-full" />
          )}
        </span>
        <span className="text-[10px] font-medium uppercase tracking-wide">More</span>
      </button>
    </nav>
  );
};

export default MobileBottomBar;
