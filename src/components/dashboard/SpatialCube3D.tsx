import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';
import { Rotate3d, Compass } from 'lucide-react';

export const SpatialCube3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = 230;

    // Create scene and camera
    const scene = new THREE.Scene();
    scene.background = null; // transparent background to blend with card

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

    // Add some 3D columns representing spatial crime counts
    const columns: THREE.Mesh[] = [];
    const colData = [
      { x: -1.5, z: -1.5, height: 2.2, color: 0xC94A2A }, // High risk (red)
      { x: 1.5, z: 1.5, height: 1.4, color: 0xD4820A },  // Medium risk (amber)
      { x: -1.5, z: 1.5, height: 1.8, color: 0x6C43CC },  // Cyber peak (purple)
      { x: 1.5, z: -1.5, height: 2.5, color: 0xC94A2A },  // Critical peak (red)
      { x: 0, z: 0, height: 1.2, color: 0x0E9E78 }       // Low risk (green)
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
      scene.add(mesh);
      columns.push(mesh);

      // Add a wireframe outline for tactical styling
      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 1 });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
      wireframe.position.copy(mesh.position);
      scene.add(wireframe);
    });

    // Add subtle ambient lights
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5, 10, 7);
    scene.add(light);

    // Mouse drag interaction state
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let rotationSpeed = 0.005;

    const handleMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
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
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      // Slow idle spin if the user is not dragging
      if (!isDragging) {
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
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      window.removeEventListener('resize', handleResize);
      if (containerRef.current) {
        containerRef.current.removeChild(domElement);
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
            <Rotate3d className="w-4 h-4 text-[#1E6FD9] animate-pulse" />
            3D Spatial Density Cube
          </h4>
          <span className="text-[8px] text-slate-500 uppercase">Drag to Rotate Spatial Crime Columns</span>
        </div>
      </div>

      {/* WebGL Canvas target */}
      <div ref={containerRef} className="w-full flex justify-center items-center cursor-grab active:cursor-grabbing" style={{ height: '220px' }} />

      {/* Visual orientation metrics inside dashboard box */}
      <div className="flex justify-between text-[8px] text-slate-500 uppercase tracking-widest pt-2 border-t border-slate-900">
        <span className="flex items-center gap-1">
          <Compass className="w-3 h-3 text-[#0e9e78]" />
          Lat / Lon Projections
        </span>
        <span>XGBoost Grid Fit</span>
      </div>

      <div className="absolute inset-0 chart-diagonal-grid opacity-5 pointer-events-none -z-10" />
    </div>
  );
};

export default SpatialCube3D;
