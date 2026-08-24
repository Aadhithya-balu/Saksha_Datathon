/**
 * Issue #118 — FaceIDScanner
 *
 * Real biometric authentication UI.  Captures a webcam frame and sends it
 * to the backend for server-side matching against the KSP officer database.
 * No demo data, no Math.random(), no hardcoded faces.
 */
import React, { useRef, useState, useEffect } from 'react';
import Webcam from 'react-webcam';
import { useFaceAuth } from '../../hooks/useFaceAuth';
import {
  Eye,
  ShieldAlert,
  Loader2,
  CheckCircle2,
  ScanFace,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react';

interface FaceIDScannerProps {
  onVerifySuccess: () => void;
}

export const FaceIDScanner: React.FC<FaceIDScannerProps> = ({ onVerifySuccess }) => {
  const {
    isModelLoading,
    isScanning,
    scanProgress,
    scanSuccess,
    errorMessage,
    startScanning,
    resetScanner,
  } = useFaceAuth();

  const [hasCameraError, setHasCameraError] = useState(false);
  const webcamRef = useRef<Webcam>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  /* Trigger success callback after brief confirmation display */
  useEffect(() => {
    if (scanSuccess === true) {
      const timer = setTimeout(() => onVerifySuccess(), 1400);
      return () => clearTimeout(timer);
    }
  }, [scanSuccess, onVerifySuccess]);

  const handleStartScan = () => {
    if (!hasCameraError) {
      startScanning(webcamRef);
    }
  };

  const frameColor =
    scanSuccess === true
      ? 'var(--lp-green)'
      : scanSuccess === false
        ? 'var(--lp-red)'
        : 'var(--lp-border-strong)';

  const frameGlow =
    scanSuccess === true
      ? '0 0 0 1px rgba(47,185,132,0.35), 0 0 24px rgba(47,185,132,0.12)'
      : scanSuccess === false
        ? '0 0 0 1px rgba(224,96,85,0.35), 0 0 24px rgba(224,96,85,0.10)'
        : 'none';

  return (
    <div className="flex flex-col items-center w-full">
      {/* Biometric viewport */}
      <div
        className="relative aspect-square w-[clamp(190px,32vh,250px)] overflow-hidden rounded-xl border transition-all duration-300"
        style={{
          borderColor: frameColor,
          background: 'var(--lp-surface-3)',
          boxShadow: frameGlow,
          animation: scanSuccess === false ? 'lp-shake 0.4s ease-in-out' : undefined,
        }}
        role="img"
        aria-label="Biometric face verification viewport"
      >
        {/* Camera stream */}
        {!hasCameraError && !isModelLoading && (
          <Webcam
            ref={webcamRef}
            audio={false}
            screenshotFormat="image/jpeg"
            screenshotQuality={0.85}
            videoConstraints={{ width: 320, height: 320, facingMode: 'user' }}
            onUserMediaError={() => setHasCameraError(true)}
            className="absolute inset-0 w-full h-full object-cover"
            mirrored={false}
          />
        )}

        {/* Camera offline backdrop */}
        {(hasCameraError || isModelLoading) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <ScanFace
              className="w-14 h-14 stroke-[1]"
              style={{ color: hasCameraError ? 'var(--lp-text-3)' : 'var(--lp-accent-hi)', opacity: 0.5 }}
            />
            {hasCameraError && (
              <span
                className="text-[8px] font-mono uppercase tracking-[0.18em] text-center px-3"
                style={{ color: 'var(--lp-amber)' }}
              >
                Camera unavailable · use Badge ID
              </span>
            )}
          </div>
        )}

        {/* Overlay canvas (kept for alignment brackets) */}
        <canvas
          ref={canvasRef}
          width={320}
          height={320}
          className="absolute inset-0 w-full h-full pointer-events-none z-20"
        />

        {/* Sweep line while analyzing */}
        {isScanning && <div className="lp-scanline z-20 rounded-none" aria-hidden="true" />}

        {/* Alignment brackets */}
        {(['top-2.5 left-2.5 border-t border-l',
           'top-2.5 right-2.5 border-t border-r',
           'bottom-2.5 left-2.5 border-b border-l',
           'bottom-2.5 right-2.5 border-b border-r'] as const).map((pos) => (
          <div
            key={pos}
            className={`absolute w-4 h-4 z-20 transition-colors duration-300 ${pos}`}
            style={{
              borderColor:
                scanSuccess === true
                  ? 'var(--lp-green)'
                  : scanSuccess === false
                    ? 'var(--lp-red)'
                    : 'var(--lp-accent-hi)',
            }}
            aria-hidden="true"
          />
        ))}

        {/* Verified overlay */}
        {scanSuccess === true && (
          <div
            className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-2"
            style={{ background: 'color-mix(in srgb, var(--lp-green) 14%, rgba(4,10,18,0.82))' }}
          >
            <CheckCircle2 className="w-11 h-11" style={{ color: 'var(--lp-green)' }} strokeWidth={1.6} />
            <span className="font-sans text-[13px] font-bold uppercase tracking-wide" style={{ color: 'var(--lp-text)' }}>
              Identity Verified
            </span>
            <span className="font-mono text-[8.5px] uppercase tracking-[0.18em]" style={{ color: 'var(--lp-green)' }}>
              Clearance granted
            </span>
          </div>
        )}

        {/* Rejected overlay */}
        {scanSuccess === false && (
          <div
            className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-2 px-3"
            style={{ background: 'color-mix(in srgb, var(--lp-red) 14%, rgba(4,10,18,0.84))' }}
          >
            <ShieldAlert className="w-11 h-11" style={{ color: 'var(--lp-red)' }} strokeWidth={1.6} />
            <span className="font-sans text-[12px] font-bold uppercase tracking-wide text-center" style={{ color: 'var(--lp-text)' }}>
              Identity Not Verified
            </span>
            <span
              className="font-mono text-[8px] uppercase tracking-[0.14em] text-center leading-relaxed"
              style={{ color: 'var(--lp-text-2)' }}
            >
              {errorMessage ?? 'Your face could not be matched with an authorized KSP officer.'}
            </span>
            <button
              onClick={resetScanner}
              className="mt-2 px-3 py-1.5 rounded-md border flex items-center gap-1.5 font-mono text-[9px] font-bold uppercase tracking-widest cursor-pointer transition-colors hover:bg-[color:var(--lp-accent-soft)]"
              style={{ borderColor: 'var(--lp-border-strong)', color: 'var(--lp-text)', background: 'transparent' }}
            >
              <RotateCcw className="w-3 h-3" />
              Retry Scan
            </button>
          </div>
        )}
      </div>

      {/* Controls / progress */}
      {!isModelLoading && scanSuccess === null && (
        <div className="mt-5 w-[clamp(190px,32vh,250px)]">
          {isScanning ? (
            <div aria-live="polite">
              <div className="flex items-baseline justify-between mb-1.5">
                <span
                  className="font-sans text-[9px] font-semibold uppercase tracking-[0.14em]"
                  style={{ color: 'var(--lp-text-3)' }}
                >
                  {scanProgress < 65 ? 'Capturing frame' : 'Verifying identity'}
                </span>
                <span className="font-mono text-[9px]" style={{ color: 'var(--lp-accent-hi)' }}>
                  {scanProgress}%
                </span>
              </div>
              <div
                className="w-full h-1 rounded-full overflow-hidden"
                style={{ background: 'var(--lp-surface-3)' }}
                role="progressbar"
                aria-valuenow={scanProgress}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="h-full rounded-full transition-all duration-100"
                  style={{
                    width: `${scanProgress}%`,
                    background: 'linear-gradient(90deg, var(--lp-accent), var(--lp-teal))',
                  }}
                />
              </div>
            </div>
          ) : (
            <button
              onClick={handleStartScan}
              disabled={hasCameraError}
              className="lp-primary-btn relative flex h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl font-sans text-xs font-bold uppercase tracking-[0.18em] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                background: 'linear-gradient(135deg, var(--lp-accent), #2467c2)',
                color: '#f2f6fc',
                boxShadow: '0 8px 24px rgba(31, 92, 179, 0.32)',
              }}
            >
              <Eye className="h-4 w-4" strokeWidth={2} />
              Verify With Face ID
            </button>
          )}
        </div>
      )}

      {/* Honest capability disclosure */}
      <p
        className="mx-auto mt-4 inline-flex max-w-[280px] items-center gap-1.5 rounded-full border px-3 py-1 text-center font-mono text-[8px] uppercase tracking-[0.16em]"
        style={{ borderColor: 'var(--lp-border)', background: 'var(--lp-surface-3)', color: 'var(--lp-text-3)' }}
      >
        <AlertTriangle className="w-2.5 h-2.5 shrink-0" style={{ color: 'var(--lp-amber)' }} />
        Basic face matching · no liveness detection
      </p>
    </div>
  );
};

export default FaceIDScanner;
