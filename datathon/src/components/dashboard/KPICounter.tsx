import React, { useEffect, useState } from 'react';

interface KPICounterProps {
  value: number;
  suffix?: string;
  prefix?: string;
  durationMs?: number;
}

export const KPICounter: React.FC<KPICounterProps> = ({
  value,
  suffix = '',
  prefix = '',
  durationMs = 1200
}) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let active = true;
    const startTime = performance.now();

    const run = (now: number) => {
      if (!active) return;
      const elapsed = now - startTime;
      const progress = Math.min(1, elapsed / durationMs);
      
      // easeOutQuint
      const ease = 1 - Math.pow(1 - progress, 5);
      const currentVal = Math.floor(ease * value);
      
      setCount(currentVal);

      if (progress < 1) {
        requestAnimationFrame(run);
      } else {
        setCount(value);
      }
    };

    requestAnimationFrame(run);

    return () => {
      active = false;
    };
  }, [value, durationMs]);

  return (
    <span>
      {prefix}
      {count.toLocaleString()}
      {suffix}
    </span>
  );
};

export default KPICounter;
