import React from 'react';
import type { NetworkWorkspaceView } from '../../hooks/useNetwork';
import {
  Share2,
  GitCommit,
  Users,
  BarChart3,
  Calendar,
  Sparkles,
  RefreshCw,
  Sliders,
  Database,
  Search,
} from 'lucide-react';

interface GraphExplorerToolbarProps {
  activeView: NetworkWorkspaceView;
  setActiveView: (view: NetworkWorkspaceView) => void;
  categoryFilter: string;
  setCategoryFilter: (cat: string) => void;
  minRisk: number;
  setMinRisk: (val: number) => void;
  isNeo4jBacked: boolean;
  onExportMatrix: () => void;
  onNeo4jSync: () => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export const GraphExplorerToolbar: React.FC<GraphExplorerToolbarProps> = ({
  activeView,
  setActiveView,
  categoryFilter,
  setCategoryFilter,
  minRisk,
  setMinRisk,
  isNeo4jBacked,
  onExportMatrix,
  onNeo4jSync,
  searchQuery,
  setSearchQuery,
}) => {
  const views: { id: NetworkWorkspaceView; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: '3d_explorer', label: '3D Graph Explorer', icon: Share2 },
    { id: 'shortest_path', label: 'Shortest Path', icon: GitCommit },
    { id: 'gangs', label: 'Gang Networks', icon: Users },
    { id: 'link_analysis', label: 'Link Analysis', icon: BarChart3 },
    { id: 'timeline', label: 'Timeline View', icon: Calendar },
    { id: 'ai_insights', label: 'AI Insights', icon: Sparkles },
  ];

  return (
    <div className="flex flex-col gap-3 bg-[#0a101d] p-3 rounded-card border border-white/10 shadow-lg font-mono">
      {/* Top Navigation Row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Workspace View Mode Selector */}
        <div className="flex items-center gap-1.5 bg-[#050912] p-1 rounded-btn border border-white/5 overflow-x-auto">
          {views.map((v) => {
            const Icon = v.icon;
            const isActive = activeView === v.id;
            return (
              <button
                key={v.id}
                onClick={() => setActiveView(v.id)}
                className={`px-3 py-1.5 rounded-btn text-[11px] font-bold tracking-wider uppercase transition-all flex items-center gap-2 cursor-pointer whitespace-nowrap ${
                  isActive
                    ? 'bg-[#1E6FD9] text-white shadow-[0_0_12px_rgba(30,111,217,0.5)] border border-[#3B82F6]'
                    : 'text-[#8A99AD] hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white animate-pulse' : 'text-[#8A99AD]'}`} />
                <span>{v.label}</span>
              </button>
            );
          })}
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2 text-[10px] uppercase">
          {/* Neo4j Status Badge */}
          <div
            className={`px-2.5 py-1.5 rounded-btn border flex items-center gap-1.5 text-[9.5px] font-bold ${
              isNeo4jBacked
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30'
                : 'bg-amber-950/40 text-amber-400 border-amber-500/30'
            }`}
          >
            <Database className="w-3 h-3" />
            <span>{isNeo4jBacked ? 'Neo4j Connected' : 'SQL Graph Fallback'}</span>
          </div>

          <button
            onClick={onNeo4jSync}
            title="Sync PostgreSQL relational records to Neo4j Graph"
            className="px-2.5 py-1.5 bg-[#111D35] hover:bg-[#1E6FD9]/20 border border-[#1e6fd9]/30 text-[#A8B4CC] hover:text-white rounded-btn transition-colors cursor-pointer flex items-center gap-1.5"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Sync Neo4j</span>
          </button>

          <button
            onClick={onExportMatrix}
            className="px-2.5 py-1.5 bg-[#1E6FD9]/15 hover:bg-[#1E6FD9]/30 border border-[#1E6FD9]/40 text-[#60A5FA] hover:text-white rounded-btn transition-colors cursor-pointer flex items-center gap-1.5 font-bold"
          >
            <Share2 className="w-3 h-3" />
            <span>Export Matrix</span>
          </button>
        </div>
      </div>

      {/* Bottom Filter & Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-white/5 text-[11px]">
        {/* Node Search Bar */}
        <div className="relative flex-1 min-w-[220px] max-w-sm">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#6A7A96]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search suspect, case, location..."
            className="w-full bg-[#050912] border border-white/10 rounded-btn pl-8 pr-3 py-1.5 text-xs text-white placeholder-[#6A7A96] focus:outline-none focus:border-[#1E6FD9]"
          />
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#6A7A96] uppercase font-bold flex items-center gap-1">
            <Sliders className="w-3 h-3 text-[#1E6FD9]" /> Entity:
          </span>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-[#050912] border border-white/10 text-white rounded-btn px-2.5 py-1 text-xs focus:outline-none focus:border-[#1E6FD9]"
          >
            <option value="all">All Categories</option>
            <option value="suspect">Suspects (At Large)</option>
            <option value="offender">Known Offenders</option>
            <option value="case">Cases / FIRs</option>
            <option value="location">Jurisdiction Hotspots</option>
            <option value="victim">Victims & Complainants</option>
          </select>
        </div>

        {/* Risk Threshold Slider */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#6A7A96] uppercase font-bold">Min Risk: {minRisk}</span>
          <input
            type="range"
            min={0}
            max={90}
            step={5}
            value={minRisk}
            onChange={(e) => setMinRisk(Number(e.target.value))}
            className="w-24 accent-[#1E6FD9] cursor-pointer"
          />
        </div>
      </div>
    </div>
  );
};

export default GraphExplorerToolbar;
