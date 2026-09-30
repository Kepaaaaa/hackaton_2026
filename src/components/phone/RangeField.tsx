"use client";

import { useId } from "react";

interface RangeFieldProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  display: string;
  onChange: (value: number) => void;
  minLabel?: string;
  maxLabel?: string;
}

export function RangeField({ label, value, min, max, step, display, onChange, minLabel, maxLabel }: RangeFieldProps) {
  const id = useId();
  const fill = max === min ? 0 : ((value - min) / (max - min)) * 100;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <label htmlFor={id} className="text-[13px] font-bold text-kbc-night-300">
          {label}
        </label>
        <output htmlFor={id} className="tabular text-[15px] font-extrabold text-kbc-night">
          {display}
        </output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="kbc-range mt-1"
        style={{ "--fill": `${fill}%` } as React.CSSProperties}
      />
      {minLabel || maxLabel ? (
        <div className="tabular flex justify-between text-[11px] font-semibold text-kbc-night-200">
          <span>{minLabel}</span>
          <span>{maxLabel}</span>
        </div>
      ) : null}
    </div>
  );
}
