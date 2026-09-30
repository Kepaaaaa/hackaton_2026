"use client";

interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  size?: "sm" | "md";
}

export function Switch({ checked, onChange, label, size = "md" }: SwitchProps) {
  const dims = size === "sm" ? { track: "h-6 w-10", knob: "size-5", on: "translate-x-4" } : { track: "h-7 w-12", knob: "size-6", on: "translate-x-5" };
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`press relative inline-flex shrink-0 items-center rounded-full p-0.5 transition-colors duration-200 ${dims.track} ${
        checked ? "bg-kbc-accent" : "bg-kbc-night-100"
      }`}
    >
      <span
        className={`${dims.knob} rounded-full bg-white shadow-[0_1px_3px_rgba(13,42,80,0.3)] transition-transform duration-200 ease-(--ease-out-strong) ${
          checked ? dims.on : "translate-x-0"
        }`}
      />
    </button>
  );
}
