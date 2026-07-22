import { useState, useEffect, useRef } from 'react';

// Generates 68 standard facial landmarks centered in the frame
const generateFaceLandmarks = (centerX: number, centerY: number, width: number, height: number, time: number) => {
  const points: [number, number][] = [];
  const breathing = Math.sin(time * 2) * 2;
  const shakeX = Math.cos(time * 5) * 1.5;
  const shakeY = Math.sin(time * 5) * 1.5;

  const wScale = width * 0.35;
  const hScale = height * 0.42;

  // 0-16: Face Outline (U-shape)
  for (let i = 0; i < 17; i++) {
    const angle = Math.PI + (i * Math.PI) / 16;
    const offsetMultiplier = 1.0 + Math.sin(angle * 3 + time) * 0.01;
    points.push([
      centerX + Math.cos(angle) * wScale * offsetMultiplier + shakeX,
      centerY + Math.sin(angle) * hScale * 0.9 * offsetMultiplier + breathing + shakeY
    ]);
  }

  // 17-21: Left Eyebrow
  for (let i = 0; i < 5; i++) {
    points.push([
      centerX - wScale * (0.8 - i * 0.12) + shakeX,
      centerY - hScale * 0.35 + Math.sin(i * 0.5) * 5 + breathing + shakeY
    ]);
  }

  // 22-26: Right Eyebrow
  for (let i = 0; i < 5; i++) {
    points.push([
      centerX + wScale * (0.32 + i * 0.12) + shakeX,
      centerY - hScale * 0.35 + Math.sin((4 - i) * 0.5) * 5 + breathing + shakeY
    ]);
  }

  // 27-30: Nose Bridge
  for (let i = 0; i < 4; i++) {
    points.push([
      centerX + shakeX,
      centerY - hScale * 0.15 + i * 20 + breathing + shakeY
    ]);
  }

  // 31-35: Nose Tip / Base
  for (let i = 0; i < 5; i++) {
    points.push([
      centerX - 35 + i * 17.5 + shakeX,
      centerY + hScale * 0.15 + Math.abs(2 - i) * 5 + breathing + shakeY
    ]);
  }

  // 36-41: Left Eye
  const eyeLeftCenterX = centerX - wScale * 0.45;
  const eyeLeftCenterY = centerY - hScale * 0.08;
  const eyeRadius = 16;
  for (let i = 0; i < 6; i++) {
    const angle = (i * Math.PI) / 3;
    points.push([
      eyeLeftCenterX + Math.cos(angle) * eyeRadius + shakeX,
      eyeLeftCenterY + Math.sin(angle) * eyeRadius * 0.6 + breathing + shakeY
    ]);
  }

  // 42-47: Right Eye
  const eyeRightCenterX = centerX + wScale * 0.45;
  const eyeRightCenterY = centerY - hScale * 0.08;
  for (let i = 0; i < 6; i++) {
    const angle = (i * Math.PI) / 3;
    points.push([
      eyeRightCenterX + Math.cos(angle) * eyeRadius + shakeX,
      eyeRightCenterY + Math.sin(angle) * eyeRadius * 0.6 + breathing + shakeY
    ]);
  }

  // 48-59: Outer Mouth
  const mouthW = wScale * 0.45;
  const mouthH = hScale * 0.22;
  for (let i = 0; i < 12; i++) {
    const angle = (i * Math.PI) / 6;
    points.push([
      centerX + Math.cos(angle) * mouthW + shakeX,
      centerY + hScale * 0.35 + Math.sin(angle) * mouthH * (angle > Math.PI ? 0.5 : 1.0) + breathing + shakeY
    ]);
  }

  // 60-67: Inner Mouth
  for (let i = 0; i < 8; i++) {
    const angle = (i * Math.PI) / 4;
    points.push([
      centerX + Math.cos(angle) * mouthW * 0.7 + shakeX,
      centerY + hScale * 0.35 + Math.sin(angle) * mouthH * 0.3 + breathing + shakeY
    ]);
  }

  return points;
};

export const useFaceAuth = () => {
  const [isModelLoading, setIsModelLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanSuccess, setScanSuccess] = useState<boolean | null>(null);
  const [landmarks, setLandmarks] = useState<[number, number][]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  
  // Simulate Model Loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsModelLoading(false);
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  // Scanning sound generator (scientific sweep sound)
  const playScanBeep = (freqStart: number, freqEnd: number, duration: number, type: OscillatorType = 'sine') => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
      
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      
      osc.type = type;
      osc.frequency.setValueAtTime(freqStart, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(freqEnd, ctx.currentTime + duration);
      
      gain.gain.setValueAtTime(0.06, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.001, ctx.currentTime + duration);
      
      osc.connect(gain);
      gain.connect(ctx.destination);
      
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      console.warn("Audio Context blocked by browser permission policy.");
    }
  };

  const startScanning = () => {
    if (isModelLoading) return;
    setIsScanning(true);
    setScanProgress(0);
    setScanSuccess(null);
    playScanBeep(300, 600, 0.4, 'sawtooth');
  };

  // Perform landmarks update loop during scanning
  useEffect(() => {
    let animationId: number;
    let progressTimer: NodeJS.Timeout;

    if (isScanning && !isModelLoading) {
      const startTime = Date.now();
      
      const updateMesh = () => {
        const timeVal = (Date.now() - startTime) / 1000;
        // Assume frame is 320x320 inside login layout
        const curPoints = generateFaceLandmarks(160, 150, 320, 320, timeVal);
        setLandmarks(curPoints);
        
        // play scanning clicking sound occasionally
        if (Math.random() < 0.1) {
          playScanBeep(800, 850, 0.05, 'sine');
        }

        animationId = requestAnimationFrame(updateMesh);
      };
      
      animationId = requestAnimationFrame(updateMesh);

      // Progress Tracker
      progressTimer = setInterval(() => {
        setScanProgress((prev) => {
          if (prev >= 100) {
            clearInterval(progressTimer);
            cancelAnimationFrame(animationId);
            evaluateFaceMatching();
            return 100;
          }
          return prev + 5;
        });
      }, 100);
    }

    return () => {
      cancelAnimationFrame(animationId);
      clearInterval(progressTimer);
    };
  }, [isScanning, isModelLoading]);

  const evaluateFaceMatching = () => {
    // 90% chance success for UX demo, 10% chance mock failure
    const success = Math.random() < 0.92;
    setScanSuccess(success);
    setIsScanning(false);
    
    if (success) {
      playScanBeep(600, 1000, 0.5, 'sine');
    } else {
      playScanBeep(250, 100, 0.6, 'triangle');
    }
  };

  return {
    isModelLoading,
    isScanning,
    scanProgress,
    scanSuccess,
    landmarks,
    startScanning,
    resetScanner: () => {
      setScanSuccess(null);
      setIsScanning(false);
      setScanProgress(0);
      setLandmarks([]);
    }
  };
};
