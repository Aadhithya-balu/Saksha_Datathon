import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { LayoutGrid, BarChart2 } from 'lucide-react';

interface PieDataPoint {
  name: string;
  value: number;
  percent: string;
}

const COLORS = ['#1E6FD9', '#C94A2A', '#0E9E78', '#6C43CC', '#D4820A', '#80b3ff'];
const HEX_COLORS = [0x1E6FD9, 0xC94A2A, 0x0E9E78, 0x6C43CC, 0xD4820A, 0x80b3ff];

interface DonutChartProps {
  data?: PieDataPoint[];
}

export const DonutChart: React.FC<DonutChartProps> = ({ data = [] }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredRing, setHoveredRing] = useState<{
    name: string;
    value: number;
    percent: string;
    color: string;
    x: number;
    y: number;
  } | null>(null);

  const totalCrimes = data.reduce((a, b) => a + b.value, 0);

  useEffect(() => {
    if (!containerRef.current || !data.length) return;

    const width = containerRef.current.clientWidth;
    const height = 180;

    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 100);
    camera.position.set(0, 5, 5.5);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    // Dynamic grid floor
    const gridHelper = new THREE.GridHelper(5, 10, 0x1E6FD9, 0x111D35);
    gridHelper.position.y = -0.15;
    scene.add(gridHelper);

    const rings: THREE.Mesh[] = [];

    // Render concentric 3D Toruses
    data.forEach((item, index) => {
      const radius = 1.6 - index * 0.28;
      const numPercent = parseFloat(item.percent) / 100;
      const arcLength = 2.0 * Math.PI * numPercent;

      const geometry = new THREE.TorusGeometry(radius, 0.05, 12, 64, arcLength);
      const material = new THREE.MeshBasicMaterial({
        color: HEX_COLORS[index % HEX_COLORS.length],
        transparent: true,
        opacity: 0.75,
        side: THREE.DoubleSide
      });
      const mesh = new THREE.Mesh(geometry, material);
      
      mesh.rotation.x = -Math.PI / 2;
      mesh.rotation.z = Math.PI / 2;
      mesh.position.set(0, 0, 0);
      
      mesh.userData = {
        name: item.name,
        value: item.value,
        percent: item.percent,
        hexColor: COLORS[index % COLORS.length]
      };

      scene.add(mesh);
      rings.push(mesh);

      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color: HEX_COLORS[index % HEX_COLORS.length], linewidth: 1.5 });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
      wireframe.rotation.copy(mesh.rotation);
      wireframe.position.copy(mesh.position);
      scene.add(wireframe);
    });

    // Raycasting
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    const rotationSpeed = 0.005;

    const handleMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(rings);

      if (intersects.length > 0) {
        const hitMesh = intersects[0].object as THREE.Mesh;
        rings.forEach(ring => {
          (ring.material as THREE.MeshBasicMaterial).opacity = 0.3;
        });
        (hitMesh.material as THREE.MeshBasicMaterial).opacity = 0.95;

        const data = hitMesh.userData;
        setHoveredRing({
          name: data.name,
          value: data.value,
          percent: data.percent,
          color: data.hexColor,
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      } else {
        rings.forEach(ring => {
          (ring.material as THREE.MeshBasicMaterial).opacity = 0.75;
        });
        setHoveredRing(null);
      }

      if (!isDragging) return;

      const deltaMove = {
        x: e.clientX - previousMousePosition.x,
        y: e.clientY - previousMousePosition.y
      };

      scene.rotation.y += deltaMove.x * rotationSpeed;
      scene.rotation.x += deltaMove.y * rotationSpeed;

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseUp = () => {
      isDragging = false;
    };

    const domElement = renderer.domElement;
    domElement.addEventListener('mousedown', handleMouseDown);
    domElement.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      if (!isDragging && hoveredRing === null) {
        scene.rotation.y += 0.003;
      }
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
      domElement.removeEventListener('mousedown', handleMouseDown);
      domElement.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('resize', handleResize);
      if (containerRef.current && domElement.parentNode === containerRef.current) {
        containerRef.current.removeChild(domElement);
      }
      renderer.dispose();
    };
  }, [data, hoveredRing]);

  return (
    <div className="w-full h-[280px] bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none relative font-mono overflow-hidden">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2 select-none">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <LayoutGrid className="w-4 h-4 text-[#1E6FD9] animate-pulse" />
            3D Crime Category Orbits
          </h4>
          <span className="text-[9px] text-[#A8B4CC] uppercase font-semibold">WebGL Radial Tube Distribution Matrix</span>
        </div>
      </div>

      {/* WebGL Canvas & Hover Tooltip */}
      <div className="w-full relative flex justify-center items-center cursor-grab active:cursor-grabbing" style={{ height: '180px' }}>
        {data.length ? (
          <>
            <div ref={containerRef} className="w-full h-full" />
            
            {hoveredRing ? (
              <div 
                className="absolute z-20 p-2.5 bg-black/95 border rounded shadow-2xl flex flex-col gap-1 w-48 pointer-events-none transition-all duration-150 animate-[fadeIn_0.15s_ease-out]"
                style={{ 
                  borderColor: hoveredRing.color,
                  left: `${Math.min(hoveredRing.x + 15, containerRef.current ? containerRef.current.clientWidth - 200 : 100)}px`,
                  top: `${Math.min(hoveredRing.y - 10, 110)}px`
                }}
              >
                <div className="flex items-center justify-between pb-1 border-b border-white/5">
                  <span className="text-[9.5px] text-white font-extrabold uppercase truncate">{hoveredRing.name}</span>
                </div>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-[8px] text-slate-400">TOTAL CASES:</span>
                  <span className="text-[11px] font-bold text-white">{hoveredRing.value.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center mt-0.5">
                  <span className="text-[8px] text-slate-400">SHARE METRIC:</span>
                  <span className="text-[11px] font-bold" style={{ color: hoveredRing.color }}>{hoveredRing.percent}</span>
                </div>
              </div>
            ) : (
              <div className="absolute top-2 right-2 bg-slate-950/60 border border-white/5 p-2 rounded text-[8px] text-[#A8B4CC] flex flex-col gap-1 select-none pointer-events-none max-w-[140px]">
                <span className="flex items-center gap-1 font-bold text-white uppercase"><BarChart2 className="w-3 h-3 text-[#1e6fd9]" /> HUD Orbits</span>
                {data.slice(0, 4).map((item, index) => (
                  <div key={item.name} className="flex items-center gap-1 truncate">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                    <span className="truncate">{item.name}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-[10px] text-[#6A7A96] uppercase tracking-wider border border-dashed border-slate-800 rounded">
            No category rows available
          </div>
        )}
      </div>

      {/* Visual orientation metrics inside dashboard box */}
      <div className="flex justify-between text-[9px] text-[#E8EDF5] font-bold uppercase tracking-widest pt-2 border-t border-slate-900 select-none">
        <span>Drag to rotate Orbits</span>
        <span>Total: {totalCrimes.toLocaleString()} Cases</span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default DonutChart;
