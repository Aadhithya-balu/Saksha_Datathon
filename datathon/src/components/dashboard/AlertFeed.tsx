import React, { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAlertStore } from '../../store/alertStore';
import type { CrimeAlert } from '../../store/alertStore';
import { AlertCircle, Eye, ShieldAlert, CheckCircle, Navigation } from 'lucide-react';
import * as THREE from 'three';

interface AlertFeedProps {
  onAlertClick?: (alert: CrimeAlert) => void;
  limit?: number;
}

export const AlertFeed: React.FC<AlertFeedProps> = ({ onAlertClick, limit = 5 }) => {
  const alerts = useAlertStore((state) => state.alerts);
  const activeAlerts = alerts.slice(0, limit);

  // THREE.JS Radar Ref
  const radarRef = useRef<HTMLDivElement>(null);
  const [hovered3DAlert, setHovered3DAlert] = useState<{
    firNumber: string;
    anomalyScore: number;
    severity: string;
    station: string;
    color: string;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    if (!radarRef.current || !activeAlerts.length) return;

    const width = radarRef.current.clientWidth;
    const height = 150;

    const scene = new THREE.Scene();
    scene.background = null;

    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 100);
    camera.position.set(0, 4.5, 6);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    radarRef.current.appendChild(renderer.domElement);

    // Radar coordinate floor grid
    const gridHelper = new THREE.GridHelper(5, 10, 0x1E6FD9, 0x111D35);
    gridHelper.position.y = -0.5;
    scene.add(gridHelper);

    // Glowing coordinate sweep ring
    const sweepGeo = new THREE.RingGeometry(0, 2.5, 32);
    const sweepMat = new THREE.MeshBasicMaterial({
      color: 0x1E6FD9,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide
    });
    const sweepMesh = new THREE.Mesh(sweepGeo, sweepMat);
    sweepMesh.rotation.x = -Math.PI / 2;
    sweepMesh.position.y = -0.49;
    scene.add(sweepMesh);

    const beacons: THREE.Mesh[] = [];
    const lines: THREE.Line[] = [];

    // Map activeAlerts to 3D points
    activeAlerts.forEach((alert, index) => {
      // Calculate coordinates: circular layout on grid
      const angle = (index * 2.0 * Math.PI) / activeAlerts.length;
      const radius = 1.0 + index * 0.22;
      const altitude = (alert.anomalyScore / 100) * 1.5; // height represents threat score

      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = altitude - 0.5; // position on grid base

      // Severity Color Code
      let color = 0x1E6FD9; // WATCH/LOW (Blue)
      let hexColor = '#1E6FD9';
      if (alert.severity === 'HIGH') {
        color = 0xC94A2A; // CRITICAL (Red)
        hexColor = '#C94A2A';
      } else if (alert.severity === 'WATCH') {
        color = 0xD4820A; // WARNING (Amber)
        hexColor = '#D4820A';
      }

      // 1. Beacon Geometry (Octahedron)
      const geometry = new THREE.OctahedronGeometry(0.1, 0);
      const material = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.8
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(x, y, z);
      mesh.userData = {
        id: alert.id,
        firNumber: alert.firNumber,
        anomalyScore: alert.anomalyScore,
        severity: alert.severity,
        station: alert.station,
        hexColor
      };

      scene.add(mesh);
      beacons.push(mesh);

      // 2. Lock Line (Vertical Laser from node to floor grid)
      const linePoints = [
        new THREE.Vector3(x, -0.5, z),
        new THREE.Vector3(x, y, z)
      ];
      const lineGeo = new THREE.BufferGeometry().setFromPoints(linePoints);
      const lineMat = new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity: 0.4
      });
      const lockLine = new THREE.Line(lineGeo, lineMat);
      scene.add(lockLine);
      lines.push(lockLine);

      // 3. Glowing wireframe mesh
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
      const intersects = raycaster.intersectObjects(beacons);

      if (intersects.length > 0) {
        const hitMesh = intersects[0].object as THREE.Mesh;
        beacons.forEach(b => {
          (b.material as THREE.MeshBasicMaterial).opacity = 0.35;
        });
        (hitMesh.material as THREE.MeshBasicMaterial).opacity = 0.95;

        const data = hitMesh.userData;
        setHovered3DAlert({
          firNumber: data.firNumber,
          anomalyScore: data.anomalyScore,
          severity: data.severity,
          station: data.station,
          color: data.hexColor,
          x: e.clientX - rect.left,
          y: e.clientY - rect.top
        });
      } else {
        beacons.forEach(b => {
          (b.material as THREE.MeshBasicMaterial).opacity = 0.8;
        });
        setHovered3DAlert(null);
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
      if (!isDragging && hovered3DAlert === null) {
        scene.rotation.y += 0.003;
      }
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!radarRef.current) return;
      const newWidth = radarRef.current.clientWidth;
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
      if (radarRef.current && domElement.parentNode === radarRef.current) {
        radarRef.current.removeChild(domElement);
      }
      renderer.dispose();
    };
  }, [activeAlerts, hovered3DAlert]);

  return (
    <div className="flex flex-col gap-3">
      {/* Feed Header */}
      <div className="flex justify-between items-center select-none mb-1">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#C94A2A] animate-ping" />
          <h4 className="text-[11px] font-mono uppercase tracking-widest text-[#E8EDF5] text-glow-coral">
            Critical Anomaly Feed
          </h4>
        </div>
        <span className="px-2 py-0.5 bg-[#C94A2A]/10 text-[#C94A2A] rounded-full text-[9px] font-bold font-mono border border-[#C94A2A]/20">
          {alerts.filter(a => a.status === 'PENDING').length} PENDING UNRESOLVED
        </span>
      </div>

      {/* 3D WEBGL ALERTS RADAR VISUALIZATION */}
      {activeAlerts.length > 0 && (
        <div className="w-full bg-[#0a1220]/80 border border-white/5 p-2.5 rounded-lg flex flex-col justify-between select-none relative font-mono overflow-hidden">
          <span className="text-[8px] text-[#A8B4CC] uppercase font-bold tracking-widest">
            3D Holographic Threat Radar
          </span>
          <div className="w-full relative flex justify-center items-center cursor-grab active:cursor-grabbing" style={{ height: '140px' }}>
            <div ref={radarRef} className="w-full h-full" />
            
            {hovered3DAlert ? (
              <div 
                className="absolute z-20 p-2 bg-black/95 border rounded shadow-2xl flex flex-col gap-0.5 w-40 pointer-events-none transition-all duration-150 animate-[fadeIn_0.15s_ease-out]"
                style={{ 
                  borderColor: hovered3DAlert.color,
                  left: `${Math.min(hovered3DAlert.x + 10, radarRef.current ? radarRef.current.clientWidth - 170 : 100)}px`,
                  top: `${Math.min(hovered3DAlert.y - 10, 80)}px`
                }}
              >
                <span className="text-[9px] text-white font-extrabold truncate">{hovered3DAlert.firNumber}</span>
                <span className="text-[8px] text-slate-400 mt-0.5">{hovered3DAlert.station}</span>
                <div className="flex justify-between items-center mt-1 border-t border-white/5 pt-1">
                  <span className="text-[7.5px] text-slate-400">SCORE:</span>
                  <span className="text-[10px] font-bold" style={{ color: hovered3DAlert.color }}>{hovered3DAlert.anomalyScore}%</span>
                </div>
              </div>
            ) : (
              <div className="absolute top-1.5 right-1.5 bg-slate-950/70 border border-white/5 p-1.5 rounded text-[7.5px] text-[#A8B4CC] flex flex-col gap-0.5 select-none pointer-events-none">
                <div className="flex items-center gap-1 font-bold text-white uppercase">Threat Keys</div>
                <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#C94A2A]" /> HIGH</div>
                <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#D4820A]" /> WATCH</div>
                <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-[#1E6FD9]" /> LOW</div>
              </div>
            )}
          </div>
          <span className="text-[7.5px] text-slate-500 uppercase mt-1 select-none">
            Y-Axis: Threat severity • Rotation represents temporal beat sequence
          </span>
        </div>
      )}

      {/* Cards list */}
      <div className="flex flex-col gap-2.5 overflow-y-auto max-h-[310px] pr-1.5 custom-scrollbar">
        <AnimatePresence initial={false}>
          {activeAlerts.map((alert, index) => {
            const isHigh = alert.severity === 'HIGH';
            const isWatch = alert.severity === 'WATCH';
            
            // Pulsing border styles
            const borderClass = isHigh 
              ? 'border-l-[3.5px] border-l-[#C94A2A] pulse-border-red' 
              : isWatch 
              ? 'border-l-[3.5px] border-l-[#D4820A] pulse-border-amber' 
              : 'border-l-[3.5px] border-l-[#1E6FD9]';

            return (
              <motion.div
                key={alert.id}
                initial={{ x: 120, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: -100, opacity: 0 }}
                transition={{ 
                  type: 'spring', 
                  stiffness: 140, 
                  damping: 15,
                  mass: 0.8,
                  delay: index * 0.05 
                }}
                onClick={() => onAlertClick?.(alert)}
                className={`p-3.5 bg-slate-950/40 border border-border-color hover:border-[#1E6FD9]/30 rounded-card cursor-pointer flex flex-col gap-2 text-left relative overflow-hidden transition-all duration-300 ${borderClass}`}
              >
                {/* Top card row */}
                <div className="flex justify-between items-start">
                  <div className="flex flex-col">
                    <span className="text-[10px] font-mono text-[#E8EDF5] font-bold">
                      {alert.firNumber}
                    </span>
                    <span className="text-[8px] font-mono text-[#6A7A96] uppercase mt-0.5">
                      {alert.station} • {alert.district}
                    </span>
                  </div>

                  <span className={`px-2 py-0.5 rounded text-[8.5px] font-mono font-bold ${
                    isHigh 
                      ? 'bg-[#C94A2A]/10 text-[#C94A2A] border border-[#C94A2A]/20' 
                      : isWatch 
                      ? 'bg-[#D4820A]/10 text-[#D4820A] border border-[#D4820A]/20' 
                      : 'bg-[#1E6FD9]/10 text-[#1E6FD9] border border-[#1E6FD9]/20'
                  }`}>
                    {alert.severity} SCORE: {alert.anomalyScore}%
                  </span>
                </div>

                {/* Details Section */}
                <p className="text-[10.5px] text-[#A8B4CC] leading-relaxed line-clamp-2">
                  {alert.offenceDetails}
                </p>

                {/* Footer status markers */}
                <div className="flex justify-between items-center mt-1 border-t border-slate-900 pt-2 text-[9px] font-mono">
                  <div className="flex items-center gap-1.5">
                    {alert.status === 'PENDING' ? (
                      <span className="text-red-400 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 animate-pulse" />
                        UNRESOLVED
                      </span>
                    ) : alert.status === 'REVIEWED' ? (
                      <span className="text-[#0E9E78] flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        UNDER INVESTIGATION
                      </span>
                    ) : (
                      <span className="text-[#6C43CC] flex items-center gap-1">
                        <ShieldAlert className="w-3 h-3" />
                        ESCALATED TO SP
                      </span>
                    )}
                  </div>
                  
                  <span className="text-[#6A7A96]">
                    {new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} IST
                  </span>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
        
        {activeAlerts.length === 0 && (
          <div className="p-8 text-center text-xs font-mono text-[#6A7A96] uppercase select-none border border-dashed border-border-color/30 rounded-card">
            No Active Anomalies Detected
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertFeed;
