import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { Sparkles, Rotate3d, HelpCircle } from 'lucide-react';

interface ForecastDataPoint {
  day: string;
  value: number;
  type: 'historical' | 'predicted' | 'today';
  color: number;
  hexColor: string;
}

const FORECAST_SERIES: ForecastDataPoint[] = [
  { day: 'T-10d', value: 145, type: 'historical', color: 0x1E6FD9, hexColor: '#1E6FD9' },
  { day: 'T-8d', value: 152, type: 'historical', color: 0x1E6FD9, hexColor: '#1E6FD9' },
  { day: 'T-6d', value: 148, type: 'historical', color: 0x1E6FD9, hexColor: '#1E6FD9' },
  { day: 'T-4d', value: 160, type: 'historical', color: 0x1E6FD9, hexColor: '#1E6FD9' },
  { day: 'T-2d', value: 172, type: 'historical', color: 0x1E6FD9, hexColor: '#1E6FD9' },
  { day: 'TODAY', value: 185, type: 'today', color: 0x0E9E78, hexColor: '#0E9E78' },
  { day: 'P+2d', value: 191, type: 'predicted', color: 0x0ea5e9, hexColor: '#0ea5e9' },
  { day: 'P+4d', value: 198, type: 'predicted', color: 0x0ea5e9, hexColor: '#0ea5e9' },
  { day: 'P+6d', value: 215, type: 'predicted', color: 0x0ea5e9, hexColor: '#0ea5e9' },
  { day: 'P+8d', value: 202, type: 'predicted', color: 0x0ea5e9, hexColor: '#0ea5e9' },
  { day: 'P+10d', value: 210, type: 'predicted', color: 0x0ea5e9, hexColor: '#0ea5e9' },
  { day: 'P+12d', value: 226, type: 'predicted', color: 0x0ea5e9, hexColor: '#0ea5e9' },
  { day: 'P+14d', value: 238, type: 'predicted', color: 0x0ea5e9, hexColor: '#0ea5e9' }
];

export const ForecastChart: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{
    day: string;
    value: number;
    type: string;
    color: string;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 180;

    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 100);
    camera.position.set(0, 5, 8);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    // Timeline baseline grid
    const gridHelper = new THREE.GridHelper(7, 14, 0x1E6FD9, 0x111D35);
    gridHelper.position.y = -0.5;
    scene.add(gridHelper);

    const columns: THREE.Mesh[] = [];
    const splinePoints: THREE.Vector3[] = [];

    // Map series to 3D Cylinders
    FORECAST_SERIES.forEach((pt, index) => {
      const x = -3.0 + (index * 6.0) / (FORECAST_SERIES.length - 1);
      const z = 0;
      const cylHeight = pt.value / 95; // normalize scale

      const geometry = new THREE.CylinderGeometry(0.12, 0.12, cylHeight, 16);
      const material = new THREE.MeshBasicMaterial({
        color: pt.color,
        transparent: true,
        opacity: pt.type === 'predicted' ? 0.55 : 0.8,
        wireframe: false
      });
      const mesh = new THREE.Mesh(geometry, material);
      
      mesh.position.set(x, cylHeight / 2 - 0.5, z);
      mesh.userData = {
        day: pt.day,
        value: pt.value,
        type: pt.type,
        hexColor: pt.hexColor
      };

      scene.add(mesh);
      columns.push(mesh);

      // Save top points for spline curve
      splinePoints.push(new THREE.Vector3(x, cylHeight - 0.5, z));

      // Outline wireframe
      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 1 });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
      wireframe.position.copy(mesh.position);
      scene.add(wireframe);
    });

    // Add continuous spline curve connecting tops of the cylinders
    const splineCurve = new THREE.CatmullRomCurve3(splinePoints);
    const curvePoints = splineCurve.getPoints(100);
    const curveGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
    const curveMat = new THREE.LineBasicMaterial({
      color: 0x0ea5e9,
      linewidth: 3
    });
    const curveLine = new THREE.Line(curveGeo, curveMat);
    scene.add(curveLine);

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
      const intersects = raycaster.intersectObjects(columns);

      if (intersects.length > 0) {
        const hitMesh = intersects[0].object as THREE.Mesh;
        columns.forEach(col => {
          (col.material as THREE.MeshBasicMaterial).opacity = 0.35;
        });
        (hitMesh.material as THREE.MeshBasicMaterial).opacity = 0.95;

        const data = hitMesh.userData;
        setHoveredPoint({
          day: data.day,
          value: data.value,
          type: data.type,
          color: data.hexColor,
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      } else {
        columns.forEach(col => {
          (col.material as THREE.MeshBasicMaterial).opacity = col.userData.type === 'predicted' ? 0.55 : 0.8;
        });
        setHoveredPoint(null);
      }

      if (!isDragging) return;

      const deltaMove = {
        x: e.clientX - previousMousePosition.x,
        y: e.clientY - previousMousePosition.y
      };

      scene.rotation.y += deltaMove.x * rotationSpeed;
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
    const startTime = performance.now();
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = (performance.now() - startTime) / 1000;
      if (!isDragging && hoveredPoint === null) {
        scene.rotation.y = Math.sin(elapsed * 0.15) * 0.4;
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
    <div className="w-full h-[280px] bg-[#111D35]/30 border border-border-color p-4 rounded-card relative overflow-hidden flex flex-col justify-between font-mono">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2 select-none">
        <div>
          <span className="text-[10px] text-[#D4820A] uppercase font-bold tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-[#D4820A] animate-pulse" />
            3D AI PREDICTIVE TIMELINE
          </span>
          <h4 className="text-[12px] font-bold text-white mt-0.5">30-Day Cylinder Forecast Model</h4>
        </div>
      </div>

      {/* WebGL Canvas & Hover Tooltip */}
      <div className="w-full relative flex justify-center items-center cursor-grab active:cursor-grabbing" style={{ height: '180px' }}>
        <div ref={containerRef} className="w-full h-full" />

        {hoveredPoint ? (
          <div 
            className="absolute z-20 p-2.5 bg-black/95 border rounded shadow-2xl flex flex-col gap-1 w-48 pointer-events-none transition-all duration-150 animate-[fadeIn_0.15s_ease-out]"
            style={{ 
              borderColor: hoveredPoint.color,
              left: `${Math.min(hoveredPoint.x + 15, containerRef.current ? containerRef.current.clientWidth - 200 : 100)}px`,
              top: `${Math.min(hoveredPoint.y - 10, 110)}px`
            }}
          >
            <div className="flex items-center justify-between pb-1 border-b border-white/5">
              <span className="text-[9.5px] text-white font-extrabold uppercase">{hoveredPoint.day}</span>
            </div>
            <div className="flex justify-between items-center mt-1">
              <span className="text-[8px] text-slate-400">DATA VALUE:</span>
              <span className="text-[11px] font-bold text-white">{hoveredPoint.value} Incidents</span>
            </div>
            <div className="flex justify-between items-center mt-0.5">
              <span className="text-[8px] text-slate-400">MODEL TYPE:</span>
              <span className="text-[8px] font-bold uppercase" style={{ color: hoveredPoint.color }}>
                {hoveredPoint.type}
              </span>
            </div>
          </div>
        ) : (
          <div className="absolute top-2 right-2 bg-slate-950/60 border border-white/5 p-2 rounded text-[8px] text-[#A8B4CC] flex flex-col gap-1 select-none pointer-events-none">
            <span className="flex items-center gap-1 font-bold text-white uppercase"><Rotate3d className="w-3 h-3 text-[#D4820A]" /> Timeline Keys</span>
            <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#1E6FD9]" /> HISTORICAL</div>
            <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#0E9E78]" /> TODAY</div>
            <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#0ea5e9]" /> AI PREDICTED</div>
          </div>
        )}
      </div>

      {/* Visual orientation metrics inside dashboard box */}
      <div className="flex justify-between text-[9px] text-[#E8EDF5] font-bold uppercase tracking-widest pt-2 border-t border-slate-900 select-none">
        <span className="flex items-center gap-1">
          <HelpCircle className="w-3.5 h-3.5 text-[#D4820A]" />
          Drag to Pivot Timeline • Left to Right progression
        </span>
        <span>Confidence Interval: 94.6%</span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-10 pointer-events-none -z-10" />
    </div>
  );
};

export default ForecastChart;
