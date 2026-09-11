import React, { useEffect, useRef } from 'react';

/**
 * SecureBackdrop — the SAKSHA login/landing environment.
 *
 * Layered, extremely low-contrast intelligence ambience:
 *   1. Radial lighting focused on the content area
 *   2. A very fine technical grid
 *   3. Abstract topographic contour lines (no specific location)
 *   4. A slow constellation of connected nodes (canvas)
 *
 * All layers are theme-aware (they resolve --lp-* tokens) and
 * degrade gracefully under prefers-reduced-motion.
 */

interface BgNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  a: number;
}

interface Pulse {
  x: number;
  y: number;
  r: number;
}

const hexToRgb = (hex: string): [number, number, number] => {
  const h = hex.trim().replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6);
  const n = parseInt(full, 16);
  if (Number.isNaN(n)) return [47, 127, 224];
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

const SecureBackdrop: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let rafId = 0;
    let nodes: BgNode[] = [];
    let pulses: Pulse[] = [];
    let accentRgb: [number, number, number] = [47, 127, 224];
    let running = true;

    const readThemeColors = () => {
      const styles = getComputedStyle(canvas);
      accentRgb = hexToRgb(styles.getPropertyValue('--lp-accent') || '#2f7fe0');
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (w === 0 || h === 0) return;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const target = Math.min(30, Math.max(14, Math.round((w * h) / 42000)));
      nodes = Array.from({ length: target }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.16,
        vy: (Math.random() - 0.5) * 0.16,
        r: 1 + Math.random() * 1.3,
        a: 0.25 + Math.random() * 0.35,
      }));
      pulses = [];
    };

    const drawFrame = (time: number) => {
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      ctx.clearRect(0, 0, w, h);

      /* Network lines */
      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dist = Math.hypot(n1.x - n2.x, n1.y - n2.y);
          if (dist < 132) {
            ctx.beginPath();
            ctx.moveTo(n1.x, n1.y);
            ctx.lineTo(n2.x, n2.y);
            ctx.strokeStyle = `rgba(${accentRgb[0]},${accentRgb[1]},${accentRgb[2]},${((1 - dist / 132) * 0.13).toFixed(3)})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }

      /* Nodes */
      for (const n of nodes) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${accentRgb[0]},${accentRgb[1]},${accentRgb[2]},${(n.a * 0.8).toFixed(3)})`;
        ctx.fill();
      }

      /* Occasional system pulse */
      pulses = pulses.filter((p) => p.r < 84);
      for (const p of pulses) {
        p.r += 0.55;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${accentRgb[0]},${accentRgb[1]},${accentRgb[2]},${(0.16 * (1 - p.r / 84)).toFixed(3)})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      if (!reducedMotion && time > 0 && Math.random() < 0.004 && pulses.length < 2 && nodes.length > 0) {
        const n = nodes[Math.floor(Math.random() * nodes.length)];
        pulses.push({ x: n.x, y: n.y, r: 6 });
      }
    };

    const tick = (time: number) => {
      if (!running) return;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      for (const n of nodes) {
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < -8) n.x = w + 8;
        if (n.x > w + 8) n.x = -8;
        if (n.y < -8) n.y = h + 8;
        if (n.y > h + 8) n.y = -8;
      }
      drawFrame(time);
      rafId = requestAnimationFrame(tick);
    };

    readThemeColors();
    resize();
    if (reducedMotion) {
      drawFrame(0);
    } else {
      rafId = requestAnimationFrame(tick);
    }

    const themeObserver = new MutationObserver(() => {
      readThemeColors();
      if (reducedMotion) drawFrame(0);
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    const handleResize = () => {
      resize();
      if (reducedMotion) drawFrame(0);
    };
    const handleVisibility = () => {
      if (document.hidden) {
        running = false;
        cancelAnimationFrame(rafId);
      } else if (!reducedMotion && !running) {
        running = true;
        rafId = requestAnimationFrame(tick);
      }
    };

    window.addEventListener('resize', handleResize);
    document.addEventListener('visibilitychange', handleVisibility);

    return () => {
      running = false;
      cancelAnimationFrame(rafId);
      themeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('visibilitychange', handleVisibility);
    };
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0" aria-hidden="true">
      {/* Radial lighting around the content area */}
      <div className="absolute inset-0 lp-glow-a" />
      {/* Very fine technical grid */}
      <div className="absolute inset-0 lp-grid-layer" />
      {/* Abstract topographic contours — large screens only */}
      <svg
        viewBox="0 0 600 500"
        className="hidden lg:block absolute right-[3%] top-1/2 -translate-y-1/2 h-[68vh] w-auto"
        fill="none"
        role="presentation"
        style={{ color: 'var(--lp-accent)', opacity: 0.06 }}
      >
        {/* Organic contour rings — abstract, no geographic identity */}
        <ellipse cx="300" cy="250" rx="260" ry="210" stroke="currentColor" strokeWidth="1.2" />
        <ellipse cx="300" cy="250" rx="210" ry="170" stroke="currentColor" strokeWidth="1" />
        <ellipse cx="300" cy="250" rx="165" ry="135" stroke="currentColor" strokeWidth="0.9" />
        <ellipse cx="300" cy="250" rx="120" ry="100" stroke="currentColor" strokeWidth="0.8" />
        <ellipse cx="300" cy="250" rx="80" ry="65" stroke="currentColor" strokeWidth="0.7" />
        <ellipse cx="300" cy="250" rx="45" ry="35" stroke="currentColor" strokeWidth="0.6" />
        {/* Offset inner contours for depth */}
        <ellipse cx="280" cy="240" rx="140" ry="115" stroke="currentColor" strokeWidth="0.6" opacity="0.7" />
        <ellipse cx="320" cy="260" rx="100" ry="80" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
        {/* Radial measurement lines */}
        <line x1="300" y1="40" x2="300" y2="460" stroke="currentColor" strokeWidth="0.3" opacity="0.4" />
        <line x1="40" y1="250" x2="560" y2="250" stroke="currentColor" strokeWidth="0.3" opacity="0.4" />
        <line x1="120" y1="90" x2="480" y2="410" stroke="currentColor" strokeWidth="0.25" opacity="0.3" />
        <line x1="480" y1="90" x2="120" y2="410" stroke="currentColor" strokeWidth="0.25" opacity="0.3" />
        {/* Scatter reference points */}
        <circle cx="180" cy="140" r="2" fill="currentColor" opacity="0.5" />
        <circle cx="420" cy="180" r="1.5" fill="currentColor" opacity="0.4" />
        <circle cx="200" cy="360" r="1.5" fill="currentColor" opacity="0.4" />
        <circle cx="400" cy="320" r="2" fill="currentColor" opacity="0.5" />
        <circle cx="130" cy="260" r="1.2" fill="currentColor" opacity="0.35" />
        <circle cx="470" cy="260" r="1.2" fill="currentColor" opacity="0.35" />
      </svg>
      {/* Slow intelligence-node constellation */}
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      {/* Vignette keeps focus on the content */}
      <div className="absolute inset-0 lp-vignette" />
    </div>
  );
};

export default SecureBackdrop;
