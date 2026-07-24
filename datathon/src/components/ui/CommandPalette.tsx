import React, { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppStore } from '../../store/appStore';
import {
  Search,
  LayoutDashboard,
  FileText,
  Map,
  Network,
  Brain,
  Briefcase,
  Bell,
  AlertTriangle,
  Users,
  ShieldAlert,
  Heart,
  BarChart3,
  MessageSquare,
  UserCog,
  FolderOpen,
  Settings,
  BookOpen,
  Command,
  ArrowRight,
  CornerDownLeft,
} from 'lucide-react';

interface CommandItem {
  id: string;
  label: string;
  description?: string;
  icon: React.ReactNode;
  tab: string;
  category: string;
  keywords: string[];
}

const commands: CommandItem[] = [
  { id: 'dashboard', label: 'Overview Dashboard', description: 'View KPIs, trends, and alerts', icon: <LayoutDashboard className="w-4 h-4" />, tab: 'dashboard', category: 'Navigation', keywords: ['overview', 'dashboard', 'home', 'kpi', 'stats'] },
  { id: 'crime_cases', label: 'Crime Cases', description: 'Manage and track crime cases', icon: <Briefcase className="w-4 h-4" />, tab: 'crime_cases', category: 'Navigation', keywords: ['case', 'crime', 'cases', 'manage'] },
  { id: 'investigation', label: 'Investigation', description: 'Investigation workflow and timeline', icon: <Search className="w-4 h-4" />, tab: 'investigation', category: 'Navigation', keywords: ['investigation', 'probe', 'timeline'] },
  { id: 'fir', label: 'FIR Registry', description: 'First Information Reports', icon: <FileText className="w-4 h-4" />, tab: 'fir', category: 'Navigation', keywords: ['fir', 'report', 'information'] },
  { id: 'hotspot', label: 'Hotspot Map', description: 'Crime hotspot spatial analysis', icon: <Map className="w-4 h-4" />, tab: 'hotspot', category: 'Navigation', keywords: ['hotspot', 'map', 'spatial', 'location'] },
  { id: 'network', label: 'Network Graph', description: 'Criminal network visualization', icon: <Network className="w-4 h-4" />, tab: 'network', category: 'Navigation', keywords: ['network', 'graph', 'connections', 'links'] },
  { id: 'predictive', label: 'Predictive AI', description: 'AI-powered crime predictions', icon: <Brain className="w-4 h-4" />, tab: 'predictive', category: 'Navigation', keywords: ['predict', 'ai', 'forecast', 'risk'] },
  { id: 'anomaly', label: 'Anomaly Feed', description: 'Real-time anomaly detection alerts', icon: <AlertTriangle className="w-4 h-4" />, tab: 'anomaly', category: 'Navigation', keywords: ['anomaly', 'alert', 'unusual', 'detect'] },
  { id: 'offenders', label: 'Offender Registry', description: 'Criminal offender profiles', icon: <ShieldAlert className="w-4 h-4" />, tab: 'offenders', category: 'Registry', keywords: ['offender', 'criminal', 'profile', 'registry'] },
  { id: 'criminals', label: 'Criminal Dossiers', description: 'Detailed criminal records', icon: <Users className="w-4 h-4" />, tab: 'criminals', category: 'Registry', keywords: ['criminal', 'dossier', 'record'] },
  { id: 'victims', label: 'Victims Registry', description: 'Victim and witness profiles', icon: <Heart className="w-4 h-4" />, tab: 'victims', category: 'Registry', keywords: ['victim', 'witness', 'registry'] },
  { id: 'officers', label: 'Officer Management', description: 'Police officer directory', icon: <UserCog className="w-4 h-4" />, tab: 'officers', category: 'Registry', keywords: ['officer', 'police', 'directory', 'management'] },
  { id: 'evidence', label: 'Evidence Handling', description: 'Evidence chain of custody', icon: <FolderOpen className="w-4 h-4" />, tab: 'evidence', category: 'Registry', keywords: ['evidence', 'custody', 'forensic', 'proof'] },
  { id: 'notifications', label: 'Intelligence Center', description: 'Notifications and activity feed', icon: <Bell className="w-4 h-4" />, tab: 'notifications', category: 'System', keywords: ['notification', 'alert', 'intelligence', 'feed'] },
  { id: 'reports', label: 'Reports Center', description: 'Generate and export reports', icon: <BarChart3 className="w-4 h-4" />, tab: 'reports', category: 'Tools', keywords: ['report', 'export', 'download', 'pdf', 'csv'] },
  { id: 'ai_chat', label: 'AI Assistant', description: 'Conversational AI for crime analysis', icon: <MessageSquare className="w-4 h-4" />, tab: 'ai_chat', category: 'Tools', keywords: ['ai', 'chat', 'assistant', 'ask', 'copilot'] },
  { id: 'docs', label: 'Documentation', description: 'Platform guides and documentation', icon: <BookOpen className="w-4 h-4" />, tab: 'docs', category: 'Tools', keywords: ['docs', 'documentation', 'help', 'guide', 'manual'] },
  { id: 'settings', label: 'Settings', description: 'System settings and admin panel', icon: <Settings className="w-4 h-4" />, tab: 'settings_help', category: 'System', keywords: ['settings', 'admin', 'config', 'preferences'] },
];

export const CommandPalette: React.FC = () => {
  const { commandPaletteOpen, setCommandPaletteOpen, setActiveTab } = useAppStore();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    if (!query.trim()) return commands;
    const q = query.toLowerCase();
    return commands.filter(
      (cmd) =>
        cmd.label.toLowerCase().includes(q) ||
        cmd.description?.toLowerCase().includes(q) ||
        cmd.keywords.some((kw) => kw.includes(q))
    );
  }, [query]);

  useEffect(() => {
    if (commandPaletteOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [commandPaletteOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const execute = (cmd: CommandItem) => {
    setActiveTab(cmd.tab);
    setCommandPaletteOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && filtered[selectedIndex]) {
      execute(filtered[selectedIndex]);
    } else if (e.key === 'Escape') {
      setCommandPaletteOpen(false);
    }
  };

  // Scroll selected item into view
  useEffect(() => {
    const list = listRef.current;
    if (!list) return;
    const item = list.children[selectedIndex] as HTMLElement;
    if (item) {
      item.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  return (
    <AnimatePresence>
      {commandPaletteOpen && (
        <div className="fixed inset-0 flex items-start justify-center pt-[15vh]" style={{ zIndex: 500 }}>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setCommandPaletteOpen(false)}
          />

          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -10 }}
            transition={{ duration: 0.15, ease: [0.4, 0, 0.2, 1] }}
            className="relative w-full max-w-lg bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-xl shadow-sk-xl overflow-hidden"
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--border-secondary)]">
              <Search className="w-5 h-5 text-[var(--text-muted)] shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search modules, pages, actions..."
                className="flex-1 bg-transparent text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)] outline-none"
              />
              <kbd className="hidden sm:inline-flex items-center px-1.5 py-0.5 text-[10px] font-mono bg-[var(--bg-tertiary)] border border-[var(--border-secondary)] rounded text-[var(--text-muted)]">
                ESC
              </kbd>
            </div>

            {/* Results */}
            <div ref={listRef} className="max-h-[320px] overflow-y-auto p-2">
              {filtered.length === 0 ? (
                <div className="py-8 text-center text-sm text-[var(--text-muted)]">No results found</div>
              ) : (
                <>
                  {['Navigation', 'Registry', 'Tools', 'System'].map((category) => {
                    const items = filtered.filter((c) => c.category === category);
                    if (items.length === 0) return null;
                    return (
                      <div key={category} className="mb-2">
                        <div className="px-3 py-1.5 text-[10px] font-semibold tracking-wider text-[var(--text-disabled)] uppercase">
                          {category}
                        </div>
                        {items.map((cmd) => {
                          const globalIndex = filtered.indexOf(cmd);
                          return (
                            <button
                              key={cmd.id}
                              onClick={() => execute(cmd)}
                              onMouseEnter={() => setSelectedIndex(globalIndex)}
                              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors cursor-pointer ${
                                globalIndex === selectedIndex
                                  ? 'bg-[var(--accent-blue)]/10 text-[var(--text-primary)]'
                                  : 'text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                              }`}
                            >
                              <span className="shrink-0 text-[var(--text-muted)]">{cmd.icon}</span>
                              <div className="flex-1 min-w-0">
                                <div className="text-sm font-medium truncate">{cmd.label}</div>
                                {cmd.description && (
                                  <div className="text-[11px] text-[var(--text-muted)] truncate">{cmd.description}</div>
                                )}
                              </div>
                              <ArrowRight className={`w-3.5 h-3.5 shrink-0 transition-opacity ${
                                globalIndex === selectedIndex ? 'opacity-100' : 'opacity-0'
                              }`} />
                            </button>
                          );
                        })}
                      </div>
                    );
                  })}
                </>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center gap-4 px-4 py-2 border-t border-[var(--border-secondary)] text-[10px] text-[var(--text-muted)]">
              <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 bg-[var(--bg-tertiary)] border border-[var(--border-secondary)] rounded font-mono">↑↓</kbd> Navigate</span>
              <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 bg-[var(--bg-tertiary)] border border-[var(--border-secondary)] rounded font-mono"><CornerDownLeft className="w-2.5 h-2.5 inline" /></kbd> Select</span>
              <span className="flex items-center gap-1"><kbd className="px-1 py-0.5 bg-[var(--bg-tertiary)] border border-[var(--border-secondary)] rounded font-mono">esc</kbd> Close</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default CommandPalette;
