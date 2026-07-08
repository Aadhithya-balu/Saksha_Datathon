import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { AlertTriangle, Clock } from 'lucide-react';

interface ActiveAlert {
  id: string;
  label: string;
  timestamp: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  color: number;
  pos: [number, number, number];
}

const ALERTS_DATA: ActiveAlert[] = [
  { id: 'al-01', label: 'High Theft Risk in Whitefield', timestamp: '2m', severity: 'CRITICAL', color: 0xC94A2A, pos: [-1.4, 0.4, -0.6] },
  { id: 'al-02', label: 'Cyber Fraud Spike Detected', timestamp: '15m', severity: 'WARNING', color: 0xD4820A, pos: [1.2, 0.4, 0.8] },
  { id: 'al-03', label: 'Witness at Risk - Case #CR2456', timestamp: '30m', severity: 'INFO', color: 0x1E6FD9, pos: [-0.3, 0.4, 1.3] }
];

export const AlertRadar3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeAlert, setActiveAlert] = useState<ActiveAlert>(ALERTS_DATA[0]);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 160;

    // Scene and camera
    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 100);
    camera.position.set(0, 4.5, 7.5);
    camera.lookAt(0, 0.2, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    // Radar Concentric rings
    const ringMaterial = new THREE.LineBasicMaterial({ color: 0x1E6FD9, transparent: true, opacity: 0.25 });
    const ringRadii = [1, 2, 3];
    
    ringRadii.forEach(radius => {
      const ringGeom = new THREE.RingGeometry(radius, radius + 0.03, 32);
      const ringMesh = new THREE.Mesh(ringGeom, new THREE.MeshBasicMaterial({ color: 0x1E6FD9, transparent: true, opacity: 0.15, side: THREE.DoubleSide }));
      ringMesh.rotation.x = Math.PI / 2;
      scene.add(ringMesh);
    });

    // Radar Sweep rotating line
    const sweepGeom = new THREE.PlaneGeometry(0.04, 3);
    const sweepMat = new THREE.MeshBasicMaterial({ color: 0x0E9E78, transparent: true, opacity: 0.4, side: THREE.DoubleSide });
    const sweepMesh = new THREE.Mesh(sweepGeom, sweepMat);
    sweepMesh.rotation.x = Math.PI / 2;
    sweepMesh.position.set(0, 0.01, 0);
    scene.add(sweepMesh);

    // Add 3D alert pyramids (cones) representing alert locations
    const alertMeshes: THREE.Mesh[] = [];
    
    ALERTS_DATA.forEach(data => {
      const geometry = new THREE.ConeGeometry(0.24, 0.5, 4); // 4-sided pyramid cone
      const material = new THREE.MeshBasicMaterial({
        color: data.color,
        transparent: true,
        opacity: 0.8
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(data.pos[0], data.pos[1], data.pos[2]);
      scene.add(mesh);
      alertMeshes.push(mesh);

      // Outer outline
      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color: 0xffffff });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
      wireframe.position.copy(mesh.position);
      scene.add(wireframe);
    });

    // Animation Loop
    let angle = 0;
    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Spin radar sweep
      sweepMesh.rotation.z += 0.03;

      // Pulsing blink beacons opacity rate
      angle += 0.08;
      const blinkOpacity = 0.4 + Math.sin(angle) * 0.4;
      
      alertMeshes.forEach((mesh, index) => {
        mesh.rotation.y += 0.02;
        // Blinking severity colors
        const mat = mesh.material as THREE.MeshBasicMaterial;
        mat.opacity = blinkOpacity + 0.2;
      });

      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!containerRef.current) return;
      const newWidth = containerRef.current.clientWidth;
      camera.aspect = newWidth / height;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, height);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      if (containerRef.current && renderer.domElement.parentNode) {
        containerRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  const getSeverityColor = (sev: ActiveAlert['severity']) => {
    switch (sev) {
      case 'CRITICAL': return 'text-red-400 bg-red-950/20 border-red-900/30';
      case 'WARNING': return 'text-amber-400 bg-amber-950/20 border-amber-900/30';
      default: return 'text-blue-400 bg-blue-950/20 border-blue-900/30';
    }
  };

  return (
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none font-mono relative">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-[#D4820A] animate-pulse" />
            Active Alerts (3D Radar)
          </h4>
          <span className="text-[8px] text-slate-500 uppercase">3D Sweep Sonar Mapping Warning Pyramids</span>
        </div>
      </div>

      {/* WebGL 3D Canvas */}
      <div ref={containerRef} className="w-full flex justify-center items-center" style={{ height: '140px' }} />

      {/* Active detail display overlay */}
      <div className="pt-2 border-t border-slate-900 flex flex-col gap-1.5">
        {/* Alerts slider buttons selection */}
        <div className="flex gap-1.5 overflow-x-auto custom-scrollbar select-none text-[8.5px]">
          {ALERTS_DATA.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveAlert(item)}
              className={`px-2.5 py-1 border rounded shrink-0 uppercase tracking-wide cursor-pointer transition-all ${
                activeAlert.id === item.id
                  ? getSeverityColor(item.severity) + ' font-bold border-opacity-70'
                  : 'bg-transparent border-transparent text-slate-500 hover:text-slate-400'
              }`}
            >
              {item.timestamp} • {item.label.split(' ').slice(0, 2).join(' ')}
            </button>
          ))}
        </div>
        
        {/* Selected alert description */}
        <div className="text-[9px] text-[#A8B4CC] flex items-center justify-between border-t border-white/5 pt-1.5 select-none min-h-[16px]">
          <span className="truncate text-white font-bold uppercase">{activeAlert.label}</span>
          <span className="text-slate-500 flex items-center gap-1 shrink-0 ml-2">
            <Clock className="w-3 h-3" />
            {activeAlert.timestamp} ago
          </span>
        </div>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default AlertRadar3D;
