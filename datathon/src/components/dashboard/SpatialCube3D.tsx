import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { Rotate3d, Compass, BarChart2 } from 'lucide-react';

export const SpatialCube3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredSector, setHoveredSector] = useState<{
    name: string;
    score: number;
    category: string;
    color: string;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 230;

    // Create scene and camera
    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(45, width / height, 1, 100);
    camera.position.set(8, 8, 8);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    // Create a 3D grid helper (acting as the geographical grid)
    const gridHelper = new THREE.GridHelper(6, 12, 0x1E6FD9, 0x111D35);
    gridHelper.position.y = -0.5;
    scene.add(gridHelper);

    // Add 3D compass orientation helpers (North/East indicators)
    const dirX = new THREE.Vector3(1, 0, 0);
    const arrowX = new THREE.ArrowHelper(dirX, new THREE.Vector3(-3.0, -0.5, 3.0), 1, 0x1E6FD9, 0.2, 0.1);
    scene.add(arrowX);

    const dirZ = new THREE.Vector3(0, 0, -1);
    const arrowZ = new THREE.ArrowHelper(dirZ, new THREE.Vector3(-3.0, -0.5, 3.0), 1, 0x0E9E78, 0.2, 0.1);
    scene.add(arrowZ);

    // Add some 3D columns representing spatial crime counts
    const columns: THREE.Mesh[] = [];
    const colData = [
      { x: -1.5, z: -1.5, height: 2.2, color: 0xC94A2A, hexColor: '#C94A2A', name: 'Whitefield Beat Sector', score: 91, category: 'Cyber Extortion' },
      { x: 1.5, z: 1.5, height: 1.4, color: 0xD4820A, hexColor: '#D4820A', name: 'Devaraja Beat Limit', score: 58, category: 'Lock Burglary' },
      { x: -1.5, z: 1.5, height: 1.8, color: 0x6C43CC, hexColor: '#6C43CC', name: 'Indiranagar Sector B', score: 78, category: 'Online Scam' },
      { x: 1.5, z: -1.5, height: 2.5, color: 0xC94A2A, hexColor: '#C94A2A', name: 'Harbor Gate Node A', score: 95, category: 'Contraband Traffic' },
      { x: 0, z: 0, height: 1.2, color: 0x0E9E78, hexColor: '#0E9E78', name: 'Bengaluru Central Admin', score: 32, category: 'Low Threat Activity' }
    ];

    colData.forEach((data) => {
      const geometry = new THREE.BoxGeometry(0.5, data.height, 0.5);
      const material = new THREE.MeshBasicMaterial({
        color: data.color,
        transparent: true,
        opacity: 0.75,
        wireframe: false
      });
      const mesh = new THREE.Mesh(geometry, material);
      
      // Position column on the grid
      mesh.position.set(data.x, data.height / 2 - 0.5, data.z);
      mesh.userData = {
        name: data.name,
        score: data.score,
        category: data.category,
        hexColor: data.hexColor
      };

      scene.add(mesh);
      columns.push(mesh);

      // Add a wireframe outline for tactical styling
      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 1 });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
      wireframe.position.copy(mesh.position);
      scene.add(wireframe);
    });

    // Raycaster for hover interactions
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    // Mouse drag interaction state
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let rotationSpeed = 0.005;

    const handleMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      
      // Calculate normalized mouse coords for Raycasting
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(columns);

      if (intersects.length > 0) {
        const hitMesh = intersects[0].object as THREE.Mesh;
        
        // Highlight hovered column, dim others
        columns.forEach(col => {
          (col.material as THREE.MeshBasicMaterial).opacity = 0.45;
        });
        (hitMesh.material as THREE.MeshBasicMaterial).opacity = 0.95;

        const data = hitMesh.userData;
        setHoveredSector({
          name: data.name,
          score: data.score,
          category: data.category,
          color: data.hexColor,
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      } else {
        // Reset opacities if not hovering columns
        columns.forEach(col => {
          (col.material as THREE.MeshBasicMaterial).opacity = 0.75;
        });
        setHoveredSector(null);
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

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Slow idle spin if the user is not dragging
      if (!isDragging && hoveredSector === null) {
        scene.rotation.y += 0.004;
      }

      renderer.render(scene, camera);
    };
    animate();

    // Handle container resize
    const handleResize = () => {
      if (!containerRef.current) return;
      const newWidth = containerRef.current.clientWidth;
      camera.aspect = newWidth / height;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, height);
    };
    window.addEventListener('resize', handleResize);

    // Cleanup WebGL resources
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
    <div className="w-full h-full bg-[#0a1220]/80 border border-white/5 p-4 rounded-lg flex flex-col justify-between select-none font-mono relative group overflow-hidden">
      
      {/* Title */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h4 className="text-[11.5px] font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Rotate3d className="w-4 h-4 text-[#1E6FD9] animate-pulse" />
            3D Spatial Density Cube
          </h4>
          <span className="text-[9px] text-[#A8B4CC] uppercase font-semibold">Hover to Query Beat Pillars • Drag to Rotate</span>
        </div>
      </div>

      {/* WebGL Canvas target & Tooltip */}
      <div className="w-full relative flex justify-center items-center cursor-grab active:cursor-grabbing" style={{ height: '220px' }}>
        <div ref={containerRef} className="w-full h-full" />

        {/* 3D HUD Tooltip overlay */}
        {hoveredSector ? (
          <div 
            className="absolute z-20 p-3 bg-black/95 border rounded shadow-2xl flex flex-col gap-1 w-52 pointer-events-none transition-all duration-150 animate-[fadeIn_0.15s_ease-out]"
            style={{ 
              borderColor: hoveredSector.color,
              left: `${Math.min(hoveredSector.x + 15, containerRef.current ? containerRef.current.clientWidth - 220 : 100)}px`,
              top: `${Math.min(hoveredSector.y - 10, 120)}px`
            }}
          >
            <div className="flex items-center justify-between pb-1 border-b border-white/5">
              <span className="text-[9.5px] text-white font-extrabold uppercase truncate">{hoveredSector.name}</span>
            </div>
            <div className="flex justify-between items-center mt-1">
              <span className="text-[8px] text-slate-400">THREAT INDEX:</span>
              <span className="text-[11px] font-bold" style={{ color: hoveredSector.color }}>{hoveredSector.score}%</span>
            </div>
            <div className="flex justify-between items-center mt-0.5">
              <span className="text-[8px] text-slate-400">DOMINANT CRIME:</span>
              <span className="text-[8.5px] text-white font-semibold truncate max-w-[110px]">{hoveredSector.category}</span>
            </div>
          </div>
        ) : (
          <div className="absolute top-2 right-2 bg-slate-950/60 border border-white/5 p-2 rounded text-[8px] text-[#A8B4CC] flex flex-col gap-1 select-none pointer-events-none">
            <span className="flex items-center gap-1 font-bold text-white uppercase"><BarChart2 className="w-3 h-3 text-[#1e6fd9]" /> HUD Legend</span>
            <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#C94A2A]" /> HIGH (&gt;85%)</div>
            <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#D4820A]" /> MEDIUM (50-85%)</div>
            <div className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#0E9E78]" /> LOW (&lt;50%)</div>
          </div>
        )}
      </div>

      {/* Visual orientation metrics inside dashboard box */}
      <div className="flex justify-between text-[9px] text-[#E8EDF5] font-bold uppercase tracking-widest pt-2 border-t border-slate-900 select-none">
        <span className="flex items-center gap-1">
          <Compass className="w-3.5 h-3.5 text-[#0e9e78]" />
          Grid Orientations (X: East, Z: North)
        </span>
        <span>XGBoost Fit Matrix</span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default SpatialCube3D;
