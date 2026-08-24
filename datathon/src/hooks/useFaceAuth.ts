/**
 * Issue #118 — useFaceAuth
 *
 * Real face-verification hook.  Captures a webcam frame, sends it to the
 * backend /auth/face-verify endpoint, and returns the result.
 *
 * The backend performs ALL biometric matching server-side against the real
 * KSP officer database.  No embeddings are downloaded to the browser.
 * No demo data, no hardcoded faces, no Math.random() success.
 */
import { useState, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../services/api';

export type FaceAuthState =
  | 'idle'
  | 'capturing'
  | 'verifying'
  | 'success'
  | 'failure';

export interface FaceAuthResult {
  /** Current state of the verification flow */
  state: FaceAuthState;
  /** Progress 0-100 shown during capture/verify phases */
  scanProgress: number;
  /** True while the camera is warming up */
  isModelLoading: boolean;
  /** True while actively scanning */
  isScanning: boolean;
  /** null = not yet attempted; true = success; false = failure */
  scanSuccess: boolean | null;
  /** Landmark points for the canvas overlay (empty when not scanning) */
  landmarks: [number, number][];
  /** Human-readable error message on failure */
  errorMessage: string | null;
  /** Verified officer info returned on success */
  verifiedOfficer: { name: string; badgeNumber: string; role: string } | null;
  /** Start the scan + verification flow */
  startScanning: (webcamRef: React.RefObject<any>) => void;
  /** Reset to idle */
  resetScanner: () => void;
}

const ERROR_MESSAGES: Record<string, string> = {
  NO_FACE:       'No face detected. Please position your face clearly in the frame.',
  MULTI_FACE:    'Multiple faces detected. Please ensure only one person is visible.',
  NO_MATCH:      'Identity could not be verified. Your face does not match any authorized KSP officer.',
  INACTIVE:      'This officer account is inactive. Contact your administrator.',
  NO_ENROLLMENT: 'Face ID enrollment required. No biometric records are registered in the system.',
  BAD_IMAGE:     'Unable to process the image. Please adjust lighting and try again.',
};

export const useFaceAuth = (): FaceAuthResult => {
  const [state, setState] = useState<FaceAuthState>('idle');
  const [scanProgress, setScanProgress] = useState(0);
  const [isModelLoading] = useState(false);   // camera warms up in the component
  const [scanSuccess, setScanSuccess] = useState<boolean | null>(null);
  const [landmarks, setLandmarks] = useState<[number, number][]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [verifiedOfficer, setVerifiedOfficer] = useState<FaceAuthResult['verifiedOfficer']>(null);

  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const _clearProgress = () => {
    if (progressRef.current) {
      clearInterval(progressRef.current);
      progressRef.current = null;
    }
  };

  const resetScanner = useCallback(() => {
    _clearProgress();
    setState('idle');
    setScanProgress(0);
    setScanSuccess(null);
    setLandmarks([]);
    setErrorMessage(null);
    setVerifiedOfficer(null);
  }, []);

  const startScanning = useCallback(async (webcamRef: React.RefObject<any>) => {
    resetScanner();
    setState('capturing');
    setScanProgress(0);

    // Animate progress bar to ~60% while capturing
    let progress = 0;
    progressRef.current = setInterval(() => {
      progress = Math.min(progress + 4, 60);
      setScanProgress(progress);
    }, 80);

    // Give the progress bar a moment to animate before capturing
    await new Promise<void>((r) => setTimeout(r, 600));

    // Capture frame from webcam
    let imageSrc: string | null = null;
    try {
      if (webcamRef.current?.getScreenshot) {
        imageSrc = webcamRef.current.getScreenshot();
      }
    } catch {
      // webcam not ready
    }

    if (!imageSrc) {
      _clearProgress();
      setScanProgress(0);
      setState('failure');
      setScanSuccess(false);
      setErrorMessage('Camera is not available. Please allow camera access and try again.');
      return;
    }

    // Animate progress to ~80% during server round-trip
    setState('verifying');
    progressRef.current = setInterval(() => {
      setScanProgress((p) => Math.min(p + 2, 90));
    }, 100);

    try {
      const { accessToken } = (() => {
        const at = typeof window !== 'undefined'
          ? window.localStorage.getItem('saksha_access_token') ?? ''
          : '';
        return { accessToken: at };
      })();

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

      const response = await fetch(`${API_BASE_URL}/auth/face-verify`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ image_b64: imageSrc }),
      });

      _clearProgress();
      setScanProgress(100);

      if (response.ok) {
        // Backend returns JWT tokens on success — store them
        const data = await response.json();
        // Store tokens so authStore.initializeSession can hydrate
        if (data.access_token) {
          window.localStorage.setItem('saksha_access_token', data.access_token);
        }
        if (data.refresh_token) {
          window.localStorage.setItem('saksha_refresh_token', data.refresh_token);
        }
        setState('success');
        setScanSuccess(true);
        setErrorMessage(null);
        // verifiedOfficer will be populated by authStore.initializeSession via /auth/me
        setVerifiedOfficer({ name: '', badgeNumber: '', role: '' });
      } else {
        const body = await response.json().catch(() => ({}));
        const code: string = body?.error?.code ?? body?.detail ?? 'NO_MATCH';
        const msg = ERROR_MESSAGES[code] ?? body?.error?.message ?? 'Identity could not be verified.';
        setState('failure');
        setScanSuccess(false);
        setErrorMessage(msg);
      }
    } catch (err) {
      _clearProgress();
      setState('failure');
      setScanSuccess(false);
      setErrorMessage('Verification service is unavailable. Please use Badge ID login.');
    }
  }, [resetScanner]);

  return {
    state,
    scanProgress,
    isModelLoading,
    isScanning: state === 'capturing' || state === 'verifying',
    scanSuccess,
    landmarks,
    errorMessage,
    verifiedOfficer,
    startScanning,
    resetScanner,
  };
};
