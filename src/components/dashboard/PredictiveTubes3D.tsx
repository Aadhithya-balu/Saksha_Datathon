import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { ShieldAlert } from 'lucide-react';

interface ThreatSector {
  name: string;
  score: number;
  level: string;
  color: number;
  textCol: string;
}

const SECTORS_DATA: ThreatSector[] = [
  { name: '1. Whitefield', score: 91, level: 'Very High', color: 0xC94A2A, textCol: 'text-[#C94A2A]' },
  { name: '2. KR Puram', score: 78, level: 'High', color: 0xD4820A, textCol: 'text-[#D4820A]' },
  { name: '3. Yeshwanthpur', score: 72, level: 'High', color: 0xD4820A, textCol: 'text-[#D4820A]' },
  { name: '4. MG Road', score: 65, level: 'Medium', color: 0x1E6FD9, textCol: 'text-blue-400' }
];

export const PredictiveTubes3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeItem, setActiveItem] = useState<ThreatSector>(SECTORS_DATA[0]);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 160;

    // Scene and camera
    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 100);
    camera.position.set(0, 3.5, 7.5);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    // Grid Floor representation
    const grid = new THREE.GridHelper(5, 10, 0x1E6FD9, 0x111D35);
    grid.position.y = 0;
    scene.add(grid);

    // Render 4 cylindrical tubes representing risk levels
    const tubes: THREE.Mesh[] = [];
    const outlines: THREE.LineSegments[] = [];

    const spacingX = [-1.8, -0.6, 0.6, 1.8];

    SECTORS_DATA.forEach((data, index) => {
      // Cylinder height corresponds to risk score scale
      const cylHeight = (data.score / 100) * 2.2;
      const geometry = new THREE.CylinderGeometry(0.22, 0.22, cylHeight, 16);
      
      const material = new THREE.MeshBasicMaterial({
        color: data.color,
        transparent: true,
        opacity: 0.65
      });
      
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(spacingX[index], cylHeight / 2, 0);
      scene.add(mesh);
      tubes.push(mesh);

      // Hologram wireframe outlining
      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.5 });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
      wireframe.position.copy(mesh.position);
      scene.add(wireframe);
      outlines.push(wireframe);
    });

    // Lights
    const light = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(light);

    // Orbit speed
    let angle = 0;

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Wobble tubes and rotate scene slightly
      angle += 0.015;
      tubes.forEach((mesh, index) => {
        mesh.position.y = ((SECTORS_DATA[index].score / 100) * 2.2) / 2 + Math.sin(angle + index) * 0.04;
        outlines[index].position.y = mesh.position.y;
        mesh.rotation.y += 0.01;
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

  return (
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none font-mono relative">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4 text-[#C94A2A] animate-pulse" />
            Predictive Risk score (3D Tubes)
          </h4>
          <span className="text-[8px] text-slate-500 uppercase">Interactive WebGL Risk Height Forecaster</span>
        </div>
      </div>

      {/* WebGL 3D Canvas */}
      <div ref={containerRef} className="w-full flex justify-center items-center" style={{ height: '140px' }} />

      {/* Mini details list representing the 3D bars data */}
      <div className="grid grid-cols-4 gap-2 text-[8px] text-center pt-2.5 border-t border-slate-900">
        {SECTORS_DATA.map((item) => (
          <button
            key={item.name}
            onClick={() => setActiveItem(item)}
            className={`p-1 rounded border transition-all cursor-pointer ${
              activeItem.name === item.name
                ? 'bg-white/5 border-white/10 text-white font-bold'
                : 'border-transparent text-slate-500 hover:text-slate-400'
            }`}
          >
            <span className="block truncate">{item.name.split(' ').pop()}</span>
            <span className={`block font-extrabold mt-0.5 ${item.textCol}`}>{item.score}%</span>
          </button>
        ))}
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default PredictiveTubes3D;
