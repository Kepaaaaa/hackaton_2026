import type { ReactNode } from "react";

// iPhone-like frame. The screen is a positioned container so sheets can overlay it.
export function PhoneFrame({ children }: { children: ReactNode }) {
  return (
    <div className="relative mx-auto w-[min(384px,100%)]">
      <div className="relative rounded-[54px] bg-[#0b1522] p-[11px] shadow-phone ring-1 ring-black/40">
        <div className="pointer-events-none absolute inset-[3px] rounded-[51px] ring-1 ring-white/10" aria-hidden />
        <div className="relative h-[780px] max-h-[calc(100svh-120px)] min-h-[640px] overflow-hidden rounded-[43px] bg-kbc-surface">
          <div
            className="pointer-events-none absolute left-1/2 top-[11px] z-40 h-[30px] w-[108px] -translate-x-1/2 rounded-full bg-black"
            aria-hidden
          />
          {children}
        </div>
      </div>
    </div>
  );
}
