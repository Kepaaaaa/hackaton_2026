"use client";

import { useEffect, useState } from "react";
import type { Persona, Recommendation } from "@/lib/engine/types";
import { ConfidenceGauge } from "./ConfidenceGauge";

const STEP_DELAY = 350;
const STEP_NAMES = ["Read", "Measure the gap", "Decide", "Compose", "Explain"];

const VERDICT: Record<Recommendation["status"], string> = {
  proposal: "Card composed",
  "nothing-to-suggest": "Nothing to suggest",
  "low-confidence": "Card hidden: below threshold",
  "no-consent": "Nothing read: no consent",
};

interface BehindTheScenesProps {
  persona: Persona;
  rec: Recommendation;
  active: boolean;
  disabledSignals: string[];
}

export function BehindTheScenes({ persona, rec, active, disabledSignals }: BehindTheScenesProps) {
  const revealed = useRevealCount(active, rec.steps.length);
  const weights = rec.status === "no-consent" ? [] : persona.signals.filter((s) => !disabledSignals.includes(s.id)).map((s) => s.weight.toFixed(2));

  return (
    <aside aria-label="Behind the scenes" className="rounded-[14px] bg-white p-6 shadow-kbc">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
        <h2 className="text-[13px] font-extrabold uppercase tracking-[0.08em] text-kbc-night">Behind the scenes</h2>
        <span className={`flex items-center gap-1.5 text-[12px] font-bold ${active ? "text-kbc-accent-600" : "text-kbc-night-200"}`}>
          <span className={`size-2 rounded-full ${active ? "bg-kbc-accent" : "bg-kbc-night-100"}`} />
          {active ? "Engine running" : "Idle"}
        </span>
      </div>

      <ol className="mt-5 space-y-1">
        {STEP_NAMES.map((name, i) => {
          const s = rec.steps[i];
          const lit = active && i < revealed;
          const skipped = lit && s?.state === "skipped";
          return (
            <li
              key={name}
              className={`relative flex gap-3.5 rounded-kbc p-2.5 transition-[background-color,opacity] duration-300 ${lit ? (skipped ? "opacity-70" : "bg-kbc-accent-25") : "opacity-45"}`}
            >
              <span
                className={`tabular grid size-7 shrink-0 place-items-center rounded-full text-[12px] font-extrabold transition-colors duration-300 ${
                  lit ? (skipped ? "bg-kbc-night-100 text-kbc-night-300" : "bg-kbc-accent text-white") : "bg-kbc-night-25 text-kbc-night-200"
                }`}
              >
                {i + 1}
              </span>
              <div className="min-w-0">
                <p className="text-[14px] font-extrabold text-kbc-night">{name}</p>
                <p className="mt-0.5 text-[12.5px] leading-snug text-kbc-night-300">
                  {lit && s ? s.detail : "Waiting"}
                </p>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="mt-5 border-t border-kbc-night-100/70 pt-5">
        <ConfidenceGauge value={rec.confidence} active={active && revealed >= 3} />
        <p className="tabular mt-3 text-[12px] text-kbc-night-300">
          {active && weights.length ? <>= {weights.join(" + ")} (active signal weights)</> : "Sum of the weights of active signals"}
        </p>
      </div>

      <div className="mt-5 rounded-kbc bg-kbc-surface px-4 py-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.08em] text-kbc-night-300">Decision</p>
        <p className="mt-0.5 text-[15px] font-extrabold text-kbc-night">
          {active && revealed >= rec.steps.length ? VERDICT[rec.status] : "—"}
        </p>
        <p className="mt-1 text-[11.5px] leading-snug text-kbc-night-300">Rules, not a language model. Texts come from templates.</p>
      </div>
    </aside>
  );
}

// Lights the steps up one by one after activation; instant with reduced motion.
// The parent remounts this panel on every activation, so the count starts from zero.
function useRevealCount(active: boolean, total: number): number {
  const [count, setCount] = useState(() =>
    active && typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? total : 0,
  );
  useEffect(() => {
    if (!active) return;
    const id = window.setInterval(() => {
      setCount((n) => {
        if (n + 1 >= total) window.clearInterval(id);
        return Math.min(total, n + 1);
      });
    }, STEP_DELAY);
    return () => window.clearInterval(id);
  }, [active, total]);
  return active ? count : 0;
}
