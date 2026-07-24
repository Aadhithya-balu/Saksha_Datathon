import React, { useState, useRef, useEffect, useMemo } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import { Search, Eye, ZoomIn, ZoomOut, RotateCcw, AlertTriangle, ShieldCheck } from 'lucide-react';

export interface GraphNode {
  id: string;
  name: string;
  category: 'suspect' | 'offender' | 'location' | 'victim';
  riskScore: number;
  details: string;
  casesCount: number;
  phone?: string;
}

export interface GraphLink {
  source: string;
  target: string;
  relationship: string;
}

const DEFAULT_NODES: GraphNode[] = [
  // Red: high-risk suspects
  { id: 'node-1', name: 'Ramu "Kodaikanal" Swamy', category: 'suspect', riskScore: 92, details: 'Leader of coordinate interstate break-in gang. Suspected in late night residential robberies in Mysuru and Bengaluru.', casesCount: 14, phone: '+91 94420-12891' },
  { id: 'node-2', name: 'Vikram "Vicky" Yadav', category: 'suspect', riskScore: 88, details: 'Underground money mule coordinator. Funnels fraudulent loans through virtual ledger IDs.', casesCount: 8, phone: '+91 98845-09228' },
  { id: 'node-3', name: 'Sayed Ibrahim', category: 'suspect', riskScore: 84, details: 'Logistics provider for narcotics shipments. Connected to Mangaluru Harbor transit lines.', casesCount: 6, phone: '+91 99014-38419' },

  // Amber: known offenders
  { id: 'node-4', name: 'Karthik Gowda', category: 'offender', riskScore: 71, details: 'Prior conviction for property fraud. Intercepted twice during excise checkpoint violations.', casesCount: 4 },
  { id: 'node-5', name: 'Mohsin Pasha', category: 'offender', riskScore: 65, details: 'Known organizer of illegal sand gravel mining syndicates in Ballari.', casesCount: 5 },

  // Blue: locations
  { id: 'node-6', name: 'Indiranagar Sect-B, Bengaluru', category: 'location', riskScore: 75, details: 'Hotspot of recurring app-based extortion campaigns.', casesCount: 22 },
  { id: 'node-7', name: 'Harbor Gate A, Mangaluru', category: 'location', riskScore: 68, details: 'Seizure point of multiple synthetic drug consignments.', casesCount: 11 },
  { id: 'node-8', name: 'Devaraja Police Limit, Mysuru', category: 'location', riskScore: 50, details: 'Historic zone of lock-break burglaries.', casesCount: 9 },

  // Grey: victims
  { id: 'node-9', name: 'K. S. Narayanan', category: 'victim', riskScore: 10, details: 'Complainant in FIR fraud scan. Swindled of 4.5L via biometric face ID bypass.', casesCount: 1 },
  { id: 'node-10', name: 'Dr. Vinay Murthy', category: 'victim', riskScore: 12, details: 'Home burglary witness in Mysuru break-in.', casesCount: 1 }
];

const DEFAULT_LINKS: GraphLink[] = [
  { source: 'node-1', target: 'node-6', relationship: 'Last active cell location' },
  { source: 'node-1', target: 'node-8', relationship: 'Prior home break-in zone' },
  { source: 'node-1', target: 'node-10', relationship: 'Attacked residential yard' },
  { source: 'node-2', target: 'node-6', relationship: 'Launders app funds' },
  { source: 'node-9', target: 'node-6', relationship: 'Victim resided zone' },
  { source: 'node-3', target: 'node-7', relationship: 'Smuggles chemical contraband' },
  { source: 'node-5', target: 'node-7', relationship: 'Connected cargo clearing agent' },
  { source: 'node-4', target: 'node-8', relationship: 'Excise transit route overlap' },
  { source: 'node-1', target: 'node-4', relationship: 'Known accomplice association' },
  { source: 'node-2', target: 'node-9', relationship: 'Targeted in loan extortions' }
];

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
  const resolvedGraphData = useMemo(() => graphData ?? { nodes: DEFAULT_NODES, links: DEFAULT_LINKS }, [graphData]);
  const [currentGraphData, setCurrentGraphData] = useState(resolvedGraphData);
  const [hasError, setHasError] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 600, height: 400 });

  useEffect(() => {
    if (!containerRef.current) return;
    
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
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
        const node3D: any = fgRef.current.scene().getObjectByName(matchedNode.id) || matchedNode;
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
          <GraphFallback onNodeSelect={onNodeSelect} />
        ) : (
          <ErrorBoundary fallback={<GraphFallback onNodeSelect={onNodeSelect} />} onError={() => setHasError(true)}>
            <ForceGraph3D
              ref={fgRef}
              graphData={currentGraphData}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor="#080E1B"
              showNavInfo={false}
              nodeLabel="name"
              nodeColor={node => getNodeColor(node.category)}
              nodeVal={node => node.category === 'suspect' ? 9 : 6}
              nodeResolution={16}
              linkColor={() => 'rgba(255, 255, 255, 0.12)'}
              linkDirectionalParticles={1.5}
              linkDirectionalParticleSpeed={0.012}
              linkDirectionalParticleWidth={2}
              linkWidth={0.8}
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

// Canvas-based fallback when WebGL crashes
interface GraphFallbackProps {
  onNodeSelect?: (node: GraphNode) => void;
}

const GraphFallback: React.FC<GraphFallbackProps> = ({ onNodeSelect }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    
    // Fallback simulated layout points coordinates representing relation matrix
    const scaleX = (val: number) => 80 + val * 6.4;
    const scaleY = (val: number) => 80 + val * 4.4;

    const mockCoords: Record<string, { x: number, y: number }> = {
      'node-1': { x: 300, y: 180 },
      'node-2': { x: 480, y: 170 },
      'node-3': { x: 200, y: 350 },
      'node-4': { x: 370, y: 320 },
      'node-5': { x: 600, y: 250 },
      'node-6': { x: 420, y: 80 },
      'node-7': { x: 150, y: 200 },
      'node-8': { x: 650, y: 380 },
      'node-9': { x: 550, y: 90 },
      'node-10': { x: 300, y: 450 }
    };

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw particle flow animation lines
      ctx.lineWidth = 1;
      DEFAULT_LINKS.forEach(link => {
        const start = mockCoords[link.source];
        const end = mockCoords[link.target];
        if (start && end) {
          ctx.beginPath();
          ctx.moveTo(start.x, start.y);
          ctx.lineTo(end.x, end.y);
          ctx.strokeStyle = 'rgba(255,255,255,0.06)';
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
      DEFAULT_NODES.forEach((node) => {
        const pt = mockCoords[node.id];
        if (pt) {
          const isHigh = node.category === 'suspect';
          const size = isHigh ? 13 : 9;
          
          let fill = '#6A7A96';
          if (node.category === 'suspect') fill = '#C94A2A';
          else if (node.category === 'offender') fill = '#D4820A';
          else if (node.category === 'location') fill = '#1E6FD9';

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
          ctx.fillStyle = selectedNodeId === node.id ? '#ffffff' : '#A8B4CC';
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
      for (const node of DEFAULT_NODES) {
        const pt = mockCoords[node.id];
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
  }, [onNodeSelect, selectedNodeId]);

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
