import React, { useState, useRef, useEffect, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import { Search, RotateCcw, AlertTriangle } from 'lucide-react';
import type { NetworkNodeCategory } from '../../services/api';
import { useAppStore } from '../../store/appStore';

export interface GraphNode {
  id: string;
  name: string;
  category: NetworkNodeCategory;
  riskScore: number;
  details: string;
  casesCount: number;
  phone?: string;
  /** True when the record originates from the bundled demo seed dataset (gap 132.4). */
  isSeed?: boolean;
  /** Spatial coordinates assigned by the force-graph simulation at render time. */
  x?: number;
  y?: number;
  z?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  relationship: string;
}

const EMPTY_GRAPH_DATA: { nodes: GraphNode[]; links: GraphLink[] } = { nodes: [], links: [] };

interface CriminalGraph3DProps {
  onNodeSelect?: (node: GraphNode) => void;
  graphData?: {
    nodes: GraphNode[];
    links: GraphLink[];
  };
}

export const CriminalGraph3D: React.FC<CriminalGraph3DProps> = ({ onNodeSelect, graphData }) => {
  const fgRef = useRef<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const resolvedGraphData = useMemo(() => graphData ?? EMPTY_GRAPH_DATA, [graphData]);
  const [currentGraphData, setCurrentGraphData] = useState(resolvedGraphData);
  const [hasError, setHasError] = useState(false);
  const theme = useAppStore((s) => s.theme);
  const isLight = theme === 'light';
  const canvasBg = isLight ? '#f7f9fc' : '#080E1B';
  const linkColor = isLight ? 'rgba(15, 42, 92, 0.28)' : 'rgba(255, 255, 255, 0.12)';

  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

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
  }, [resolvedGraphData]);

  // Filter nodes matching search criteria
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setCurrentGraphData(resolvedGraphData);
      return;
    }

    const matchedNode = currentGraphData.nodes.find((node) =>
      node.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (matchedNode) {
      // Highlight coordinates by focusing camera on the node in 3D
      if (fgRef.current && !hasError) {
        const distance = 80;
        if (fgRef.current.cameraPosition) {
          fgRef.current.cameraPosition(
            { x: matchedNode.x || 0, y: (matchedNode.y || 0) + 15, z: (matchedNode.z || 0) + distance },
            matchedNode,
            1500
          );
        }
      }
      onNodeSelect?.(matchedNode);
    }
  };

  // Node Clicked Action
  const handleNodeClick = (node: any) => {
    // Zoom camera on node click with spring bounce feel
    if (fgRef.current && fgRef.current.cameraPosition) {
      fgRef.current.cameraPosition(
        { x: node.x * 1.5, y: node.y * 1.5, z: node.z * 1.5 + 60 }, // Move camera closer
        node, // Look at node
        1200 // Transition ms
      );
    }
    const fullNode = currentGraphData.nodes.find(n => n.id === node.id);
    if (fullNode) {
      onNodeSelect?.(fullNode);
    }
  };

  // Color matching
  const getNodeColor = (cat: string) => {
    switch (cat) {
      case 'suspect': return '#C94A2A'; // Red
      case 'offender': return '#D4820A'; // Amber
      case 'location': return '#1E6FD9'; // Blue
      default: return '#6A7A96'; // Victim (Grey)
    }
  };

  // Slow orbital rotation when idle
  useEffect(() => {
    if (fgRef.current && !hasError) {
      fgRef.current.controls().autoRotate = true;
      fgRef.current.controls().autoRotateSpeed = 0.65;
    }
  }, [hasError]);

  return (
    <div className="w-full h-full min-h-[300px] relative bg-[var(--bg-surface)] rounded-card border border-border-color flex flex-col justify-between overflow-hidden">
      
      {/* SEARCH HEADER BAR */}
      <div className="absolute top-4 left-4 z-20 flex gap-2 w-full max-w-sm pointer-events-auto">
        <form onSubmit={handleSearch} className="flex-grow flex items-center relative">
          <input
            type="text"
            placeholder="Search suspect name (e.g. Ramu)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-secondary-bg/90 backdrop-blur-sm text-[var(--text-primary)] font-mono text-xs border border-border-color focus:border-[var(--accent-blue)] rounded-btn outline-none transition-colors"
          />
          <Search className="absolute left-3 w-4 h-4 text-[var(--text-secondary)]" />
        </form>
        
        <button
          type="button"
          onClick={() => {
            setSearchQuery('');
              setCurrentGraphData(resolvedGraphData);
            if (fgRef.current) fgRef.current.zoomToFit(1000);
          }}
          className="px-3 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/15 border border-border-color hover:border-[var(--accent-blue)]/30 rounded text-xs text-[var(--text-secondary)] cursor-pointer"
        >
          Reset
        </button>
      </div>

      {/* GRAPH VIEWPORT */}
      <div ref={containerRef} className="flex-1 w-full h-full relative min-h-[300px]">
        {hasError ? (
          <GraphFallback onNodeSelect={onNodeSelect} isLight={isLight} graphData={currentGraphData} />
        ) : (
          <ErrorBoundary fallback={<GraphFallback onNodeSelect={onNodeSelect} isLight={isLight} graphData={currentGraphData} />} onError={() => setHasError(true)}>
            <ForceGraph3D
              ref={fgRef}
              graphData={currentGraphData}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor={canvasBg}
              showNavInfo={false}
              nodeLabel="name"
              nodeColor={node => getNodeColor(node.category)}
              nodeVal={node => node.category === 'suspect' ? 9 : 6}
              nodeResolution={16}
              linkColor={() => linkColor}
              linkDirectionalParticles={1.5}
              linkDirectionalParticleSpeed={0.012}
              linkDirectionalParticleWidth={2}
              linkWidth={0.8}
              rendererConfig={{ antialias: true }}
              onNodeClick={handleNodeClick}
            />
          </ErrorBoundary>
        )}

        {/* Legend overlays */}
        <div className="absolute bottom-4 left-4 z-20 bg-secondary-bg/90 backdrop-blur-sm p-3.5 border border-border-color rounded-card font-mono text-[9px] flex flex-col gap-2 select-none pointer-events-none">
          <span className="text-[8px] font-bold text-[var(--text-muted)] uppercase tracking-wider">
            Clearance Categories
          </span>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-coral)] shadow-glow-coral" />
            <span className="text-[var(--text-primary)] uppercase">HIGH RISK SUSPECTS</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-amber)] shadow-glow-amber" />
            <span className="text-[var(--text-primary)]">KNOWN OFFENDERS</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-blue)] shadow-glow-blue" />
            <span className="text-[var(--text-primary)]">LOCATION COORDS</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--text-muted)]" />
            <span className="text-[var(--text-primary)]">VICTIMS/COMPLAINANTS</span>
          </div>
        </div>

        {/* Floating Zoom / Rotation HUD */}
        <div className="absolute bottom-4 right-4 z-20 flex flex-col gap-1.5 pointer-events-auto">
          <button
            onClick={() => fgRef.current?.zoomToFit(1200)}
            className="p-2 bg-[var(--bg-tertiary)] hover:bg-[var(--accent-blue)]/15 border border-border-color hover:border-[var(--accent-blue)]/30 rounded text-[var(--text-secondary)] cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
};

// Canvas-based fallback when WebGL crashes — renders the real graph data
interface GraphFallbackProps {
  onNodeSelect?: (node: GraphNode) => void;
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

const GraphFallback: React.FC<GraphFallbackProps> = ({ onNodeSelect, isLight, graphData }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Deterministic circular layout computed from the actual node list
  const layout = useMemo(() => {
    const nodes = graphData?.nodes ?? [];
    const coords: Record<string, { x: number; y: number }> = {};
    const cx = 400;
    const cy = 250;
    nodes.forEach((node, index) => {
      const angle = (index / Math.max(nodes.length, 1)) * Math.PI * 2;
      const radius = nodes.length <= 3 ? 90 : 185;
      coords[node.id] = { x: cx + radius * Math.cos(angle), y: cy + radius * 0.72 * Math.sin(angle) };
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

      // Draw particle flow animation lines
      ctx.lineWidth = 1;
      layoutLinks.forEach(link => {
        const start = coords[link.source];
        const end = coords[link.target];
        if (start && end) {
          ctx.beginPath();
          ctx.moveTo(start.x, start.y);
          ctx.lineTo(end.x, end.y);
          ctx.strokeStyle = isLight ? 'rgba(15, 42, 92, 0.18)' : 'rgba(255,255,255,0.06)';
          ctx.stroke();

          // Flow dot tracer
          const time = Date.now() / 1500;
          const ratio = (time) % 1.0;
          const px = start.x + (end.x - start.x) * ratio;
          const py = start.y + (end.y - start.y) * ratio;

          ctx.beginPath();
          ctx.arc(px, py, 2, 0, Math.PI * 2);
          ctx.fillStyle = '#6c43cc';
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

    // Attach click listener targeting coordinates
    const handleCanvasClick = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      let found: GraphNode | null = null;

      // Match coordinate radius
      for (const node of layoutNodes) {
        const pt = coords[node.id];
        if (pt) {
          const dist = Math.hypot(clickX - pt.x, clickY - pt.y);
          if (dist <= 20) {
            found = node;
            break;
          }
        }
      }

      if (found) {
        setSelectedNodeId(found.id);
        onNodeSelect?.(found);
      }
    };

    canvas.addEventListener('click', handleCanvasClick);

    return () => {
      cancelAnimationFrame(animId);
      canvas.removeEventListener('click', handleCanvasClick);
    };
  }, [onNodeSelect, selectedNodeId, isLight, layout]);

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
