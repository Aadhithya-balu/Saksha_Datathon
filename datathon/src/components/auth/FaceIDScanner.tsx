import React, { useRef, useState, useEffect } from 'react';
import Webcam from 'react-webcam';
import { useFaceAuth } from '../../hooks/useFaceAuth';
import { Eye, ShieldAlert, Cpu, CheckCircle2, Scan } from 'lucide-react';

interface FaceIDScannerProps {
  onVerifySuccess: () => void;
}

export const FaceIDScanner: React.FC<FaceIDScannerProps> = ({ onVerifySuccess }) => {
  const {
    isModelLoading,
    isScanning,
    scanProgress,
    scanSuccess,
    landmarks,
    startScanning,
    resetScanner
  } = useFaceAuth();

  const [hasCameraError, setHasCameraError] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const webcamRef = useRef<Webcam>(null);

  // Trigger success callback after feedback animation delay
  useEffect(() => {
    if (scanSuccess === true) {
      const timer = setTimeout(() => {
        onVerifySuccess();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [scanSuccess, onVerifySuccess]);

  // Draw simple bounding grid overlay
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (landmarks.length > 0) {
      const color = scanSuccess === true ? '#0E9E78' : scanSuccess === false ? '#C94A2A' : '#1E6FD9';
      
      // Draw a clean bounding face box
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      
      // Find min/max landmarks to draw box
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      landmarks.forEach(([x, y]) => {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      });

      // Pad box slightly
      const padding = 15;
      minX -= padding;
      maxX += padding;
      minY -= padding;
      maxY += padding;

      const width = maxX - minX;
      const height = maxY - minY;

      ctx.strokeRect(minX, minY, width, height);
      ctx.setLineDash([]);
      
      // Draw facial center target
      ctx.beginPath();
      ctx.arc(minX + width / 2, minY + height / 2, 4, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    }
  }, [landmarks, scanSuccess]);

  return (
    <div className="flex flex-col items-center w-full">
      
      {/* 1. Camera preview placeholder / Scanner Frame */}
      <div className={`relative w-72 h-72 rounded-2xl border flex items-center justify-center overflow-hidden transition-all duration-300 ${
        scanSuccess === true ? 'border-[#0E9E78] bg-emerald-950/10 shadow-[0_0_20px_rgba(14,158,120,0.15)]' : 
        scanSuccess === false ? 'border-[#C94A2A] bg-rose-950/10 shadow-[0_0_20px_rgba(201,74,42,0.15)] animate-shake' : 
        'border-border-color bg-[var(--bg-secondary)]/45'
      }`}>
        
        {/* Webcam stream */}
        {!hasCameraError && !isModelLoading ? (
          <Webcam
            ref={webcamRef}
            audio={false}
            screenshotFormat="image/jpeg"
            videoConstraints={{ width: 320, height: 320, facingMode: 'user' }}
            onUserMediaError={() => setHasCameraError(true)}
            className="w-full h-full object-cover rounded-2xl position-absolute"
          />
        ) : (
          // Simulated Scanner Frame / Large illustration placeholder
          <div className="w-full h-full flex flex-col items-center justify-center bg-[var(--bg-secondary)] relative">
            <div className="text-[var(--text-disabled)] flex flex-col items-center justify-center space-y-3">
              <Scan className="w-16 h-16 stroke-[1.2] text-[#1E6FD9]/30" />
              <span className="text-[8px] font-mono uppercase tracking-widest text-[var(--text-muted)]">
                Camera placeholder
              </span>
            </div>
            {hasCameraError && (
              <div className="absolute bottom-3 text-center z-20">
                <span className="text-[8px] uppercase tracking-widest font-mono text-[#D4820A] bg-black/60 px-2 py-0.5 rounded">
                  Camera offline - simulation active
                </span>
              </div>
            )}
          </div>
        )}

        {/* Canvas overlay */}
        <canvas
          ref={canvasRef}
          width={320}
          height={320}
          className="absolute inset-0 w-full h-full pointer-events-none z-20"
        />

        {/* Dynamic laser scan bar */}
        {isScanning && <div className="scan-line z-20" />}

        {/* Corner Alignment brackets */}
        <div className="absolute top-4 left-4 w-4 h-4 border-t border-l border-[#1E6FD9] z-20" />
        <div className="absolute top-4 right-4 w-4 h-4 border-t border-r border-[#1E6FD9] z-20" />
        <div className="absolute bottom-4 left-4 w-4 h-4 border-b border-l border-[#1E6FD9] z-20" />
        <div className="absolute bottom-4 right-4 w-4 h-4 border-b border-r border-[#1E6FD9] z-20" />

        {/* Loading overlay */}
        {isModelLoading && (
          <div className="absolute inset-0 bg-[#0B1426] flex flex-col items-center justify-center gap-3 z-30 font-mono text-[9px] uppercase tracking-widest">
            <Cpu className="w-6 h-6 text-[#1E6FD9] animate-spin" />
            <span className="text-[var(--text-secondary)]">Loading AI biometrics...</span>
          </div>
        )}

        {/* Verification Success Overlay */}
        {scanSuccess === true && (
          <div className="absolute inset-0 bg-emerald-950/80 backdrop-blur-sm z-30 flex flex-col items-center justify-center gap-2">
            <CheckCircle2 className="w-12 h-12 text-[#0E9E78] animate-bounce" />
            <span className="text-[13px] font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Face Match Verified
            </span>
            <span className="text-[8.5px] font-mono text-[var(--text-secondary)]">
              Clearance granted
            </span>
          </div>
        )}

        {/* Verification Failure Overlay */}
        {scanSuccess === false && (
          <div className="absolute inset-0 bg-rose-950/80 backdrop-blur-sm z-30 flex flex-col items-center justify-center gap-2">
            <ShieldAlert className="w-12 h-12 text-[#C94A2A] animate-ping" />
            <span className="text-[13px] font-bold uppercase tracking-wider text-[var(--text-primary)]">
              Identity Rejected
            </span>
            <span className="text-[8.5px] font-mono text-[var(--text-secondary)]">
              No matching record
            </span>
            <button
              onClick={resetScanner}
              className="mt-3 px-3 py-1 bg-[#C94A2A] hover:bg-[#C94A2A]/80 text-[9.5px] font-mono text-[var(--text-primary)] rounded cursor-pointer transition-colors"
            >
              Re-scan
            </button>
          </div>
        )}
      </div>

      {/* 2. Control block & progress indicator */}
      {!isModelLoading && scanSuccess === null && (
        <div className="mt-5 w-full flex flex-col items-center">
          {isScanning ? (
            <div className="w-72 font-mono">
              <div className="flex justify-between text-[9px] text-[var(--text-secondary)] mb-1.5 uppercase">
                <span>Analyzing facial landmarks...</span>
                <span>{scanProgress}%</span>
              </div>
              <div className="w-full bg-[var(--bg-tertiary)] h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-[#0e9e78] h-full transition-all duration-100 shadow-glow-teal"
                  style={{ width: `${scanProgress}%` }}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={startScanning}
              className="w-72 py-2.5 bg-[#1E6FD9] hover:bg-[#1E6FD9]/85 text-[var(--text-primary)] font-mono text-[10px] font-bold uppercase tracking-wider rounded-btn hover:translate-y-[-1px] transition-all cursor-pointer flex items-center justify-center gap-2"
            >
              <Eye className="w-4 h-4" />
              <span>Verify Face ID</span>
            </button>
          )}
        </div>
      )}
      
      <span className="text-[8.5px] font-mono text-[var(--text-muted)] mt-4 uppercase select-none">
        Cryptographic Face Authentication Protocol (V2)
      </span>
    </div>
  );
};

export default FaceIDScanner;
