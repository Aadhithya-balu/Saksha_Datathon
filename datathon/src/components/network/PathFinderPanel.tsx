import React from 'react';
import type { GraphNode } from './CriminalGraph3D';
import type { NetworkPathResponse } from '../../services/api';
import {
  Waypoints,
  GitCommit,
  Loader2,
  FileText,
  MapPin,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Info,
  SearchX,
  Eye,
  EyeOff,
  User,
} from 'lucide-react';

interface PathFinderPanelProps {
  nodes: GraphNode[];
  pathSource: GraphNode | null;
  pathTarget: GraphNode | null;
  maxHops: number;
  loading: boolean;
  error: string | null;
  result: NetworkPathResponse | null;
  highlightOn: boolean;
  onSetSource: (node: GraphNode | null) => void;
  onSetTarget: (node: GraphNode | null) => void;
  onSetMaxHops: (hops: number) => void;
  onRunSearch: () => void;
  onToggleHighlight: () => void;
  onClear: () => void;
  onSelectNode?: (node: GraphNode) => void;
}

const PERSON_CATEGORIES = new Set(['suspect', 'offender', 'victim', 'officer']);

export const PathFinderPanel: React.FC<PathFinderPanelProps> = ({
  nodes,
  pathSource,
  pathTarget,
  maxHops,
  loading,
  error,
  result,
  highlightOn,
  onSetSource,
  onSetTarget,
  onSetMaxHops,
  onRunSearch,
  onToggleHighlight,
  onClear,
  onSelectNode,
}) => {
  const personNodes = React.useMemo(() => {
    const seen = new Set<string>();
    return nodes
      .filter((n) => PERSON_CATEGORIES.has(n.category) && !seen.has(n.id) && seen.add(n.id))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [nodes]);

  const srcId = pathSource?.id ?? '';
  const tgtId = pathTarget?.id ?? '';
  const canRun = !!pathSource && !!pathTarget && pathSource.id !== pathTarget.id && !loading;
  const sameEntity = !!pathSource && !!pathTarget && pathSource.id === pathTarget.id;

  const findNode = (id: string) => personNodes.find((n) => n.id === id) ?? null;

  const resolveName = (id: string) => result?.nodes?.find((n) => n.id === id)?.name ?? id;

  const summary = result?.summary;
  const hasResult = !!result && result.found;

  return (
    <div className="h-full bg-secondary-bg border border-border-color rounded-card flex flex-col select-none overflow-hidden">
      {/* Header */}
      <div className="p-4 pb-3 border-b border-border-color shrink-0 bg-gradient-to-r from-[#0B1120] to-[#102A3C]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 shrink-0 rounded-full flex items-center justify-center bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
            <Waypoints className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-[var(--text-primary)] uppercase tracking-wider">Connection Path Finder</h3>
            <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
              Evidence-backed path between two entities — constrained to your active search filters
            </p>
          </div>
        </div>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-sm">
        {/* Endpoint selects */}
        <div className="space-y-2.5">
          <div>
            <label className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold flex items-center gap-1">
              <GitCommit className="w-3 h-3" /> Source Entity
            </label>
            <select
              value={srcId}
              onChange={(e) => onSetSource(findNode(e.target.value))}
              className="mt-1 w-full bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-btn px-2.5 py-2 text-xs focus:outline-none focus:border-[var(--accent-blue)] cursor-pointer"
            >
              <option value="">Select source entity...</option>
              {personNodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} — {n.category.toUpperCase()}{n.district ? ` (${n.district})` : ''}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold flex items-center gap-1">
              <GitCommit className="w-3 h-3" /> Target Entity
            </label>
            <select
              value={tgtId}
              onChange={(e) => onSetTarget(findNode(e.target.value))}
              className="mt-1 w-full bg-[var(--bg-primary)] border border-[var(--border-color)] text-[var(--text-primary)] rounded-btn px-2.5 py-2 text-xs focus:outline-none focus:border-[var(--accent-blue)] cursor-pointer"
            >
              <option value="">Select target entity...</option>
              {personNodes.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name} — {n.category.toUpperCase()}{n.district ? ` (${n.district})` : ''}
                </option>
              ))}
            </select>
          </div>
          {sameEntity && (
            <p className="text-[10px] text-[var(--accent-amber)] flex items-center gap-1">
              <Info className="w-3 h-3" /> Select two different entities.
            </p>
          )}
        </div>

        {/* Max hops */}
        <div>
          <label className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold">Max Hops</label>
          <div className="mt-1.5 grid grid-cols-5 gap-1">
            {[1, 2, 3, 4, 5].map((hop) => (
              <button
                key={hop}
                onClick={() => onSetMaxHops(hop)}
                className={`py-1.5 rounded-btn text-[10px] font-bold uppercase border cursor-pointer transition-colors ${
                  maxHops === hop
                    ? 'bg-[var(--accent-blue)] text-[var(--text-primary)] border-[var(--accent-blue)]'
                    : 'bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/20 text-[var(--text-muted)] border-[var(--border-color)]'
                }`}
              >
                {hop}
              </button>
            ))}
          </div>
        </div>

        {/* Run */}
        <button
          onClick={onRunSearch}
          disabled={!canRun}
          className={`w-full py-2.5 rounded-lg text-[11px] uppercase font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
            canRun
              ? 'bg-cyan-500/15 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 shadow-[0_0_14px_rgba(34,211,238,0.15)]'
              : 'bg-[var(--bg-tertiary)] text-[var(--text-disabled)] border border-[var(--border-color)] cursor-not-allowed'
          }`}
        >
          <Waypoints className="w-4 h-4" />
          {loading ? 'Searching...' : 'Find Connection'}
        </button>

        {/* Error banner */}
        {error && (
          <div className="p-3 rounded-lg bg-[var(--accent-coral)]/5 border border-[var(--accent-coral)]/25 text-[var(--accent-coral)] text-[11px] flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center gap-2 py-4 text-[var(--text-muted)]">
            <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
            <span className="text-[10px] uppercase tracking-wider">tracing shared-FIR links within {maxHops} hop{maxHops === 1 ? '' : 's'}</span>
          </div>
        )}

        {/* Result: found */}
        {hasResult && result && (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/25">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-300 text-[10px] font-bold uppercase tracking-wider">Connection found</span>
              </div>
              <span className="text-[11px] text-[var(--text-primary)] font-bold">
                {result.distance} hop{result.distance === 1 ? '' : 's'}
              </span>
            </div>

            {result.message && (
              <p className="text-[11px] text-[var(--text-secondary)] leading-relaxed bg-[var(--bg-secondary)] p-3 rounded-lg border border-[var(--border-color)]">
                {result.message}
              </p>
            )}

            {summary && (
              <div className="grid grid-cols-2 gap-1.5">
                <SummaryChip icon={<FileText className="w-3 h-3" />} label="Supporting FIRs" value={String(summary.supporting_firs)} />
                <SummaryChip icon={<GitCommit className="w-3 h-3" />} label="Edges" value={String(summary.hops)} />
                <SummaryChip icon={<ShieldAlert className="w-3 h-3" />} label="Crime types" value={String(summary.crime_types)} />
                <SummaryChip icon={<MapPin className="w-3 h-3" />} label="Districts" value={String(summary.districts)} />
              </div>
            )}

            {/* Hopped chain */}
            <div>
              <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold mb-1.5">Tracing chain</p>
              <div className="space-y-1.5">
                {result.relationships?.map((rel, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)] hover:border-cyan-500/40 transition-colors">
                    <div className="flex items-center gap-1.5 text-[12px]">
                      <button
                        onClick={() => {
                          const g = nodes.find((n) => n.id === rel.source_id);
                          if (g && onSelectNode) onSelectNode(g);
                        }}
                        className="text-[var(--text-primary)] hover:text-cyan-300 hover:underline truncate cursor-pointer"
                      >
                        {resolveName(rel.source_id)}
                      </button>
                      <span className="text-[var(--accent-blue)] shrink-0">
                        {idx === 0 ? '' : '↔'} <GitCommit className="w-3 h-3 inline" />
                      </span>
                      <button
                        onClick={() => {
                          const g = nodes.find((n) => n.id === rel.target_id);
                          if (g && onSelectNode) onSelectNode(g);
                        }}
                        className="text-[var(--text-primary)] hover:text-cyan-300 hover:underline truncate cursor-pointer"
                      >
                        {resolveName(rel.target_id)}
                      </button>
                    </div>
                    {rel.fir_numbers.length > 0 && (
                      <p className="mt-1 text-[10px] text-[var(--text-muted)] flex items-center gap-1">
                        <FileText className="w-3 h-3 text-[var(--accent-blue)] shrink-0" />
                        Shared FIR{rel.fir_numbers.length === 1 ? '' : 's'}: {rel.fir_numbers.join(', ')}
                        {rel.case_numbers.length > 0 ? ` (${rel.case_numbers.join(', ')})` : ''}
                      </p>
                    )}
                    {(rel.crime_types.length > 0 || rel.districts.length > 0) && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {rel.crime_types.slice(0, 4).map((ct, i) => (
                          <span key={i} className="px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-primary)] text-[9px] border border-[var(--border-color)]">{ct}</span>
                        ))}
                        {rel.districts.slice(0, 3).map((d, i) => (
                          <span key={`d${i}`} className="px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--text-muted)] text-[9px] border border-[var(--border-color)] flex items-center gap-0.5">
                            <MapPin className="w-2.5 h-2.5" /> {d}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Involved entities */}
            {result.nodes && result.nodes.length > 0 && (
              <div>
                <p className="text-[9px] uppercase tracking-wider text-[var(--text-muted)] font-bold mb-1.5">
                  Entities on path ({result.nodes.length})
                </p>
                <div className="flex flex-wrap gap-1">
                  {result.nodes.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => {
                        const g = nodes.find((x) => x.id === n.id);
                        if (g && onSelectNode) onSelectNode(g);
                      }}
                      className="px-1.5 py-0.5 rounded bg-cyan-500/5 hover:bg-cyan-500/15 border border-cyan-500/25 text-[9px] text-cyan-200 cursor-pointer uppercase tracking-wider"
                    >
                      {n.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Result: no path */}
        {result && !result.found && (
          <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/25 flex items-start gap-2">
            <SearchX className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
            <div className="text-[11px] text-[var(--text-secondary)] space-y-1">
              <p className="font-bold text-amber-300 uppercase tracking-wider text-[10px]">No connection found</p>
              <p>{result.message}</p>
              {result.distance < 5 && (
                <p className="text-[10px] text-[var(--text-muted)]">
                  Try increasing the max-hop limit, or widen your search filters to allow intermediate entities.
                </p>
              )}
            </div>
          </div>
        )}

        {/* Initial hint */}
        {!result && !loading && !error && (
          <div className="p-3 rounded-lg bg-cyan-500/5 border border-dashed border-cyan-500/25 text-[10px] text-[var(--text-muted)] flex items-start gap-2">
            <User className="w-3.5 h-3.5 shrink-0 mt-0.5 text-cyan-400" />
            <span>
              Pick two people, officers or victims from the current filtered network. Saksha traces shared-FIR
              participation hop-by-hop and always stays inside your active{' '}
              <span className="text-cyan-300 font-bold">search filters</span>.
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border-color shrink-0 space-y-2">
        {hasResult && (
          <button
            onClick={onToggleHighlight}
            className={`w-full py-1.5 rounded-lg text-[10px] uppercase font-bold flex items-center justify-center gap-1.5 border transition-colors cursor-pointer ${
              highlightOn
                ? 'bg-cyan-500/10 text-cyan-300 border-cyan-500/30'
                : 'bg-[var(--bg-tertiary)] text-[var(--text-muted)] border-[var(--border-color)]'
            }`}
          >
            {highlightOn ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            {highlightOn ? 'Highlighted on graph' : 'Highlight hidden on graph'}
          </button>
        )}
        {hasResult && (
          <button
            onClick={onClear}
            className="w-full py-1.5 rounded-lg text-[10px] uppercase font-bold bg-[var(--bg-tertiary)] hover:bg-[var(--bg-tertiary)]/80 text-[var(--text-muted)] border border-[var(--border-color)] cursor-pointer"
          >
            Show Full Network
          </button>
        )}
        <p className="text-[8.5px] text-[var(--text-muted)] text-center flex items-center justify-center gap-1">
          <ShieldAlert className="w-2.5 h-2.5 text-[var(--accent-amber)]" />
          Paths are computed only inside your active search filters (Issue #226)
        </p>
      </div>
    </div>
  );
};

const SummaryChip: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => (
  <div className="p-2 rounded-lg bg-[var(--bg-secondary)] border border-[var(--border-color)]">
    <div className="flex items-center gap-1.5 text-[8.5px] uppercase tracking-wider text-[var(--text-muted)]">
      {icon}
      {label}
    </div>
    <div className="text-base font-bold text-[var(--text-primary)] mt-0.5">{value}</div>
  </div>
);

export default PathFinderPanel;