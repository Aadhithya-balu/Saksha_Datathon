import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { Flame, Compass, HelpCircle } from 'lucide-react';

interface HeatmapCell {
  day: string;
  hour: string;
  intensity: number;
  cases: number;
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'];

const HEATMAP_DATA: HeatmapCell[] = [];
DAYS.forEach(day => {
  HOURS.forEach(hour => {
    let base = 25;
    if (day === 'Fri' || day === 'Sat') {
      if (hour === '00:00' || hour === '20:00') base = 85;
    } else if (hour === '12:00' || hour === '16:00') {
      base = 60;
    }
    const cases = Math.floor(base + Math.random() * 15);
    HEATMAP_DATA.push({
      day,
      hour,
      intensity: cases,
      cases
    });
  });
});

export const SpatiotemporalHeatmap: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredCell, setHoveredCell] = useState<{
    day: string;
    hour: string;
    cases: number;
    color: string;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 230;

    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 100);
    camera.position.set(7, 7, 7);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    // Create a grid base helper
    const gridHelper = new THREE.GridHelper(6, 12, 0x6C43CC, 0x111D35);
    gridHelper.position.y = -0.5;
    scene.add(gridHelper);

    // Columns list for raycaster
    const columns: THREE.Mesh[] = [];

    // Map cells to 3D columns
    HEATMAP_DATA.forEach((cell) => {
      const dayIndex = DAYS.indexOf(cell.day);
      const hourIndex = HOURS.indexOf(cell.hour);

      // Map dayIndex to x [-2.0, 2.0]
      const x = -2.0 + (dayIndex * 4.0) / (DAYS.length - 1);
      // Map hourIndex to z [-1.5, 1.5]
      const z = -1.5 + (hourIndex * 3.0) / (HOURS.length - 1);

      // Height mapping
      const barHeight = cell.cases / 30;

      // Color mapping
      let color = 0x1E6FD9; // Low (Blue)
      let hexColor = '#1E6FD9';
      if (cell.cases >= 75) {
        color = 0xC94A2A; // High (Red)
        hexColor = '#C94A2A';
      } else if (cell.cases >= 50) {
        color = 0x6C43CC; // Med (Purple)
        hexColor = '#6C43CC';
      }

      const geometry = new THREE.BoxGeometry(0.35, barHeight, 0.35);
      const material = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.7,
        wireframe: false
      });
      const mesh = new THREE.Mesh(geometry, material);
      
      mesh.position.set(x, barHeight / 2 - 0.5, z);
      mesh.userData = {
        day: cell.day,
        hour: cell.hour,
        cases: cell.cases,
        hexColor
      };

      scene.add(mesh);
      columns.push(mesh);

      // Wireframe helper
      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 1 });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
      wireframe.position.copy(mesh.position);
      scene.add(wireframe);
    });

    // Add axes helpers
    const dirX = new THREE.Vector3(1, 0, 0);
    const arrowX = new THREE.ArrowHelper(dirX, new THREE.Vector3(-3.0, -0.5, 2.0), 0.8, 0x6C43CC, 0.2, 0.1);
    scene.add(arrowX);

    const dirZ = new THREE.Vector3(0, 0, -1);
    const arrowZ = new THREE.ArrowHelper(dirZ, new THREE.Vector3(-3.0, -0.5, 2.0), 0.8, 0xC94A2A, 0.2, 0.1);
    scene.add(arrowZ);

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
      const intersects = raycaster.intersectObjects(columns);

      if (intersects.length > 0) {
        const hitMesh = intersects[0].object as THREE.Mesh;
        columns.forEach(col => {
          (col.material as THREE.MeshBasicMaterial).opacity = 0.35;
        });
        (hitMesh.material as THREE.MeshBasicMaterial).opacity = 0.95;

        const data = hitMesh.userData;
        setHoveredCell({
          day: data.day,
          hour: data.hour,
          cases: data.cases,
          color: data.hexColor,
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      } else {
        columns.forEach(col => {
          (col.material as THREE.MeshBasicMaterial).opacity = 0.70;
        });
        setHoveredCell(null);
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
      if (!isDragging && hoveredCell === null) {
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
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach((mat) => mat.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
      if (containerRef.current && domElement.parentNode === containerRef.current) {
        containerRef.current.removeChild(domElement);
      }
      renderer.dispose();
    };
  }, []);

  return (
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none font-mono relative overflow-hidden group">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Flame className="w-4 h-4 text-[#C94A2A] animate-pulse" />
            3D Spatiotemporal Incident Heatmap
          </h4>
          <span className="text-[9px] text-[#A8B4CC] uppercase font-semibold">WebGL 3D Temporal Density Grid • Rotate & Hover</span>
        </div>
      </div>

      {/* WebGL Canvas & Tooltip */}
      <div className="w-full relative flex justify-center items-center cursor-grab active:cursor-grabbing" style={{ height: '220px' }}>
        <div ref={containerRef} className="w-full h-full" />

        {hoveredCell ? (
          <div 
            className="absolute z-20 p-2.5 bg-black/95 border rounded shadow-2xl flex flex-col gap-1 w-48 pointer-events-none transition-all duration-150 animate-[fadeIn_0.15s_ease-out]"
            style={{ 
              borderColor: hoveredCell.color,
              left: `${Math.min(hoveredCell.x + 15, containerRef.current ? containerRef.current.clientWidth - 200 : 100)}px`,
              top: `${Math.min(hoveredCell.y - 10, 120)}px`
            }}
          >
            <div className="flex items-center justify-between pb-1 border-b border-white/5">
              <span className="text-[9.5px] text-white font-extrabold uppercase">{hoveredCell.day} @ {hoveredCell.hour}</span>
            </div>
            <div className="flex justify-between items-center mt-1">
              <span className="text-[8px] text-slate-400">INCIDENT CASES:</span>
              <span className="text-[11px] font-bold text-white">{hoveredCell.cases} Cases</span>
            </div>
            <div className="flex justify-between items-center mt-0.5">
              <span className="text-[8px] text-slate-400">STATUS LEVEL:</span>
              <span className="text-[8px] font-bold uppercase" style={{ color: hoveredCell.color }}>
                {hoveredCell.cases >= 75 ? 'Critical Density' : hoveredCell.cases >= 50 ? 'Elevated Alert' : 'Normal Patrol'}
              </span>
            </div>
          </div>
        ) : (
          <div className="absolute bottom-2 right-2 bg-slate-950/60 border border-white/5 p-2 rounded text-[8px] text-[#A8B4CC] flex flex-col gap-1 select-none pointer-events-none">
            <span className="flex items-center gap-1 font-bold text-white uppercase"><HelpCircle className="w-3 h-3 text-[#C94A2A]" /> Grid Bounds</span>
            <div className="flex items-center gap-1">X-Axis: Days (Mon-Sun)</div>
            <div className="flex items-center gap-1">Z-Axis: Hours (00:00-20:00)</div>
          </div>
        )}
      </div>

      {/* Visual orientation metrics inside dashboard box */}
      <div className="flex justify-between text-[9px] text-[#E8EDF5] font-bold uppercase tracking-widest pt-2 border-t border-slate-900 select-none">
        <span className="flex items-center gap-1">
          <Compass className="w-3.5 h-3.5 text-[#C94A2A]" />
          Grid Orientations (X: Days, Z: Hours)
        </span>
        <span>Spatiotemporal Helix</span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default SpatiotemporalHeatmap;
