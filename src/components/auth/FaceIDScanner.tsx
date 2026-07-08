import React, { useRef, useState, useEffect } from 'react';
import Webcam from 'react-webcam';
import { useFaceAuth } from '../../hooks/useFaceAuth';
import { Camera, RefreshCw, CheckCircle2, ShieldAlert, Cpu } from 'lucide-react';

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

  // Draw face mesh landmarks on overlay canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear
    ctx.clearRect(0,0, canvas.width, canvas.height);

    if (landmarks.length > 0) {
      // Set line colors based on status
      const dotColor = scanSuccess === true ? '#0E9E78' : scanSuccess === false ? '#C94A2A' : '#1E6FD9';
      const meshColor = scanSuccess === true ? 'rgba(14, 158, 120, 0.15)' : scanSuccess === false ? 'rgba(201, 74, 42, 0.15)' : 'rgba(30, 111, 217, 0.15)';

      // Draw connection lines
      ctx.lineWidth = 1;
      
      // Face jaw boundary (0-16)
      ctx.beginPath();
      ctx.moveTo(landmarks[0][0], landmarks[0][1]);
      for (let i = 1; i < 17; i++) {
        ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      }
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      // Eyebrows
      ctx.beginPath();
      ctx.moveTo(landmarks[17][0], landmarks[17][1]);
      for (let i = 18; i < 22; i++) ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(landmarks[22][0], landmarks[22][1]);
      for (let i = 23; i < 27; i++) ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      // Nose
      ctx.beginPath();
      ctx.moveTo(landmarks[27][0], landmarks[27][1]);
      for (let i = 28; i < 31; i++) ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(landmarks[31][0], landmarks[31][1]);
      for (let i = 32; i < 36; i++) ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      // Eyes
      ctx.beginPath();
      ctx.moveTo(landmarks[36][0], landmarks[36][1]);
      for (let i = 37; i < 42; i++) ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      ctx.closePath();
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(landmarks[42][0], landmarks[42][1]);
      for (let i = 43; i < 48; i++) ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      ctx.closePath();
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      // Mouth outline
      ctx.beginPath();
      ctx.moveTo(landmarks[48][0], landmarks[48][1]);
      for (let i = 49; i < 60; i++) ctx.lineTo(landmarks[i][0], landmarks[i][1]);
      ctx.closePath();
      ctx.strokeStyle = meshColor;
      ctx.stroke();

      // Draw all 68 dots
      landmarks.forEach(([x, y]) => {
        ctx.beginPath();
        ctx.arc(x, y, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = dotColor;
        ctx.fill();
        
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.strokeStyle = dotColor + '44';
        ctx.lineWidth = 0.5;
        ctx.stroke();
      });
    }
  }, [landmarks, scanSuccess]);

  return (
    <div className="flex flex-col items-center">
      {/* Biometric HUD Wrapper */}
      <div className={`relative w-80 h-80 flex items-center justify-center hex-border ${
        scanSuccess === true ? 'border-glow-emerald bg-emerald-950/20' : 
        scanSuccess === false ? 'border-glow-rose bg-rose-950/20 animate-shake' : 
        'bg-slate-950/40'
      }`}>
        
        {/* Hexagonal Clip */}
        <div className="w-[312px] h-[312px] hex-clip bg-slate-950 relative flex items-center justify-center">
          
          {/* Webcam view */}
          {!hasCameraError && !isModelLoading ? (
            <Webcam
              ref={webcamRef}
              audio={false}
              screenshotFormat="image/jpeg"
              videoConstraints={{ width: 320, height: 320, facingMode: 'user' }}
              onUserMediaError={() => setHasCameraError(true)}
              className="w-full h-full object-cover hex-clip position-absolute"
            />
          ) : (
            // Simulated Head Matrix wireframe if camera denied/no camera
            <div className="w-full h-full hex-clip flex items-center justify-center bg-[#070e1b] relative">
              <div className="absolute inset-0 flex items-center justify-center opacity-30">
                <svg viewBox="0 0 100 100" className="w-48 h-48 stroke-[#1E6FD9] fill-none stroke-[0.3]">
                  <ellipse cx="50" cy="45" rx="20" ry="26" />
                  <line x1="50" y1="10" x2="50" y2="80" />
                  <line x1="20" y1="45" x2="80" y2="45" />
                  <path d="M 33 28 Q 50 35 67 28" />
                  <path d="M 33 62 Q 50 55 67 62" />
                </svg>
              </div>
              {hasCameraError && (
                <div className="absolute bottom-4 text-center z-20">
                  <span className="text-[9px] uppercase tracking-widest font-mono text-[#D4820A] bg-black/60 px-2 py-0.5 rounded">
                    CAMERA ACCESS MUTED - SIMULATION RUN
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Canvas biometric overlay */}
          <canvas
            ref={canvasRef}
            width={320}
            height={320}
            className="absolute inset-0 w-full h-full pointer-events-none z-20"
          />

          {/* Green Laser Scan Line Sweep */}
          {isScanning && <div className="scan-line z-20" />}

          {/* HUD Target corners */}
          <div className="absolute top-8 left-8 w-4 h-4 border-t-2 border-l-2 border-[#1E6FD9] z-20 opacity-80" />
          <div className="absolute top-8 right-8 w-4 h-4 border-t-2 border-r-2 border-[#1E6FD9] z-20 opacity-80" />
          <div className="absolute bottom-8 left-8 w-4 h-4 border-b-2 border-l-2 border-[#1E6FD9] z-20 opacity-80" />
          <div className="absolute bottom-8 right-8 w-4 h-4 border-b-2 border-r-2 border-[#1E6FD9] z-20 opacity-80" />

          {/* AI Model Loading overlay */}
          {isModelLoading && (
            <div className="absolute inset-0 bg-[#0B1426] flex flex-col items-center justify-center gap-3 z-30">
              <Cpu className="w-8 h-8 text-[#1E6FD9] animate-spin" />
              <div className="text-[11px] font-mono tracking-widest uppercase text-[#A8B4CC]">
                LOADING BIOMETRIC MODELS...
              </div>
            </div>
          )}

          {/* Recognition Feedback Messages */}
          {scanSuccess === true && (
            <div className="absolute inset-0 bg-emerald-950/80 backdrop-blur-sm z-30 flex flex-col items-center justify-center gap-2">
              <CheckCircle2 className="w-12 h-12 text-[#0E9E78] animate-bounce" />
              <div className="text-[14px] font-bold uppercase tracking-widest text-[#E8EDF5] font-sans">
                Identity Verified
              </div>
              <div className="text-[10px] font-mono text-[#A8B4CC]">
                SCRB ANALYST ACCESS CLEARED
              </div>
            </div>
          )}

          {scanSuccess === false && (
            <div className="absolute inset-0 bg-rose-950/80 backdrop-blur-sm z-30 flex flex-col items-center justify-center gap-2">
              <ShieldAlert className="w-12 h-12 text-[#C94A2A] animate-ping" />
              <div className="text-[14px] font-bold uppercase tracking-widest text-[#E8EDF5]">
                Unrecognised Face
              </div>
              <div className="text-[10px] font-mono text-[#E8EDF5]">
                CREDENTIAL RECORD MISMATCH
              </div>
              <button
                onClick={resetScanner}
                className="mt-3 px-3 py-1 bg-[#C94A2A] hover:bg-[#C94A2A]/80 text-[10px] font-mono rounded cursor-pointer transition-colors"
              >
                RE-SCAN TARGET
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Control Buttons */}
      {!isModelLoading && scanSuccess === null && (
        <div className="mt-6 flex flex-col items-center gap-2">
          {isScanning ? (
            <div className="w-64">
              <div className="flex justify-between text-[10px] font-mono text-[#A8B4CC] mb-1">
                <span>ANALYZING EYE CORRELATION...</span>
                <span>{scanProgress}%</span>
              </div>
              <div className="w-full bg-[#111D35] h-1 rounded overflow-hidden">
                <div
                  className="bg-[#0E9E78] h-full transition-all duration-100 shadow-glow-teal"
                  style={{ width: `${scanProgress}%` }}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={startScanning}
              className="flex items-center gap-2 px-6 py-2.5 bg-[#1E6FD9] hover:bg-[#1E6FD9]/80 shadow-glow-blue hover:scale-105 active:scale-100 text-white font-mono text-xs uppercase tracking-wider rounded-btn transition-all cursor-pointer"
            >
              <Camera className="w-4 h-4" />
              Commence Face Authenticator
            </button>
          )}
          
          <span className="text-[9px] font-mono text-[#6A7A96] mt-2 select-none uppercase">
            FACIAL RECOGNITION CLEARANCE LAYER 10
          </span>
        </div>
      )}
    </div>
  );
};

export default FaceIDScanner;
