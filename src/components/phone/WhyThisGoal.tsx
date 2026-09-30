"use client";

import type { Signal, SignalSource } from "@/lib/engine/types";
import { THRESHOLD } from "@/lib/engine/types";
import { pct } from "@/lib/format";
import { Switch } from "./Switch";

const SOURCE: Record<SignalSource, { label: string; tone: string }> = {
  transactions: { label: "Your transactions", tone: "bg-kbc-night-25 text-kbc-night-300" },
  products: { label: "Your products", tone: "bg-kbc-night-25 text-kbc-night-300" },
  declared: { label: "You told us", tone: "bg-[#fdecee] text-[#a32a3b]" },
};

interface WhyThisGoalProps {
  title: string;
  signals: Signal[];
  disabled: string[];
  confidence: number;
  onToggle: (id: string, on: boolean) => void;
}

export function WhyThisGoal({ title, signals, disabled, confidence, onToggle }: WhyThisGoalProps) {
  const below = confidence < THRESHOLD;
  return (
    <section className="rounded-kbc bg-white p-4 shadow-kbc">
      <div className="flex items-baseline justify-between px-1">
        <h3 className="text-[15px] font-extrabold text-kbc-night">{title}</h3>
        <span className={`tabular text-[12px] font-bold ${below ? "text-kbc-warning" : "text-kbc-night-300"}`}>
          Confidence {pct(confidence)}
        </span>
      </div>
      <ul className="mt-2 divide-y divide-kbc-night-100/60">
        {signals.map((s) => {
          const on = !disabled.includes(s.id);
          return (
            <li key={s.id} className="flex items-center gap-3 px-1 py-3">
              <div className={`min-w-0 flex-1 transition-opacity duration-200 ${on ? "" : "opacity-45"}`}>
                <p className="text-[13.5px] font-bold leading-snug text-kbc-night">{s.label}</p>
                <p className="mt-0.5 text-[12px] leading-snug text-kbc-night-300">{s.detail}</p>
                <span className={`mt-1.5 inline-block rounded-kbc-sm px-1.5 py-0.5 text-[10.5px] font-bold ${SOURCE[s.source].tone}`}>
                  {SOURCE[s.source].label} · weight {s.weight.toFixed(2)}
                </span>
              </div>
              <Switch size="sm" checked={on} onChange={(v) => onToggle(s.id, v)} label={`Use signal: ${s.label}`} />
            </li>
          );
        })}
      </ul>
      <p className="px-1 pt-1 text-[11.5px] leading-snug text-kbc-night-300">
        Switch off a signal and the screen recomposes. Below {pct(THRESHOLD)} confidence, we show nothing.
      </p>
    </section>
  );
}
