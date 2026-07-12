import React, { useRef, useState, useEffect, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html } from '@react-three/drei';
import * as THREE from 'three';
import { DISTRICT_COORDS } from '../../store/mapStore';

// Map lat/lon to spherical 3D points
const latLonToSpherical = (lat: number, lon: number, radius: number) => {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  const x = -(radius * Math.sin(phi) * Math.sin(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.cos(theta);

  return new THREE.Vector3(x, y, z);
};

// Karnataka Boundary Spline coordinates
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
  { lat: 12.5, lon: 74.8 },
  { lat: 13.5, lon: 74.6 },
  { lat: 14.5, lon: 74.2 },
  { lat: 15.5, lon: 74.0 },
  { lat: 16.0, lon: 74.2 },
  { lat: 16.5, lon: 75.0 },
  { lat: 17.3, lon: 76.0 },
  { lat: 18.0, lon: 77.5 }
];

// Inner component for Globe logic, rotation, and mouse parallax
const GlobeInstance: React.FC = () => {
  const globeRef = useRef<THREE.Group>(null);
  const laserRef = useRef<THREE.Mesh>(null);
  const sat1Ref = useRef<THREE.Mesh>(null);
  const sat2Ref = useRef<THREE.Mesh>(null);
  const hudRing1Ref = useRef<THREE.Group>(null);
  const hudRing2Ref = useRef<THREE.Group>(null);

  const { mouse } = useThree();
  const radius = 2.0;

  // Generate particle positions for the Holographic Shell
  const particlesPos = useMemo(() => {
    const count = 750;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);
    }
    return positions;
  }, [radius]);

  // Orbit rotation + Parallax + Rings + Satellites + Laser translation
  useFrame(({ clock }) => {
    const elapsed = clock.getElapsedTime();
    
    if (globeRef.current) {
      globeRef.current.rotation.y += 0.003;
      globeRef.current.rotation.y += (mouse.x * 0.5 - globeRef.current.rotation.y) * 0.05;
      globeRef.current.rotation.x = (mouse.y * 0.3 - globeRef.current.rotation.x) * 0.05;
    }

    if (laserRef.current) {
      // Moves scanning plane up and down
      laserRef.current.position.y = Math.sin(elapsed * 1.8) * radius;
    }

    if (sat1Ref.current) {
      // Orbit 1: horizontal
      sat1Ref.current.position.x = Math.cos(elapsed * 0.7) * (radius + 0.4);
      sat1Ref.current.position.z = Math.sin(elapsed * 0.7) * (radius + 0.4);
    }

    if (sat2Ref.current) {
      // Orbit 2: vertical tilted
      sat2Ref.current.position.y = Math.cos(elapsed * 1.1 + 0.5) * (radius + 0.5);
      sat2Ref.current.position.z = Math.sin(elapsed * 1.1 + 0.5) * (radius + 0.5);
    }

    if (hudRing1Ref.current) {
      hudRing1Ref.current.rotation.z = elapsed * 0.06;
    }

    if (hudRing2Ref.current) {
      hudRing2Ref.current.rotation.z = -elapsed * 0.09;
    }
  });

  // Calculate boundary coordinates
  const borderPoints = KARNATAKA_BORDER_PTS.map((p) => latLonToSpherical(p.lat, p.lon, radius + 0.02));
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

  // Define city-to-city communication arcs representing intel query sync lines
  const connections = [
    { from: 'Bengaluru Urban', to: 'Kalaburagi', color: '#C94A2A' },
    { from: 'Bengaluru Urban', to: 'Belagavi', color: '#D4820A' },
    { from: 'Bengaluru Urban', to: 'Mangaluru', color: '#1E6FD9' },
    { from: 'Mysuru', to: 'Ballari', color: '#6C43CC' }
  ];

  const connectionArcs = connections.map((conn, idx) => {
    const fromCoords = DISTRICT_COORDS[conn.from as keyof typeof DISTRICT_COORDS];
    const toCoords = DISTRICT_COORDS[conn.to as keyof typeof DISTRICT_COORDS];
    if (!fromCoords || !toCoords) return null;
    
    const p1 = latLonToSpherical(fromCoords.lat, fromCoords.lng, radius);
    const p2 = latLonToSpherical(toCoords.lat, toCoords.lng, radius);
    
    const midPoint = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
    const dist = p1.distanceTo(p2);
    midPoint.normalize().multiplyScalar(radius + dist * 0.45);
    
    const curve = new THREE.QuadraticBezierCurve3(p1, midPoint, p2);
    const points = curve.getPoints(40);
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    
    return { geometry, color: conn.color, key: idx };
  }).filter(Boolean);

  return (
    <group>
      {/* 1. Holographic Particle Shell */}
      <points ref={globeRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[particlesPos, 3]} />
        </bufferGeometry>
        <pointsMaterial 
          color="#1e6fd9" 
          size={0.038} 
          sizeAttenuation 
          transparent 
          opacity={0.65} 
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* 2. Scanning Laser plane */}
      <mesh ref={laserRef} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0, radius + 0.1, 32]} />
        <meshBasicMaterial 
          color="#0E9E78" 
          transparent 
          opacity={0.2} 
          side={THREE.DoubleSide} 
          blending={THREE.AdditiveBlending} 
        />
      </mesh>

      {/* 3. Orbiting Satellite 1 (Red) */}
      <mesh ref={sat1Ref}>
        <octahedronGeometry args={[0.07, 0]} />
        <meshBasicMaterial color="#C94A2A" />
      </mesh>
      {/* Sat 1 Track */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[radius + 0.4, radius + 0.405, 64]} />
        <meshBasicMaterial color="#C94A2A" transparent opacity={0.06} side={THREE.DoubleSide} />
      </mesh>

      {/* 4. Orbiting Satellite 2 (Amber) */}
      <mesh ref={sat2Ref}>
        <octahedronGeometry args={[0.06, 0]} />
        <meshBasicMaterial color="#D4820A" />
      </mesh>
      {/* Sat 2 Track */}
      <mesh rotation={[0, Math.PI / 3, 0]}>
        <ringGeometry args={[radius + 0.5, radius + 0.505, 64]} />
        <meshBasicMaterial color="#D4820A" transparent opacity={0.06} side={THREE.DoubleSide} />
      </mesh>

      {/* 5. Tactical HUD concentric circles */}
      <group ref={hudRing1Ref} rotation={[Math.PI / 2.3, 0, 0]}>
        <mesh>
          <ringGeometry args={[radius + 0.75, radius + 0.76, 64]} />
          <meshBasicMaterial color="#1E6FD9" transparent opacity={0.2} side={THREE.DoubleSide} />
        </mesh>
      </group>
      <group ref={hudRing2Ref} rotation={[Math.PI / 2.3, 0, 0]}>
        <mesh>
          <ringGeometry args={[radius + 0.85, radius + 0.854, 64]} />
          <meshBasicMaterial color="#0E9E78" transparent opacity={0.12} side={THREE.DoubleSide} />
        </mesh>
      </group>

      {/* Karnataka wireframe core sphere */}
      <mesh>
        <sphereGeometry args={[radius - 0.05, 24, 24]} />
        <meshBasicMaterial color="#0d1f3b" transparent opacity={0.15} wireframe />
      </mesh>

      {/* Glowing Karnataka Boundary spline */}
      <line geometry={borderGeometry}>
        <lineBasicMaterial color="#0E9E78" linewidth={3} />
      </line>

      {/* Glowing communication curves */}
      {connectionArcs.map((arc: any) => (
        <line key={arc.key} geometry={arc.geometry}>
          <lineBasicMaterial color={arc.color} transparent opacity={0.7} linewidth={2} />
        </line>
      ))}

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
      <mesh>
        <sphereGeometry args={[0.09, 12, 12]} />
        <meshBasicMaterial color={color} transparent opacity={0.22} />
      </mesh>
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
        <Canvas camera={{ position: [0, 0, 4.3], fov: 60 }}>
          <ambientLight intensity={0.8} />
          <pointLight position={[10, 10, 10]} intensity={1.5} />
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
        <div className="text-[10px] uppercase font-mono tracking-widest text-[#0E9E78]">Holographic Core Active</div>
        <div className="text-[9px] font-mono text-[#6A7A96]">TACTICAL DIGITAL TWIN SIMULATION</div>
      </div>
    </div>
  );
};

// High-fidelity SVG backup
const GlobeFallback: React.FC = () => {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center relative overflow-hidden bg-[#0a1122]">
      <div className="w-80 h-80 rounded-full border border-dashed border-[#1E6FD9]/20 flex items-center justify-center animate-[spin_60s_linear_infinite] relative">
        <div className="absolute inset-0 rounded-full border border-[#0E9E78]/10 animate-[pulse_2.5s_infinite]"></div>
        <div className="absolute w-[160px] h-[160px] top-0 left-0 bg-gradient-to-tr from-transparent to-[#1E6FD9]/10 origin-bottom-right rounded-tl-full"></div>
        <svg viewBox="0 0 100 100" className="w-48 h-48 opacity-60 text-emerald-500 fill-none stroke-current stroke-[0.5]">
          <polygon points="50,15 65,25 72,40 68,55 58,62 55,75 48,85 41,75 35,66 32,54 40,43 38,32 50,15" className="fill-[#1E6FD9]/5" />
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
