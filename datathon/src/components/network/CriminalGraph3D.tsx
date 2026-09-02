import React, { useState, useRef, useEffect, useMemo, useCallback, type RefObject } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { AlertTriangle, Maximize2, ChevronUp, ChevronDown, Crosshair, ZoomIn, ZoomOut } from 'lucide-react';
import type { NetworkNodeCategory } from '../../services/api';
import { useAppStore } from '../../store/appStore';

export interface GraphNode {
  id: string;
  name: string;
  category: NetworkNodeCategory;
  riskScore: number;
  details: string;
  casesCount: number;
  phone?: string | null;
  gangAffiliation?: string | null;
  status?: string | null;
  district?: string | null;
  date?: string | null;
  /** True when the record originates from the bundled demo seed dataset (gap 132.4). */
  isSeed?: boolean;
  /** Spatial coordinates assigned by the force-graph simulation at render time. */
  x?: number;
  y?: number;
  z?: number;
}

export interface GraphLink {
  source: string | any;
  target: string | any;
  relationship: string;
  weight?: number;
  first_seen?: string | null;
  last_seen?: string | null;
  provenance?: 'DIRECT_DATABASE' | 'ANALYTICAL_INFERENCE' | 'DEMO_SEED' | 'MIXED' | 'UNKNOWN' | string;
  verification_status?: 'VERIFIED' | 'POTENTIAL' | 'UNVERIFIED' | 'DEMO' | string;
  relationship_type?: string;
  evidence?: Array<{
    record_type?: string;
    record_id?: string;
    record_number?: string;
    details?: string;
    timestamp?: string | null;
    factors?: string[];
  }>;
  confidence?: number | null;
  confidence_level?: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN' | string;
  is_demo_derived?: boolean;
  operational_warning?: string | null;
}

const EMPTY_GRAPH_DATA: { nodes: GraphNode[]; links: GraphLink[] } = { nodes: [], links: [] };

interface CriminalGraph3DProps {
  onNodeSelect?: (node: GraphNode) => void;
  onLinkSelect?: (link: GraphLink) => void;
  graphData?: {
    nodes: GraphNode[];
    links: GraphLink[];
  };
  /** Issue #230: node ids + undirected edge keys (`min~max`) to emphasize after a
   *  connection-path search. All non-highlighted content is dimmed while active. */
  highlightPath?: {
    nodeIds: string[];
    linkKeys: string[];
  } | null;
}

export const CriminalGraph3D: React.FC<CriminalGraph3DProps> = ({ onNodeSelect, onLinkSelect, graphData, highlightPath }) => {
  const fgRef = useRef<any>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const resolvedGraphData = useMemo(() => graphData ?? EMPTY_GRAPH_DATA, [graphData]);
  const [currentGraphData, setCurrentGraphData] = useState(resolvedGraphData);
  const [hasError, setHasError] = useState(false);
  const [legendOpen, setLegendOpen] = useState(false);
  const theme = useAppStore((s) => s.theme);
  const isLight = theme === 'light';
  const canvasBg = isLight ? '#f7f9fc' : '#080E1B';

  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

  // Issue #230: normalize the highlighted path so nodes/edges can be emphasized.
  const pathNodeIds = useMemo(() => {
    const set = new Set(highlightPath?.nodeIds ?? []);
    return set;
  }, [highlightPath]);
  const pathLinkKeys = useMemo(() => {
    const set = new Set(highlightPath?.linkKeys ?? []);
    return set;
  }, [highlightPath]);
  const hasHighlight = !!highlightPath && (pathNodeIds.size > 0 || pathLinkKeys.size > 0);

  const linkKey = (link: GraphLink): string => {
    const sId = typeof link.source === 'object' ? (link.source as any).id : link.source;
    const tId = typeof link.target === 'object' ? (link.target as any).id : link.target;
    return [String(sId), String(tId)].sort().join('~');
  };
  const isPathLink = (link: GraphLink): boolean => pathLinkKeys.has(linkKey(link));
  const isPathNode = (node: GraphNode): boolean => pathNodeIds.has(node.id);

  // Issue #230: nodes that keep a permanent on-canvas label — the selection plus
  // every entity on the highlighted connection path.
  const labeledNodes = useMemo(() => {
    if (!selectedNodeId && !hasHighlight) return [];
    return currentGraphData.nodes.filter((n) => n.id === selectedNodeId || (hasHighlight && isPathNode(n)));
  }, [currentGraphData, selectedNodeId, hasHighlight, pathNodeIds]);

  useEffect(() => {
    if (!containerRef.current) return;
    
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({
          width: width || 600,
          height: height || 400
        });
      }
    });
    
    resizeObserver.observe(containerRef.current);
    
    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    setCurrentGraphData(resolvedGraphData);
    // Reset auto-fit so new graph data triggers camera fit (Issue #189)
    hasAutoFit.current = false;
  }, [resolvedGraphData]);

  // Compute degree centrality for node scaling
  const degreeMap = useMemo(() => {
    const deg: Record<string, number> = {};
    for (const link of currentGraphData.links) {
      const src = typeof link.source === 'object' ? (link.source as any).id : link.source;
      const tgt = typeof link.target === 'object' ? (link.target as any).id : link.target;
      deg[src] = (deg[src] || 0) + 1;
      deg[tgt] = (deg[tgt] || 0) + 1;
    }
    return deg;
  }, [currentGraphData]);

  // Configure force simulation for better layout
  useEffect(() => {
    if (fgRef.current && !hasError) {
      const engine = fgRef.current.d3Force;
      if (engine) {
        // Set custom link distance based on relationship type
        const linkForce = engine('link');
        if (linkForce) {
          linkForce.distance((link: any) => {
            const type = link.relationship_type || link.relationship || '';
            if (type.includes('USED') || type.includes('LINKED')) return 80;
            if (type.includes('KNOWS') || type.includes('ASSOCIATED')) return 140;
            return 110;
          });
        }
        // Increase charge repulsion to spread nodes apart
        const chargeForce = engine('charge');
        if (chargeForce) {
          chargeForce.strength(-280);
        }
      }
    }
  }, [hasError, currentGraphData]);

  // Auto-fit camera on initial data load
  const hasAutoFit = useRef(false);
  useEffect(() => {
    if (currentGraphData.nodes.length > 0 && !hasAutoFit.current && fgRef.current && !hasError) {
      hasAutoFit.current = true;
      setTimeout(() => {
        fgRef.current?.zoomToFit(400, 30);
      }, 2500);
    }
  }, [currentGraphData, hasError]);

  // Node Clicked Action — zoom camera close to the node
  const handleNodeClick = (node: any) => {
    if (fgRef.current && fgRef.current.cameraPosition) {
      const distance = 45;
      const norm = Math.hypot(node.x || 0, node.y || 0, node.z || 0) || 1;
      fgRef.current.cameraPosition(
        {
          x: (node.x || 0) + (node.x || 0) / norm * distance,
          y: (node.y || 0) + (node.y || 0) / norm * distance + 15,
          z: (node.z || 0) + (node.z || 0) / norm * distance + distance,
        },
        node,
        1500
      );
    }
    const fullNode = currentGraphData.nodes.find(n => n.id === node.id);
    if (fullNode) {
      setSelectedNodeId(fullNode.id);
      onNodeSelect?.(fullNode);
    }
  };

  // Link Clicked Action (Issue #159)
  const handleLinkClick = (link: any) => {
    if (onLinkSelect) {
      onLinkSelect(link);
    }
  };

  // Issue #189: Center camera on the currently selected node
  const handleCenterSelected = useCallback(() => {
    if (!selectedNodeId || !fgRef.current || hasError) return;
    const node = currentGraphData.nodes.find(n => n.id === selectedNodeId);
    if (!node) return;
    const distance = 45;
    const norm = Math.hypot(node.x || 0, node.y || 0, node.z || 0) || 1;
    if (fgRef.current.cameraPosition) {
      fgRef.current.cameraPosition(
        {
          x: (node.x || 0) + (node.x || 0) / norm * distance,
          y: (node.y || 0) + (node.y || 0) / norm * distance + 15,
          z: (node.z || 0) + (node.z || 0) / norm * distance + distance,
        },
        node,
        800
      );
    }
  }, [selectedNodeId, currentGraphData, hasError]);

  // Color matching for nodes
  const getNodeColor = (cat: string) => {
    switch (cat) {
      case 'suspect': return '#C94A2A'; // Red
      case 'offender': return '#D4820A'; // Amber
      case 'location': return '#1E6FD9'; // Blue
      case 'case': return '#0E9E78'; // Green
      case 'victim': return '#6A7A96'; // Grey
      case 'officer': return '#14C997'; // Teal
      default: return '#6C43CC';
    }
  };

  // Color matching for link provenance (Issue #159)
  const getLinkColor = (link: GraphLink) => {
    if (link.verification_status === 'VERIFIED' || link.provenance === 'DIRECT_DATABASE') {
      return isLight ? 'rgba(5, 150, 105, 0.85)' : 'rgba(16, 185, 129, 0.85)';
    }
    if (link.verification_status === 'POTENTIAL' || link.provenance === 'ANALYTICAL_INFERENCE') {
      return isLight ? 'rgba(217, 119, 6, 0.95)' : 'rgba(245, 158, 11, 0.95)';
    }
    if (link.is_demo_derived || link.provenance === 'DEMO_SEED' || link.provenance === 'MIXED') {
      return isLight ? 'rgba(124, 58, 237, 0.75)' : 'rgba(168, 85, 247, 0.75)';
    }
    return isLight ? 'rgba(100, 116, 139, 0.6)' : 'rgba(148, 163, 184, 0.55)';
  };

  // Slow orbital rotation when idle
  useEffect(() => {
    if (fgRef.current && !hasError) {
      fgRef.current.controls().autoRotate = true;
      fgRef.current.controls().autoRotateSpeed = 0.65;
    }
  }, [hasError]);

  return (
    <div className="w-full h-full relative bg-[var(--bg-surface)] rounded-card border border-border-color flex flex-col justify-between overflow-hidden" style={{ minHeight: '500px' }}>
      
      {/* STATUS OVERLAY */}
      <div className="absolute top-4 left-4 z-20 pointer-events-auto">
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--bg-tertiary)]/90 backdrop-blur-sm border border-[var(--border-color)] rounded-btn text-[9px] font-mono uppercase tracking-wider text-[var(--text-muted)]">
          <span>{currentGraphData.nodes.length} NODES</span>
          <span className="text-[var(--border-color)]">/</span>
          <span>{currentGraphData.links.length} EDGES</span>
          <span className="ml-2 text-[var(--text-disabled)]">CLICK NODE &rarr; DOSSIER &bull; EDGE &rarr; LINK</span>
          {hasHighlight && (
            <span className="ml-2 inline-flex items-center gap-1 text-cyan-300">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-300 animate-pulse" />
              CONNECTION PATH
            </span>
          )}
        </div>
      </div>

      {/* GRAPH VIEWPORT */}
      <div ref={containerRef} className="flex-1 w-full h-full relative" style={{ minHeight: '460px' }}>
        {hasError ? (
          <GraphFallback onNodeSelect={onNodeSelect} onLinkSelect={onLinkSelect} isLight={isLight} graphData={currentGraphData} />
        ) : (
          <ErrorBoundary fallback={<GraphFallback onNodeSelect={onNodeSelect} onLinkSelect={onLinkSelect} isLight={isLight} graphData={currentGraphData} />} onError={() => setHasError(true)}>
            <ForceGraph3D
              ref={fgRef}
              graphData={currentGraphData}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor={canvasBg}
              showNavInfo={false}
              nodeLabel={(node) => `<div style="font-family:monospace;font-size:10px;line-height:1.4;pointer-events:none">
                <b style="color:#e8edf5">${node.name}</b><br />
                <span style="color:${getNodeColor(node.category)}">${(node.category || 'entity').toUpperCase()}</span>
                <span style="color:#94a3b8"> &bull; risk ${node.riskScore ?? 0}% &bull; ${node.casesCount ?? 0} linked cases</span>
                ${node.district ? `<br /><span style="color:#94a3b8">district ${node.district}</span>` : ''}
              </div>`}
              nodeColor={node => {
                if (node.id === selectedNodeId) return '#FFFFFF';
                if (hasHighlight && isPathNode(node)) return '#22D3EE';
                if (hasHighlight) return isLight ? '#93A1B5' : '#3E4C63';
                return getNodeColor(node.category);
              }}
              nodeOpacity={selectedNodeId ? 0.35 : 1}
              nodeVal={node => {
                const deg = degreeMap[node.id] || 0;
                const base = node.category === 'suspect' ? 18 + Math.min(deg * 3, 20) : 12 + Math.min(deg * 2, 14);
                return hasHighlight && (isPathNode(node) || node.id === selectedNodeId) ? base + 7 : base;
              }}
              nodeResolution={24}
              nodeRelSize={8}
              linkLabel={(link) => {
                const l = link as GraphLink;
                const provenance = l.provenance || 'DIRECT_DATABASE';
                const status = l.verification_status || 'VERIFIED';
                return `<div style="font-family:monospace;font-size:10px;line-height:1.4;pointer-events:none">
                  <b style="color:#e8edf5">${l.relationship || 'RELATIONSHIP'}</b><br />
                  <span style="color:${getLinkColor(l)}">${provenance.replace(/_/g, ' ')} &bull; ${status.replace(/_/g, ' ')}</span>
                  ${l.weight !== undefined && l.weight !== null ? `<br /><span style="color:#94a3b8">strength ${l.weight}</span>` : ''}
                </div>`;
              }}
              linkColor={link => {
                const l = link as GraphLink;
                if (hasHighlight) {
                  if (isPathLink(l)) return '#22D3EE';
                  return isLight ? 'rgba(100, 116, 139, 0.10)' : 'rgba(148, 163, 184, 0.10)';
                }
                return getLinkColor(l);
              }}
              linkDirectionalParticles={link => {
                const l = link as GraphLink;
                if (hasHighlight) {
                  if (isPathLink(l)) return 4;
                  return 0;
                }
                return l.verification_status === 'POTENTIAL' ? 3 : 1.5;
              }}
              linkDirectionalParticleSpeed={0.018}
              linkDirectionalParticleWidth={2.5}
              linkWidth={link => {
                const l = link as GraphLink;
                if (hasHighlight) {
                  if (isPathLink(l)) return 5;
                  return 1.2;
                }
                return l.verification_status === 'VERIFIED' ? 3.5 : 2.5;
              }}
              d3AlphaDecay={0.015}
              d3VelocityDecay={0.35}
              d3AlphaMin={0.0005}
              cooldownTime={12000}
              warmupTicks={50}
              rendererConfig={{ antialias: true }}
              onNodeClick={handleNodeClick}
              onLinkClick={handleLinkClick}
              onEngineStop={() => {
                if (fgRef.current && !hasError) {
                  fgRef.current.zoomToFit(400, 30);
                }
              }}
            />
          </ErrorBoundary>
        )}

        {/* Permanent labels for selection + highlighted connection path (Issue #230) */}
        <NodePinOverlay fgRef={fgRef} nodes={labeledNodes} />

        {/* Provenance & Node Legend overlay (Issue #159) — collapsible */}
        <div
          className={`absolute bottom-4 left-4 z-20 bg-[#0B1120] border border-[#334155] rounded-card shadow-2xl font-mono select-none pointer-events-auto transition-all duration-200 ${
            legendOpen ? 'p-3 w-[210px]' : 'p-1.5 w-auto'
          }`}
        >
          <button
            onClick={() => setLegendOpen(v => !v)}
            className="flex items-center gap-1.5 cursor-pointer text-[8px] font-bold text-[#94A3B8] uppercase tracking-wider hover:text-emerald-400 transition-colors"
          >
            <span className={`w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse ${legendOpen ? '' : 'mr-0.5'}`} />
            Legend
            {legendOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
          </button>

          {legendOpen && (
            <>
              <div className="flex flex-col gap-1.5 pt-2 mt-1">
                <div className="flex items-center gap-2 bg-[#0F172A] px-2 py-1 rounded border border-[#1E293B]">
                  <span className="w-4 h-1 bg-emerald-400 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                  <span className="text-emerald-300 font-semibold text-[9px]">Direct Fact (Verified)</span>
                </div>
                <div className="flex items-center gap-2 bg-[#0F172A] px-2 py-1 rounded border border-[#1E293B]">
                  <span className="w-4 h-1 border-t-2 border-dashed border-amber-400 shadow-[0_0_8px_rgba(245,158,11,0.8)]" />
                  <span className="text-amber-300 font-semibold text-[9px]">Analytical Lead (Potential)</span>
                </div>
                <div className="flex items-center gap-2 bg-[#0F172A] px-2 py-1 rounded border border-[#1E293B]">
                  <span className="w-4 h-1 bg-purple-400 rounded-full shadow-[0_0_8px_rgba(168,85,247,0.8)]" />
                  <span className="text-purple-300 font-semibold text-[9px]">Demo / Seed Link</span>
                </div>
              </div>
              
              <div className="border-t border-[#1E293B] pt-2 mt-2 flex flex-col gap-1">
                <span className="text-[8px] font-bold text-[#94A3B8] uppercase tracking-wider">Entity Clearance</span>
                <div className="flex items-center gap-2 bg-[#0F172A] px-2 py-1 rounded border border-[#1E293B]">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#EF4444] shadow-[0_0_6px_rgba(239,68,68,0.8)]" />
                  <span className="text-slate-200 text-[9px]">Suspect</span>
                  <span className="w-2.5 h-2.5 rounded-full bg-[#F59E0B] shadow-[0_0_6px_rgba(245,158,11,0.8)] ml-1" />
                  <span className="text-slate-200 text-[9px]">Offender</span>
                </div>
              </div>

              <div className="border-t border-[#1E293B] pt-2 mt-2 flex items-center gap-2 bg-[#0F172A] px-2 py-1 rounded border border-[#1E293B]">
                <span className="text-[8px] text-[#94A3B8]">
                  {currentGraphData.nodes.length} nodes, {currentGraphData.links.length} edges
                </span>
              </div>
            </>
          )}
        </div>

        {/* Floating Zoom Controls (Issue #189: added center-selected button) */}
        <div className="absolute bottom-4 right-4 z-20 flex flex-col gap-1.5 pointer-events-auto">
          <button
            onClick={() => {
              if (fgRef.current) {
                const pos = fgRef.current.cameraPosition();
                if (pos) {
                  const scale = 0.7;
                  fgRef.current.cameraPosition(
                    { x: pos.x * scale, y: pos.y * scale, z: pos.z * scale },
                    undefined, 400
                  );
                }
              }
            }}
            title="Zoom in"
            className="p-2 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/15 border border-border-color hover:border-[var(--accent-blue)]/30 rounded text-[var(--text-secondary)] cursor-pointer"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              if (fgRef.current) {
                const pos = fgRef.current.cameraPosition();
                if (pos) {
                  const scale = 1.4;
                  fgRef.current.cameraPosition(
                    { x: pos.x * scale, y: pos.y * scale, z: pos.z * scale },
                    undefined, 400
                  );
                }
              }
            }}
            title="Zoom out"
            className="p-2 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/15 border border-border-color hover:border-[var(--accent-blue)]/30 rounded text-[var(--text-secondary)] cursor-pointer"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => fgRef.current?.zoomToFit(400, 30)}
            title="Fit all nodes in view"
            className="p-2 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/15 border border-border-color hover:border-[var(--accent-blue)]/30 rounded text-[var(--text-secondary)] cursor-pointer"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
          {selectedNodeId && (
            <button
              onClick={handleCenterSelected}
              title="Center on selected node"
              className="p-2 bg-[var(--accent-blue)]/15 hover:bg-[var(--accent-blue)]/25 border border-[var(--accent-blue)]/30 hover:border-[var(--accent-blue)]/50 rounded text-[var(--accent-blue)] cursor-pointer"
            >
              <Crosshair className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

    </div>
  );
};

// Issue #230: HTML label layer that tracks selected/path nodes in screen space on
// every animation frame. Only mounts while at least one node needs a permanent
// label, so normal browsing keeps the canvas completely unlabeled.
const NodePinOverlay = ({ fgRef, nodes }: { fgRef: RefObject<any>; nodes: GraphNode[] }) => {
  const elRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  useEffect(() => {
    const el = elRefs.current;
    let raf = 0;
    const loop = () => {
      const inst = fgRef.current;
      if (inst && inst.graphData && nodesRef.current.length > 0) {
        try {
          const graph = inst.graphData();
          const toScreen = inst.graph2ScreenCoords.bind(inst);
          for (const n of graph.nodes) {
            const nodeEl = el[n.id];
            if (nodeEl && n.x !== undefined && n.y !== undefined && n.z !== undefined) {
              const pt = toScreen(n.x, n.y, n.z);
              nodeEl.style.transform = `translate3d(${pt.x}px, ${pt.y}px, 0) translate(-50%, -230%)`;
            }
          }
        } catch {
          // Camera or graph not ready yet — try again next frame.
        }
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [fgRef]);

  if (nodes.length === 0) return null;

  return (
    <div className="absolute inset-0 top-0 left-0 z-10 pointer-events-none overflow-hidden">
      {nodes.map((n) => (
        <div
          key={n.id}
          ref={(el) => { elRefs.current[n.id] = el; }}
          className="absolute left-0 top-0 px-1.5 py-0.5 rounded border text-[8px] font-mono leading-tight whitespace-nowrap"
          style={{
            background: 'rgba(8,14,27,0.85)',
            borderColor: 'rgba(34,211,238,0.5)',
            color: '#E8EDF5',
            opacity: 0.95,
            textShadow: '0 1px 2px rgba(0,0,0,0.8)',
          }}
        >
          {n.name}
        </div>
      ))}
    </div>
  );
};

// Canvas-based fallback when WebGL crashes — renders the real graph data
interface GraphFallbackProps {
  onNodeSelect?: (node: GraphNode) => void;
  onLinkSelect?: (link: GraphLink) => void;
  isLight: boolean;
  graphData?: {
    nodes: GraphNode[];
    links: GraphLink[];
  };
}

const FALLBACK_NODE_COLORS: Record<string, string> = {
  suspect: '#C94A2A',
  offender: '#D4820A',
  location: '#1E6FD9',
  victim: '#6A7A96',
  case: '#0E9E78',
  gang: '#6C43CC',
  vehicle: '#3D8AF0',
  weapon: '#F09C2E',
  officer: '#14C997',
};

const GraphFallback: React.FC<GraphFallbackProps> = ({ onNodeSelect, onLinkSelect, isLight, graphData }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Deterministic multi-ring layout computed from the actual node list
  const layout = useMemo(() => {
    const nodes = graphData?.nodes ?? [];
    const coords: Record<string, { x: number; y: number }> = {};
    const cx = 400;
    const cy = 250;
    const nodesPerRing = 8;
    nodes.forEach((node, index) => {
      const ring = Math.floor(index / nodesPerRing);
      const posInRing = index % nodesPerRing;
      const ringSize = Math.min(nodesPerRing, nodes.length - ring * nodesPerRing);
      const radius = 100 + ring * 120;
      const angle = (posInRing / ringSize) * Math.PI * 2 - Math.PI / 2;
      coords[node.id] = {
        x: cx + radius * Math.cos(angle),
        y: cy + radius * 0.78 * Math.sin(angle),
      };
    });
    return { nodes, links: graphData?.links ?? [], coords };
  }, [graphData]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || layout.nodes.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Render at device pixel ratio for a sharp, HD-quality image
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const LOGICAL_W = 800;
    const LOGICAL_H = 500;
    canvas.width = LOGICAL_W * dpr;
    canvas.height = LOGICAL_H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    let animId: number;

    const { nodes: layoutNodes, links: layoutLinks, coords } = layout;

    const draw = () => {
      ctx.clearRect(0, 0, LOGICAL_W, LOGICAL_H);

      // Draw particle flow animation lines with provenance colors
      layoutLinks.forEach(link => {
        const start = coords[typeof link.source === 'object' ? link.source.id : link.source];
        const end = coords[typeof link.target === 'object' ? link.target.id : link.target];
        if (start && end) {
          ctx.beginPath();
          ctx.moveTo(start.x, start.y);
          ctx.lineTo(end.x, end.y);
          
          if (link.verification_status === 'VERIFIED' || link.provenance === 'DIRECT_DATABASE') {
            ctx.strokeStyle = isLight ? 'rgba(5, 150, 105, 0.9)' : 'rgba(16, 185, 129, 0.9)';
            ctx.lineWidth = 2.8;
            ctx.setLineDash([]);
          } else if (link.verification_status === 'POTENTIAL' || link.provenance === 'ANALYTICAL_INFERENCE') {
            ctx.strokeStyle = isLight ? 'rgba(217, 119, 6, 0.95)' : 'rgba(245, 158, 11, 0.95)';
            ctx.lineWidth = 2.4;
            ctx.setLineDash([5, 4]);
          } else if (link.is_demo_derived || link.provenance === 'DEMO_SEED' || link.provenance === 'MIXED') {
            ctx.strokeStyle = isLight ? 'rgba(124, 58, 237, 0.8)' : 'rgba(168, 85, 247, 0.8)';
            ctx.lineWidth = 2.0;
            ctx.setLineDash([]);
          } else {
            ctx.strokeStyle = isLight ? 'rgba(100, 116, 139, 0.6)' : 'rgba(148, 163, 184, 0.55)';
            ctx.lineWidth = 1.6;
            ctx.setLineDash([]);
          }
          
          ctx.stroke();
          ctx.setLineDash([]);

          // Flow dot tracer
          const time = Date.now() / 1500;
          const ratio = (time) % 1.0;
          const px = start.x + (end.x - start.x) * ratio;
          const py = start.y + (end.y - start.y) * ratio;

          ctx.beginPath();
          ctx.arc(px, py, 2, 0, Math.PI * 2);
          ctx.fillStyle = link.verification_status === 'VERIFIED' ? '#10b981' : '#f59e0b';
          ctx.fill();
        }
      });

      // Draw Nodes
      layoutNodes.forEach((node) => {
        const pt = coords[node.id];
        if (pt) {
          const isHigh = node.category === 'suspect';
          const size = isHigh ? 13 : 9;

          const fill = FALLBACK_NODE_COLORS[node.category] ?? '#6A7A96';

          // Outer pulsing ring on selected
          if (selectedNodeId === node.id) {
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, size + 8, 0, Math.PI*2);
            ctx.strokeStyle = fill + '66';
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }

          // Inner nodes
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, size, 0, Math.PI * 2);
          ctx.fillStyle = fill;
          ctx.fill();

          // Text labels
          ctx.font = '9px monospace';
          ctx.fillStyle = selectedNodeId === node.id ? '#ffffff' : isLight ? '#334155' : '#A8B4CC';
          ctx.fillText(node.name, pt.x - 30, pt.y - size - 4);
        }
      });

      animId = requestAnimationFrame(draw);
    };

    draw();

    // Attach click listener targeting coordinates or links
    const handleCanvasClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      let foundNode: GraphNode | null = null;

      // Match node coordinate radius
      for (const node of layoutNodes) {
        const pt = coords[node.id];
        if (pt) {
          const dist = Math.hypot(clickX - pt.x, clickY - pt.y);
          if (dist <= 20) {
            foundNode = node;
            break;
          }
        }
      }

      if (foundNode) {
        setSelectedNodeId(foundNode.id);
        onNodeSelect?.(foundNode);
        return;
      }

      // Check if click was close to any link line
      if (onLinkSelect) {
        for (const link of layoutLinks) {
          const start = coords[typeof link.source === 'object' ? link.source.id : link.source];
          const end = coords[typeof link.target === 'object' ? link.target.id : link.target];
          if (start && end) {
            // Distance from point to line segment
            const l2 = (end.x - start.x) ** 2 + (end.y - start.y) ** 2;
            if (l2 === 0) continue;
            let t = ((clickX - start.x) * (end.x - start.x) + (clickY - start.y) * (end.y - start.y)) / l2;
            t = Math.max(0, Math.min(1, t));
            const projX = start.x + t * (end.x - start.x);
            const projY = start.y + t * (end.y - start.y);
            const dist = Math.hypot(clickX - projX, clickY - projY);
            if (dist <= 8) {
              onLinkSelect(link);
              break;
            }
          }
        }
      }
    };

    canvas.addEventListener('click', handleCanvasClick);

    return () => {
      cancelAnimationFrame(animId);
      canvas.removeEventListener('click', handleCanvasClick);
    };
  }, [onNodeSelect, onLinkSelect, selectedNodeId, isLight, layout]);

  if (layout.nodes.length === 0) {
    return (
      <div className="absolute inset-0 w-full h-full flex flex-col items-center justify-center bg-[var(--bg-surface)] p-4 text-center gap-2">
        <AlertTriangle className="w-6 h-6 text-[var(--accent-amber)]" />
        <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)]">
          No network records available to visualize
        </span>
        <span className="text-[9px] font-mono text-[var(--text-disabled)]">
          Sync PostgreSQL into Neo4j or add linked FIR/case data first.
        </span>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 w-full h-full flex flex-col justify-between bg-[var(--bg-surface)] p-4 text-center">
      <div className="w-full flex items-center justify-center gap-1.5 p-2 bg-[var(--accent-amber)]/10 border border-[var(--accent-amber)]/30 text-[var(--accent-amber)] text-[9.5px] font-mono rounded">
        <AlertTriangle className="w-3.5 h-3.5 animate-pulse" />
        <span>WEBGL DIRECT X ACCELERATION OFF - RELATIONAL MATRIX SIMULATOR RUNNING</span>
      </div>
      <div className="flex-grow flex items-center justify-center relative overflow-hidden">
        <canvas ref={canvasRef} width={800} height={500} className="w-full h-full object-contain cursor-pointer max-w-[800px] max-h-[500px]" />
      </div>
    </div>
  );
};

// Simple React ErrorBoundary
class ErrorBoundary extends React.Component<{ children: React.ReactNode, fallback: React.ReactNode, onError?: () => void }, { hasError: boolean }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("ThreeJS Network Graph component failed to load:", error, errorInfo);
    if (this.props.onError) this.props.onError();
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export default CriminalGraph3D;
