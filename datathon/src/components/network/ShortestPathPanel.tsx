import React, { useState } from 'react';
import type { ShortestPathResult } from '../../services/api';
import type { GraphNode } from './CriminalGraph3D';
import { GitCommit, ArrowRight, ShieldAlert, CheckCircle2, Search, Cpu } from 'lucide-react';

interface ShortestPathPanelProps {
  nodes: GraphNode[];
  onCalculatePath: (sourceId: string, targetId: string) => Promise<void>;
  pathResult: ShortestPathResult | null;
  loading: boolean;
  onSelectNodeIn3D?: (node: GraphNode) => void;
}

export const ShortestPathPanel: React.FC<ShortestPathPanelProps> = ({
  nodes,
  onCalculatePath,
  pathResult,
  loading,
  onSelectNodeIn3D,
}) => {
  const [sourceId, setSourceId] = useState<string>(nodes[0]?.id || 'node-1');
  const [targetId, setTargetId] = useState<string>(nodes[1]?.id || 'node-2');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (sourceId && targetId) {
      void onCalculatePath(sourceId, targetId);
    }
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4 bg-[#080E1B] border border-white/10 rounded-card font-mono overflow-y-auto">
      {/* Header */}
      <div className="border-b border-white/10 pb-3">
        <h3 className="text-md font-bold text-white uppercase tracking-wider flex items-center gap-2">
          <GitCommit className="w-5 h-5 text-[#3B82F6] animate-pulse" />
          Shortest Relationship Path Analysis
        </h3>
        <p className="text-[10px] text-[#6A7A96] mt-1">
          CYPHER & GRAPH BFS DEGREES OF SEPARATION BETWEEN TWO CRIMINAL ENTITIES OR LOCATIONS
        </p>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-12 gap-3 bg-[#050912] p-3 rounded-card border border-white/5">
        <div className="md:col-span-5 flex flex-col gap-1">
          <label className="text-[10px] uppercase text-[#8A99AD] font-bold">Start Entity (Source):</label>
          <select
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
            className="w-full bg-[#0d1627] border border-white/10 rounded-btn px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#3B82F6]"
          >
            {nodes.map((n) => (
              <option key={`src-${n.id}`} value={n.id}>
                {n.name} [{n.category.toUpperCase()}]
              </option>
            ))}
          </select>
        </div>

        <div className="md:col-span-5 flex flex-col gap-1">
          <label className="text-[10px] uppercase text-[#8A99AD] font-bold">Target Entity (Destination):</label>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="w-full bg-[#0d1627] border border-white/10 rounded-btn px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#3B82F6]"
          >
            {nodes.map((n) => (
              <option key={`tgt-${n.id}`} value={n.id}>
                {n.name} [{n.category.toUpperCase()}]
              </option>
            ))}
          </select>
        </div>

        <div className="md:col-span-2 flex items-end">
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 bg-[#1E6FD9] hover:bg-[#3B82F6] text-white text-xs font-bold uppercase rounded-btn transition-colors cursor-pointer flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            {loading ? <Cpu className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            Solve Path
          </button>
        </div>
      </form>

      {/* Path Output Results */}
      <div className="flex-1 min-h-[300px] bg-[#050912] p-4 rounded-card border border-white/5 flex flex-col gap-3">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center text-xs text-[#6A7A96] gap-2">
            <Cpu className="w-8 h-8 animate-spin text-[#3B82F6]" />
            <span>Computing shortest path graph traversal...</span>
          </div>
        ) : pathResult ? (
          <div className="space-y-4">
            {/* Status Summary Banner */}
            <div className={`p-3 rounded-card border flex items-center justify-between text-xs font-bold uppercase ${
              pathResult.found
                ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-400'
                : 'bg-rose-950/30 border-rose-500/30 text-rose-400'
            }`}>
              <div className="flex items-center gap-2">
                {pathResult.found ? <CheckCircle2 className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
                <span>{pathResult.found ? `Path Connected (${pathResult.distance} Hop${pathResult.distance > 1 ? 's' : ''})` : 'No Connection Path Found'}</span>
              </div>
              <span className="text-[10px] opacity-75">{pathResult.explanation}</span>
            </div>

            {/* Path Nodes Flow Sequence */}
            {pathResult.found && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase text-[#8A99AD] tracking-wider">Connection Chain Sequence:</h4>
                <div className="flex flex-col gap-2">
                  {pathResult.path_nodes.map((node, idx) => {
                    const edgeRel = pathResult.path_edges[idx]?.relationship;
                    return (
                      <React.Fragment key={`path-item-${node.id}-${idx}`}>
                        {/* Node Card */}
                        <div
                          onClick={() => onSelectNodeIn3D?.(node as GraphNode)}
                          className="p-3 bg-[#0d1627] hover:bg-[#15233e] border border-white/10 rounded-card transition-colors cursor-pointer flex items-center justify-between"
                        >
                          <div className="flex items-center gap-3">
                            <span className="w-6 h-6 rounded-full bg-[#1E6FD9]/30 text-[#60A5FA] border border-[#1E6FD9]/50 flex items-center justify-center text-xs font-bold">
                              {idx + 1}
                            </span>
                            <div>
                              <div className="text-xs font-bold text-white uppercase">{node.name}</div>
                              <div className="text-[10px] text-[#6A7A96] uppercase">{node.category} • Risk: {node.riskScore}</div>
                            </div>
                          </div>
                          <span className="text-[9px] px-2 py-0.5 rounded bg-white/5 border border-white/10 text-[#8A99AD] uppercase">
                            Inspect
                          </span>
                        </div>

                        {/* Edge Connecting Arrow */}
                        {edgeRel && (
                          <div className="flex items-center justify-center gap-2 text-[10px] text-[#3B82F6] font-bold uppercase py-0.5">
                            <ArrowRight className="w-3.5 h-3.5 animate-pulse" />
                            <span>{edgeRel}</span>
                          </div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-xs text-[#6A7A96] text-center p-6 border border-dashed border-white/10 rounded-card">
            <GitCommit className="w-10 h-10 text-white/10 mb-2" />
            <span>Select a start entity and target entity above to calculate degrees of separation and connection chains.</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default ShortestPathPanel;
