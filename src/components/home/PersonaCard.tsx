import Link from "next/link";
import type { Persona } from "@/lib/engine/types";
import { PersonaAvatar } from "./PersonaAvatar";

function teaser(p: Persona): { label: string; tone: string } {
  switch (p.scenario.kind) {
    case "savings-goal":
      return { label: p.scenario.goalLabel, tone: "bg-kbc-accent-100 text-kbc-accent-600" };
    case "idle-cash":
      return { label: "Money sitting idle", tone: "bg-kbc-accent-100 text-kbc-accent-600" };
    case "none":
      return { label: "Nothing to suggest", tone: "bg-kbc-success-25 text-kbc-success-600" };
  }
}

export function PersonaCard({ persona, index }: { persona: Persona; index: number }) {
  const t = teaser(persona);
  return (
    <Link
      href={`/demo/${persona.id}`}
      className="press group relative flex flex-col gap-5 rounded-kbc bg-white p-6 shadow-kbc outline-none hover:shadow-kbc-raised animate-rise"
      style={{ animationDelay: `${120 + index * 60}ms` }}
    >
      <div className="flex items-center gap-4">
        <PersonaAvatar id={persona.id} name={persona.firstName} />
        <div>
          <p className="text-lg font-bold leading-tight text-kbc-night">
            {persona.firstName}, {persona.age}
          </p>
          <p className="text-sm text-kbc-night-300">{persona.tagline}</p>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <span className={`rounded-kbc-sm px-2.5 py-1 text-xs font-bold ${t.tone}`}>{t.label}</span>
        <span className="flex items-center gap-1 text-sm font-bold text-kbc-accent transition-transform duration-200 ease-(--ease-out-strong) group-hover:translate-x-0.5">
          Open demo
          <svg viewBox="0 0 16 16" className="size-4" aria-hidden>
            <path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </div>
    </Link>
  );
}
