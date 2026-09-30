import { THRESHOLD } from "@/lib/engine/types";
import { pct } from "@/lib/format";

export function ConfidenceGauge({ value, active }: { value: number; active: boolean }) {
  const above = value >= THRESHOLD;
  const shown = active ? value : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <p className="text-[13px] font-bold text-kbc-night-300">Confidence</p>
        <p className={`tabular text-[26px] font-extrabold leading-none ${!active ? "text-kbc-night-200" : above ? "text-kbc-accent" : "text-kbc-warning"}`}>
          {active ? pct(value) : "—"}
        </p>
      </div>
      <div className="relative mt-3 h-3 rounded-full bg-kbc-night-25">
        <div
          className={`h-full rounded-full transition-[width,background-color] duration-500 ease-(--ease-out-strong) ${above ? "bg-kbc-accent" : "bg-kbc-warning"}`}
          style={{ width: pct(shown) }}
        />
        <div className="absolute -top-1.5 bottom-[-6px] w-0.5 rounded-full bg-kbc-night" style={{ left: pct(THRESHOLD) }} aria-hidden />
      </div>
      <div className="relative mt-1.5 h-4 text-[11px] font-bold text-kbc-night-300">
        <span className="absolute -translate-x-1/2" style={{ left: pct(THRESHOLD) }}>
          {pct(THRESHOLD)} threshold
        </span>
      </div>
    </div>
  );
}
