import React, { useRef, useState, useEffect } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import * as THREE from 'three';
import { DISTRICT_COORDS } from '../../store/mapStore';

// Map lat/lon to spherical 3D points
const latLonToSpherical = (lat: number, lon: number, radius: number) => {
  // Focus mapping coordinates around India regional center on the globe
  // Karnataka: ~ 15°N, 75°E
  // Convert spherical coordinates
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  const x = -(radius * Math.sin(phi) * Math.sin(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.cos(theta);

  return new THREE.Vector3(x, y, z);
};

// Karnataka Boundary Spline coordinates (approximate boundary outline for visualization)
const KARNATAKA_BORDER_PTS = [
  { lat: 18.0, lon: 77.5 },
  { lat: 17.5, lon: 77.6 },
  { lat: 17.0, lon: 77.2 },
  { lat: 16.5, lon: 77.4 },
  { lat: 16.0, lon: 77.9 },
  { lat: 15.0, lon: 76.8 },
  { lat: 13.8, lon: 77.2 },
  { lat: 13.5, lon: 78.4 },
  { lat: 12.8, lon: 78.6 },
  { lat: 12.5, lon: 77.8 },
  { lat: 12.0, lon: 77.0 },
  { lat: 11.6, lon: 76.5 },
  { lat: 12.2, lon: 75.8 },
  { lat: 12.5, lon: 74.8 }, // Mangaluru
  { lat: 13.5, lon: 74.6 },
  { lat: 14.5, lon: 74.2 },
  { lat: 15.5, lon: 74.0 }, // Goa border
  { lat: 16.0, lon: 74.2 },
  { lat: 16.5, lon: 75.0 },
  { lat: 17.3, lon: 76.0 },
  { lat: 18.0, lon: 77.5 }, // Close loop
];

// Inner component for Globe logic, rotation, and mouse parallax
const GlobeInstance: React.FC = () => {
  const globeRef = useRef<THREE.Group>(null);
  const { mouse } = useThree();
  const radius = 2.0;

  // Orbit rotation + Parallax
  useFrame(() => {
    if (globeRef.current) {
      // Rotation: base rotation + mouse parallax influence
      globeRef.current.rotation.y += 0.003;
      globeRef.current.rotation.y += (mouse.x * 0.5 - globeRef.current.rotation.y) * 0.05;
      globeRef.current.rotation.x = (mouse.y * 0.3 - globeRef.current.rotation.x) * 0.05;
    }
  });

  // Calculate boundary coordinates
  const borderPoints = KARNATAKA_BORDER_PTS.map((p) => latLonToSpherical(p.lat, p.lon, radius + 0.02));
  
  // Custom curve for beautiful lines
  const borderCurve = new THREE.CatmullRomCurve3(borderPoints);
  const borderGeometry = new THREE.BufferGeometry().setFromPoints(borderCurve.getPoints(100));

  // Region hotspots (with crime scores mapping)
  const hotspotsData = Object.entries(DISTRICT_COORDS).map(([name, coords]) => {
    const pos = latLonToSpherical(coords.lat, coords.lng, radius);
    let severity: 'high' | 'medium' | 'low' = 'low';
    if (name === 'Bengaluru Urban' || name === 'Kalaburagi' || name === 'Ballari') {
      severity = 'high';
    } else if (name === 'Mysuru' || name === 'Belagavi' || name === 'Mangaluru' || name === 'Dharwad') {
      severity = 'medium';
    }
    return { name, pos, severity };
  });

  return (
    <group ref={globeRef}>
      {/* Globe base sphere */}
      <mesh>
        <sphereGeometry args={[radius, 32, 32]} />
        <meshBasicMaterial 
          color="#0d1f3b" 
          transparent 
          opacity={0.4} 
          wireframe
        />
      </mesh>
      
      {/* Globe core glow sphere */}
      <mesh>
        <sphereGeometry args={[radius - 0.02, 32, 32]} />
        <meshStandardMaterial 
          color="#060c18" 
          roughness={0.9} 
          metalness={0.2}
          emissive="#1E6FD9"
          emissiveIntensity={0.15}
        />
      </mesh>

      {/* Grid helper */}
      <gridHelper args={[6, 12, '#1E6FD9', '#111D35']} position={[0, -0.05, 0]} rotation={[Math.PI / 2, 0, 0]} />

      {/* Glowing Karnataka Boundary spline */}
      <line geometry={borderGeometry}>
        <lineBasicMaterial color="#0E9E78" linewidth={3} />
      </line>

      {/* Pulsing Hotspot Nodes */}
      {hotspotsData.map((hs, index) => (
        <HotspotNode key={index} position={hs.pos} name={hs.name} severity={hs.severity} />
      ))}
    </group>
  );
};

// Hotspot Node details
interface HotspotNodeProps {
  position: THREE.Vector3;
  name: string;
  severity: 'high' | 'medium' | 'low';
}

const HotspotNode: React.FC<HotspotNodeProps> = ({ position, name, severity }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const color = severity === 'high' ? '#C94A2A' : severity === 'medium' ? '#D4820A' : '#1E6FD9';

  useFrame(({ clock }) => {
    if (meshRef.current) {
      // Pulse scale
      const time = clock.getElapsedTime();
      const scale = 1.0 + Math.sin(time * 6 + position.x) * 0.35;
      meshRef.current.scale.set(scale, scale, scale);
    }
  });

  return (
    <group position={position}>
      <mesh ref={meshRef}>
        <sphereGeometry args={[0.045, 12, 12]} />
        <meshBasicMaterial color={color} />
      </mesh>
      {/* Glow aura */}
      <mesh>
        <sphereGeometry args={[0.09, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.18} />
      </mesh>
      {/* HTML tooltip label */}
      <Html distanceFactor={4} position={[0.07, 0, 0]}>
        <div className="px-2 py-0.5 whitespace-nowrap bg-black/80 border border-white/10 text-[9px] font-mono rounded text-[#A8B4CC]">
          {name}
        </div>
      </Html>
    </group>
  );
};

const GlobeScene: React.FC = () => {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return <GlobeFallback />;
  }

  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing">
      <ErrorBoundary fallback={<GlobeFallback />} onError={() => setHasError(true)}>
        <Canvas camera={{ position: [0, 0, 4.2], fov: 60 }}>
          <ambientLight intensity={0.7} />
          <pointLight position={[10, 10, 10]} intensity={1.5} />
          <directionalLight position={[-10, -10, 5]} intensity={0.5} />
          <GlobeInstance />
          <OrbitControls 
            enableZoom={false} 
            enablePan={false}
            minPolarAngle={Math.PI / 4}
            maxPolarAngle={Math.PI * 3/4}
          />
        </Canvas>
      </ErrorBoundary>
      
      {/* Decorative controls overlay */}
      <div className="absolute bottom-5 left-5 z-20 flex flex-col gap-1 pointer-events-none">
        <div className="text-[10px] uppercase font-mono tracking-widest text-[#0E9E78]">Biometric Core Active</div>
        <div className="text-[9px] font-mono text-[#6A7A96]">ROTATE MOUSE PARALLAX : ENGAGED</div>
      </div>
    </div>
  );
};

// High-fidelity SVG backup to protect loading and webgl errors
const GlobeFallback: React.FC = () => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center relative overflow-hidden bg-[#0a1122]">
      {/* Rotating cyber radar scan */}
      <div className="w-80 h-80 rounded-full border border-dashed border-[#1E6FD9]/20 flex items-center justify-center animate-[spin_60s_linear_infinite] relative">
        <div className="absolute inset-0 rounded-full border border-[#0E9E78]/10 animate-[pulse_2.5s_infinite]"></div>
        
        {/* Radar arm sweep */}
        <div className="absolute w-[160px] h-[160px] top-0 left-0 bg-gradient-to-tr from-transparent to-[#1E6FD9]/10 origin-bottom-right rounded-tl-full"></div>
        
        {/* Mock Karnataka map vector */}
        <svg viewBox="0 0 100 100" className="w-48 h-48 opacity-60 text-emerald-500 fill-none stroke-current stroke-[0.5] [stroke-dasharray:1000] [stroke-dashoffset:0] animate-[pulse_3s_infinite]">
          {/* Stylized polygon outline representing Karnataka */}
          <polygon points="50,15 65,25 72,40 68,55 58,62 55,75 48,85 41,75 35,66 32,54 40,43 38,32 50,15" className="fill-[#1E6FD9]/5" />
          
          {/* Mini pulsing locations inside SVG */}
          <circle cx="50" cy="45" r="1.5" className="fill-red-500 animate-ping" />
          <circle cx="48" cy="80" r="1.2" className="fill-orange-400" />
          <circle cx="68" cy="50" r="1.2" className="fill-teal-400" />
        </svg>
      </div>
      
      <div className="text-center mt-6">
        <h4 className="text-[12px] font-mono uppercase tracking-[0.2em] text-[#1E6FD9]">Digital Twin Core Matrix</h4>
        <p className="text-[10px] font-mono text-[#6A7A96] mt-1">SIMULATION MODE ACTIVE</p>
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
    console.error("Three.js Canvas failed to load:", error, errorInfo);
    if (this.props.onError) this.props.onError();
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export default GlobeScene;
export { GlobeFallback };
