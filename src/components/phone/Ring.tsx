"use client";

import { useEffect, useState, type ReactNode } from "react";

interface RingProps {
  value: number; // 0..1
  size?: number;
  stroke?: number;
  children?: ReactNode;
}

// Progress ring. Fills from zero on mount, then follows the value with an interruptible transition.
export function Ring({ value, size = 128, stroke = 11, children }: RingProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const shown = mounted ? Math.max(0, Math.min(1, value)) : 0;

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-kbc-accent-100)" strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--color-kbc-accent)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - shown)}
          style={{ transition: "stroke-dashoffset 700ms var(--ease-out-strong)" }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">{children}</div>
    </div>
  );
}
