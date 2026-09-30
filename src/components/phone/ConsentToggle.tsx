"use client";

import { Switch } from "./Switch";

export function ConsentToggle({ consent, onChange }: { consent: boolean; onChange: (v: boolean) => void }) {
  return (
    <section className="flex items-center gap-3 rounded-kbc bg-white p-4 shadow-kbc">
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-extrabold text-kbc-night">Personalised suggestions</p>
        <p className="mt-0.5 text-[12px] leading-snug text-kbc-night-300">
          {consent
            ? "KBC Fit may read your transactions and products. You can stop it at any time."
            : "Off. Nothing about you is read."}
        </p>
      </div>
      <Switch checked={consent} onChange={onChange} label="Allow personalised suggestions" />
    </section>
  );
}
