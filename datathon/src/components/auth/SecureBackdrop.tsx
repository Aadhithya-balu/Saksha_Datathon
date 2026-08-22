import React, { useEffect, useRef } from 'react';

/**
 * SecureBackdrop — the SAKSHA login environment.
 *
 * Layered, extremely low-contrast intelligence ambience:
 *   1. Radial lighting focused on the authentication area
 *   2. A very fine technical grid
 *   3. A stylized Karnataka landmass silhouette
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

/* Stylized Karnataka silhouette (abstract, recognizable intent) */
const KARNATAKA_PATH =
  'M132 4 L148 18 L154 44 L144 66 L152 92 L146 116 L158 140 L152 168 L136 192 ' +
  'L112 208 L84 214 L60 204 L38 186 L26 160 L20 132 L14 104 L10 76 L22 52 L44 40 L74 34 L100 20 Z';

const DISTRICT_MARKS: Array<[number, number]> = [
  [48, 62],
  [128, 178],
  [34, 186],
  [138, 84],
  [96, 214],
];

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
      {/* Radial lighting around the authentication area */}
      <div className="absolute inset-0 lp-glow-a" />
      {/* Very fine technical grid */}
      <div className="absolute inset-0 lp-grid-layer" />
      {/* Karnataka landmass — large screens only */}
      <svg
        viewBox="0 0 200 230"
        className="lp-karnataka hidden lg:block absolute right-[5%] top-1/2 -translate-y-1/2 h-[72vh] w-auto"
        role="presentation"
      >
        <path d={KARNATAKA_PATH} />
        {DISTRICT_MARKS.map(([cx, cy]) => (
          <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r="1.6" fill="currentColor" stroke="none" opacity="0.9" />
        ))}
      </svg>
      {/* Slow intelligence-node constellation */}
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      {/* Vignette keeps focus on the auth module */}
      <div className="absolute inset-0 lp-vignette" />
    </div>
  );
};

export default SecureBackdrop;
