import { SparkIcon } from "./icons";

export function FitTag({ children = "KBC Fit" }: { children?: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-kbc-accent-100 px-2 py-0.5 text-[11px] font-extrabold uppercase tracking-[0.06em] text-kbc-accent-600">
      <SparkIcon className="size-3" strokeWidth={2.4} />
      {children}
    </span>
  );
}
