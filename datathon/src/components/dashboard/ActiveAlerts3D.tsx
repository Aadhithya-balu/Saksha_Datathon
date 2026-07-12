import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { AlertCircle, HelpCircle } from 'lucide-react';

interface ActiveAlerts3DProps {
  alertRows: any[];
  anomalies: any[];
}

export const ActiveAlerts3D: React.FC<ActiveAlerts3DProps> = ({ alertRows = [], anomalies = [] }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoveredAlert, setHoveredAlert] = useState<{
    label: string;
    score: number;
    color: string;
    x: number;
    y: number;
  } | null>(null);

  // Combine and format alerts into a readable list
  const unifiedAlerts = React.useMemo(() => {
    const list: any[] = [];
    
    // Add hotspots alerts
    alertRows.forEach((r) => {
      let shortName = r.name;
      if (r.name.includes('Market')) shortName = 'Devaraja';
      list.push({
        label: `${r.name} - ${r.category}`,
        shortLabel: shortName,
        score: r.score
      });
    });

    // Add anomalies alerts
    anomalies.forEach((a) => {
      let shortName = 'Anomaly';
      if (a.label && a.label.includes('logins')) shortName = 'Multi Login';
      else if (a.reason && a.reason.includes('logins')) shortName = 'Multi Login';
      else if (a.reason && a.reason.includes('dossiers')) shortName = 'Bulk Export';
      else if (a.label && a.label.includes('dossiers')) shortName = 'Bulk Export';
      
      list.push({
        label: a.label || a.reason || 'System Anomaly',
        shortLabel: shortName,
        score: Math.round(a.score * 100)
      });
    });

    return list.slice(0, 5); // limit to 5 alerts as shown in the original list
  }, [alertRows, anomalies]);

  useEffect(() => {
    if (!containerRef.current || !unifiedAlerts.length) return;

    const width = containerRef.current.clientWidth || 360;
    const height = 180;

    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 100);
    camera.position.set(0, 3.2, 5.2);
    camera.lookAt(0, 0.4, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);

    // Floor Grid
    const gridHelper = new THREE.GridHelper(5, 10, 0x1E6FD9, 0x111D35);
    gridHelper.position.y = -0.5;
    scene.add(gridHelper);

    const bars: THREE.Mesh[] = [];

    // Map unified alerts to 3D Columns (Bar Chart)
    unifiedAlerts.forEach((alert, index) => {
      // Position them side-by-side along the X-axis from -1.8 to 1.8
      const x = -1.8 + (index * 3.6) / 4;
      const z = 0;
      const barHeight = (alert.score / 100) * 1.6; // normalized scale height

      // Color coding based on severity score
      let color = 0x1E6FD9; // Low (Blue)
      let hexColor = '#1E6FD9';
      if (alert.score >= 90) {
        color = 0xC94A2A; // Critical (Red)
        hexColor = '#C94A2A';
      } else if (alert.score >= 75) {
        color = 0xD4820A; // Warning (Amber)
        hexColor = '#D4820A';
      }

      const geometry = new THREE.BoxGeometry(0.42, barHeight, 0.42);
      const material = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.75
      });
      const mesh = new THREE.Mesh(geometry, material);
      
      // Position column base on grid helper
      mesh.position.set(x, barHeight / 2 - 0.5, z);
      mesh.userData = {
        label: alert.label,
        score: alert.score,
        hexColor
      };

      scene.add(mesh);
      bars.push(mesh);

      // Wireframe outlines matching column color
      const geoOutline = new THREE.EdgesGeometry(geometry);
      const matOutline = new THREE.LineBasicMaterial({ color, linewidth: 1.5 });
      const wireframe = new THREE.LineSegments(geoOutline, matOutline);
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
      const intersects = raycaster.intersectObjects(bars);

      if (intersects.length > 0) {
        const hitMesh = intersects[0].object as THREE.Mesh;
        bars.forEach(b => {
          (b.material as THREE.MeshBasicMaterial).opacity = 0.35;
        });
        (hitMesh.material as THREE.MeshBasicMaterial).opacity = 0.95;

        const data = hitMesh.userData;
        setHoveredAlert({
          label: data.label,
          score: data.score,
          color: data.hexColor,
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      } else {
        bars.forEach(b => {
          (b.material as THREE.MeshBasicMaterial).opacity = 0.75;
        });
        setHoveredAlert(null);
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
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      if (!isDragging && hoveredAlert === null) {
        // Slow idle oscillation swing
        scene.rotation.y = Math.sin(clock.getElapsedTime() * 0.1) * 0.25;
      }
      renderer.render(scene, camera);
    };
    
    const clock = new THREE.Clock();
    animate();

    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const newWidth = entry.contentRect.width || containerRef.current?.clientWidth || 360;
        camera.aspect = newWidth / height;
        camera.updateProjectionMatrix();
        renderer.setSize(newWidth, height);
      }
    });
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      cancelAnimationFrame(animationFrameId);
      domElement.removeEventListener('mousedown', handleMouseDown);
      domElement.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      resizeObserver.disconnect();
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
  }, [unifiedAlerts]);

  return (
    <div className="w-full relative flex flex-col justify-between" style={{ height: '220px' }}>
      
      {/* 3D WebGL Canvas Area */}
      <div className="w-full relative flex justify-center items-center cursor-grab active:cursor-grabbing flex-grow" style={{ height: '170px' }}>
        {unifiedAlerts.length ? (
          <>
            <div ref={containerRef} className="w-full h-full" />

            {/* Direct Label Overlays (Highly Visible & Understandable) */}
            <div className="absolute inset-0 pointer-events-none select-none z-10 flex justify-between px-6 pt-8 font-mono text-[9px] font-bold">
              {unifiedAlerts.map((alert, index) => {
                let colorClass = 'text-sky-400';
                if (alert.score >= 90) colorClass = 'text-red-500 text-glow-coral';
                else if (alert.score >= 75) colorClass = 'text-amber-500';

                return (
                  <div key={index} className="flex flex-col items-center justify-between h-full" style={{ width: '18%' }}>
                    {/* Score at the top of the bar */}
                    <span className={`${colorClass} text-[10.5px]`}>{alert.score}%</span>
                    
                    {/* Sector name at the bottom of the bar */}
                    <span className="text-[#E8EDF5] uppercase tracking-wider text-[8.5px] mt-12 block text-center truncate w-full">
                      {alert.shortLabel}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Hover Tooltip details */}
            {hoveredAlert && (
              <div 
                className="absolute z-20 p-2.5 bg-black/95 border rounded shadow-2xl flex flex-col gap-0.5 w-44 pointer-events-none transition-all duration-150 animate-[fadeIn_0.15s_ease-out]"
                style={{ 
                  borderColor: hoveredAlert.color,
                  left: `${Math.min(hoveredAlert.x + 10, containerRef.current ? containerRef.current.clientWidth - 190 : 100)}px`,
                  top: `${Math.min(hoveredAlert.y - 10, 80)}px`
                }}
              >
                <span className="text-[9.5px] text-white font-extrabold uppercase leading-snug tracking-wide truncate max-w-[150px]">{hoveredAlert.label}</span>
                <div className="flex justify-between items-center mt-1 border-t border-white/5 pt-1">
                  <span className="text-[7.5px] text-slate-400">THREAT SCORE:</span>
                  <span className="text-[10.5px] font-bold" style={{ color: hoveredAlert.color }}>{hoveredAlert.score}%</span>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="p-4 text-center text-xs text-[#6A7A96] uppercase font-semibold">
            No Pending Active Alerts
          </div>
        )}
      </div>

      {/* Guide Legend bottom bar */}
      <div className="flex justify-between text-[8px] text-[#A8B4CC] font-bold uppercase tracking-widest pt-2 border-t border-slate-900 select-none px-1">
        <span className="flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5 text-[#C94A2A]" />
          Drag to rotate chart • Hover for full labels
        </span>
        <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#C94A2A]" /> HIGH (&gt;90%)</span>
        <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#D4820A]" /> MED</span>
        <span className="flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-[#1E6FD9]" /> LOW</span>
      </div>
    </div>
  );
};
