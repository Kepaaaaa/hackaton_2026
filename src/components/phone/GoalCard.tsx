"use client";

import type { SavingsProposal } from "@/lib/engine/types";
import { eur, monthYear, pct } from "@/lib/format";
import { FitTag } from "./FitTag";
import { RangeField } from "./RangeField";
import { Ring } from "./Ring";

interface GoalCardProps {
  proposal: SavingsProposal;
  onMonthly: (value: number) => void;
  onNextStep: () => void;
}

export function GoalCard({ proposal: p, onMonthly, onNextStep }: GoalCardProps) {
  const horizonYear = new Date().getFullYear() + p.horizonYears;
  const reached = p.coverage >= 1;
  return (
    <article className="rounded-kbc bg-white p-5 shadow-kbc-raised">
      <div className="flex items-center justify-between">
        <FitTag>Your goal</FitTag>
        <span className="text-[12px] font-bold text-kbc-night-300">by {horizonYear}</span>
      </div>
      <h2 className="mt-3 text-[20px] font-extrabold leading-tight tracking-[-0.01em] text-kbc-night">{p.title}</h2>

      <div className="mt-4 flex items-center gap-4">
        <Ring value={p.coverage}>
          <div>
            <p className="tabular text-[26px] font-extrabold leading-none text-kbc-night">{pct(p.coverage)}</p>
            <p className="mt-1 text-[11px] font-bold text-kbc-night-300">of the goal</p>
          </div>
        </Ring>
        <div className="min-w-0">
          <p className="text-[12px] font-bold text-kbc-night-300">Put aside</p>
          <p className="tabular text-[28px] font-extrabold leading-tight text-kbc-accent">
            {eur(p.monthly)}
            <span className="text-[14px] font-bold text-kbc-night-300"> /month</span>
          </p>
          <p className="mt-1.5 text-[13px] leading-snug text-kbc-night">
            {p.reachDate ? (
              <>
                {reached ? "Goal reached in " : "Reached in "}
                <strong className="tabular">{monthYear(p.reachDate)}</strong>
              </>
            ) : (
              <>Not reached before {horizonYear + p.horizonYears}</>
            )}
          </p>
        </div>
      </div>

      <div className="mt-5">
        <RangeField
          label="Monthly amount"
          value={p.monthly}
          min={p.minMonthly}
          max={p.maxMonthly}
          step={10}
          display={eur(p.monthly)}
          onChange={onMonthly}
          minLabel={eur(p.minMonthly)}
          maxLabel={`${eur(p.maxMonthly)} max`}
        />
      </div>

      <div className="mt-4 rounded-kbc-sm bg-kbc-surface px-3.5 py-3">
        <div className="flex items-baseline justify-between text-[12.5px]">
          <span className="font-bold text-kbc-night-300">Without changing anything</span>
          <span className="tabular font-extrabold text-kbc-night">{pct(p.coverageIfNothing)}</span>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-kbc-night-100">
          <div className="h-full rounded-full bg-kbc-night-300" style={{ width: pct(p.coverageIfNothing) }} />
        </div>
      </div>

      <button
        type="button"
        onClick={onNextStep}
        className="press mt-5 w-full rounded-full bg-kbc-accent py-3.5 text-[15px] font-extrabold text-white shadow-kbc hover:bg-kbc-accent-600"
      >
        {p.nextStep}
      </button>
      <p className="mt-2.5 text-center text-[11px] leading-snug text-kbc-night-300">
        Capped at 40% of what you have left each month. 3% a year, an illustrative assumption, not guaranteed.
      </p>
    </article>
  );
}
