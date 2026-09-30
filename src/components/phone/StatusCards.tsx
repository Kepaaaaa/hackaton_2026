"use client";

import { useState } from "react";
import { THRESHOLD } from "@/lib/engine/types";
import { pct } from "@/lib/format";
import { CheckIcon, ChevronIcon, LockIcon } from "./icons";

export function NothingCard({ checks }: { checks: string[] }) {
  const [open, setOpen] = useState(false);
  return (
    <article className="rounded-kbc bg-white p-5 shadow-kbc-raised">
      <span className="grid size-12 place-items-center rounded-full bg-kbc-success-25 text-kbc-success">
        <CheckIcon className="size-6" strokeWidth={2.4} />
      </span>
      <h2 className="mt-4 text-[20px] font-extrabold leading-tight tracking-[-0.01em] text-kbc-night">
        Nothing to suggest today
      </h2>
      <p className="mt-1.5 text-[14px] leading-relaxed text-kbc-night-300">
        You are well covered. We looked and found no gap, so we will not push anything. We come back only when something
        changes.
      </p>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="press mt-4 flex w-full items-center justify-between rounded-kbc-sm bg-kbc-surface px-3.5 py-3 text-[14px] font-bold text-kbc-night"
      >
        See what we checked
        <ChevronIcon className={`size-4 transition-transform duration-200 ease-(--ease-out-strong) ${open ? "rotate-90" : ""}`} />
      </button>
      {open ? (
        <ul className="mt-2 space-y-2 px-1">
          {checks.map((c, i) => (
            <li
              key={c}
              className="flex items-start gap-2.5 text-[13px] text-kbc-night animate-rise"
              style={{ animationDelay: `${i * 40}ms` }}
            >
              <CheckIcon className="mt-0.5 size-4 shrink-0 text-kbc-success" strokeWidth={2.4} />
              {c}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  );
}

export function LowConfidenceCard({ confidence }: { confidence: number }) {
  return (
    <article className="rounded-kbc border border-dashed border-kbc-night-150 bg-white/70 p-5">
      <p className="text-[16px] font-extrabold text-kbc-night">Not sure enough to suggest anything</p>
      <p className="mt-1.5 text-[13.5px] leading-relaxed text-kbc-night-300">
        With the signals you left on, our confidence is <strong className="tabular text-kbc-night">{pct(confidence)}</strong>,
        below our {pct(THRESHOLD)} threshold. So we show nothing rather than guess.
      </p>
    </article>
  );
}

export function NoConsentCard() {
  return (
    <article className="rounded-kbc border border-dashed border-kbc-night-150 bg-white/70 p-5">
      <span className="grid size-10 place-items-center rounded-full bg-kbc-night-25 text-kbc-night">
        <LockIcon className="size-5" />
      </span>
      <p className="mt-3 text-[16px] font-extrabold text-kbc-night">Nothing is read</p>
      <p className="mt-1.5 text-[13.5px] leading-relaxed text-kbc-night-300">
        Personalised suggestions are off. KBC Fit reads no signal about you and suggests nothing.
      </p>
    </article>
  );
}
