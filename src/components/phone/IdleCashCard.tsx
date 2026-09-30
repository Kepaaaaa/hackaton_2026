"use client";

import type { IdleCashProposal } from "@/lib/engine/types";
import { IDLE_RATE_MAX, IDLE_RATE_MIN } from "@/lib/engine/types";
import { eur, pct } from "@/lib/format";
import { FitTag } from "./FitTag";
import { CalendarIcon } from "./icons";
import { RangeField } from "./RangeField";

interface IdleCashCardProps {
  proposal: IdleCashProposal;
  onRate: (value: number) => void;
  onNextStep: () => void;
}

export function IdleCashCard({ proposal: p, onRate, onNextStep }: IdleCashCardProps) {
  const cushionShare = p.balance > 0 ? p.cushion / p.balance : 0;
  return (
    <article className="rounded-kbc bg-white p-5 shadow-kbc-raised">
      <FitTag>Worth a look</FitTag>
      <h2 className="mt-3 text-[20px] font-extrabold leading-tight tracking-[-0.01em] text-kbc-night">
        <span className="tabular text-kbc-accent">{eur(p.idle)}</span> sitting idle
      </h2>
      <p className="mt-1 text-[13px] text-kbc-night-300">
        <strong className="tabular text-kbc-night">{pct(p.inactiveShare)}</strong> of your current account has not moved
        in months.
      </p>

      <div className="mt-4">
        <div className="flex h-3 overflow-hidden rounded-full" role="img" aria-label={`Cushion ${eur(p.cushion)}, idle ${eur(p.idle)}`}>
          <div className="h-full bg-kbc-teal" style={{ width: pct(cushionShare) }} />
          <div className="h-full flex-1 bg-kbc-accent" />
        </div>
        <div className="mt-2.5 grid grid-cols-2 gap-3 text-[12px]">
          <div>
            <p className="flex items-center gap-1.5 font-bold text-kbc-night-300">
              <span className="size-2 rounded-full bg-kbc-teal" /> Cushion, 6 months
            </p>
            <p className="tabular text-[15px] font-extrabold text-kbc-night">{eur(p.cushion)}</p>
          </div>
          <div>
            <p className="flex items-center gap-1.5 font-bold text-kbc-night-300">
              <span className="size-2 rounded-full bg-kbc-accent" /> Idle above it
            </p>
            <p className="tabular text-[15px] font-extrabold text-kbc-night">{eur(p.idle)}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 rounded-kbc-sm bg-kbc-element p-3.5">
        <RangeField
          label="If it earned, per year"
          value={Math.round(p.annualRate * 10000) / 100}
          min={IDLE_RATE_MIN * 100}
          max={IDLE_RATE_MAX * 100}
          step={0.25}
          display={pct(p.annualRate, 2)}
          onChange={(v) => onRate(v / 100)}
          minLabel="0%"
          maxLabel="2%"
        />
        <p className="mt-2 text-[13px] text-kbc-night">
          {p.yearlyGain > 0 ? (
            <>
              About <strong className="tabular text-kbc-accent-600">+{eur(p.yearlyGain)}</strong> a year, instead of
              €0 today.
            </>
          ) : (
            <>€0 a year: what this money earns today.</>
          )}
        </p>
      </div>

      <button
        type="button"
        onClick={onNextStep}
        className="press mt-5 flex w-full items-center justify-center gap-2 rounded-full bg-kbc-accent py-3.5 text-[15px] font-extrabold text-white shadow-kbc hover:bg-kbc-accent-600"
      >
        <CalendarIcon className="size-[18px]" />
        {p.nextStep}
      </button>
      <p className="mt-2.5 text-center text-[11px] leading-snug text-kbc-night-300">
        Illustrative scenario, not a KBC rate. Any investment goes through an advisor.
      </p>
    </article>
  );
}
