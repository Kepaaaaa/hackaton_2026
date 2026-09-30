"use client";

import { useEffect, useRef, useState } from "react";
import { CheckIcon } from "./icons";

export interface SheetContent {
  title: string;
  rows: { label: string; value: string }[];
  confirmLabel: string;
  doneText: string;
}

interface NextStepSheetProps {
  open: boolean;
  content: SheetContent | null;
  onClose: () => void;
}

// Bottom sheet inside the phone. Always mounted so open/close transitions can be interrupted.
export function NextStepSheet({ open, content, onClose }: NextStepSheetProps) {
  const [done, setDone] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    panelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const close = () => {
    onClose();
    setDone(false);
  };

  return (
    <div className={`absolute inset-0 z-50 ${open ? "" : "pointer-events-none"}`} inert={!open}>
      <div
        onClick={close}
        className={`absolute inset-0 bg-[rgba(13,42,80,0.4)] transition-opacity duration-300 ease-(--ease-out-strong) ${open ? "opacity-100" : "opacity-0"}`}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={content?.title ?? "Next step"}
        tabIndex={-1}
        className={`absolute inset-x-0 bottom-0 rounded-t-[22px] bg-white px-5 pb-9 pt-3 shadow-kbc-raised outline-none transition-transform duration-[420ms] ease-(--ease-drawer) ${
          open ? "translate-y-0" : "translate-y-full"
        }`}
      >
        <div className="mx-auto h-1 w-10 rounded-full bg-kbc-night-100" aria-hidden />
        {content ? (
          done ? (
            <div className="py-6 text-center animate-rise">
              <span className="mx-auto grid size-14 place-items-center rounded-full bg-kbc-success-25 text-kbc-success">
                <CheckIcon className="size-7" strokeWidth={2.4} />
              </span>
              <p className="mt-4 text-[18px] font-extrabold text-kbc-night">Simulation complete</p>
              <p className="mx-auto mt-1.5 max-w-[260px] text-[13px] leading-relaxed text-kbc-night-300">{content.doneText}</p>
              <button
                type="button"
                onClick={close}
                className="press mt-6 w-full rounded-full bg-kbc-night py-3.5 text-[15px] font-extrabold text-white"
              >
                Close
              </button>
            </div>
          ) : (
            <>
              <p className="mt-4 text-[19px] font-extrabold text-kbc-night">{content.title}</p>
              <dl className="mt-4 divide-y divide-kbc-night-100/60 rounded-kbc bg-kbc-surface px-4">
                {content.rows.map((r) => (
                  <div key={r.label} className="flex items-baseline justify-between gap-4 py-3 text-[13.5px]">
                    <dt className="text-kbc-night-300">{r.label}</dt>
                    <dd className="tabular text-right font-extrabold text-kbc-night">{r.value}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 rounded-kbc-sm bg-kbc-warning-25 px-3 py-2.5 text-[12.5px] font-bold leading-snug text-[#8a4a05]">
                This is a simulation. Nothing is subscribed.
              </p>
              <div className="mt-5 grid gap-2">
                <button
                  type="button"
                  onClick={() => setDone(true)}
                  className="press w-full rounded-full bg-kbc-accent py-3.5 text-[15px] font-extrabold text-white hover:bg-kbc-accent-600"
                >
                  {content.confirmLabel}
                </button>
                <button
                  type="button"
                  onClick={close}
                  className="press w-full rounded-full py-3 text-[14px] font-bold text-kbc-night-300 hover:bg-kbc-surface"
                >
                  Not now
                </button>
              </div>
            </>
          )
        ) : null}
      </div>
    </div>
  );
}
