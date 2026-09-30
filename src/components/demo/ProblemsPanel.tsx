import type { Persona } from "@/lib/engine";
import { CheckIcon } from "@/components/phone/icons";
import { PROBLEMS, spotlight } from "./problems";

interface ProblemsPanelProps {
  persona: Persona;
  active: boolean;
}

export function ProblemsPanel({ persona, active }: ProblemsPanelProps) {
  const spot = spotlight(persona);
  return (
    <aside aria-label={active ? "What KBC Fit changes" : "What's wrong with today's app"} className="rounded-[14px] bg-white p-6 shadow-kbc">
      <p className={`text-[12px] font-extrabold uppercase tracking-[0.08em] ${active ? "text-kbc-success-600" : "text-kbc-warning"}`}>
        {active ? "With KBC Fit" : "Today"}
      </p>
      <h2 className="mt-1 text-[20px] font-extrabold leading-tight tracking-[-0.01em] text-kbc-night">
        {active ? "What KBC Fit changes" : "What's wrong with today's app"}
      </h2>

      <div
        className={`mt-4 rounded-kbc px-4 py-3.5 transition-colors duration-300 ${active ? "bg-kbc-success-25" : "bg-kbc-warning-25"}`}
      >
        <p className={`text-[11px] font-extrabold uppercase tracking-[0.08em] ${active ? "text-kbc-success-600" : "text-[#8a4a05]"}`}>
          {active ? `For ${persona.firstName}, now` : `What ${persona.firstName} misses`}
        </p>
        <p className="mt-1 text-[13.5px] leading-snug text-kbc-night">{active ? spot.withFit : spot.today}</p>
      </div>

      <ul className="mt-4 space-y-1">
        {PROBLEMS.map((p, i) => (
          <li key={p.id} className="flex gap-3 rounded-kbc px-1 py-2">
            <StatusDot fixed={active} delay={i * 50} />
            <div className="min-w-0">
              <p className="text-[14px] font-extrabold leading-snug text-kbc-night">{active ? p.fixedTitle : p.title}</p>
              <p
                key={active ? "fit" : "today"}
                className="mt-0.5 text-[12.5px] leading-snug text-kbc-night-300 animate-fade"
                style={{ animationDelay: `${i * 50}ms` }}
              >
                {active ? p.withFit : p.today}
              </p>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

function StatusDot({ fixed, delay }: { fixed: boolean; delay: number }) {
  return (
    <span
      aria-label={fixed ? "Fixed" : "Problem"}
      role="img"
      className={`mt-0.5 grid size-6 shrink-0 place-items-center rounded-full transition-colors duration-300 ${
        fixed ? "bg-kbc-success-25 text-kbc-success" : "bg-kbc-warning-25 text-kbc-warning"
      }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {fixed ? (
        <CheckIcon className="size-3.5" strokeWidth={3} />
      ) : (
        <svg viewBox="0 0 16 16" className="size-3.5" aria-hidden>
          <path d="M8 3.5v5.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
          <circle cx="8" cy="12.3" r="1.3" fill="currentColor" />
        </svg>
      )}
    </span>
  );
}
