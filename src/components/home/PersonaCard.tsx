import Image from "next/image";
import Link from "next/link";
import { PERSONA_IMAGES } from "@/lib/data/personaImages";
import type { Persona } from "@/lib/engine/types";

// The goal label speaks to the customer ("Your child's…"); the card speaks about them.
const aboutThem = (label: string) => label.replace(/^Your (\w)/, (_, c: string) => c.toUpperCase());

function teaser(p: Persona): { label: string; tone: string } {
  switch (p.scenario.kind) {
    case "savings-goal":
      return { label: aboutThem(p.scenario.goalLabel), tone: "bg-kbc-accent-100 text-kbc-accent-600" };
    case "idle-cash":
      return { label: "Money sitting idle", tone: "bg-kbc-accent-100 text-kbc-accent-600" };
    case "none":
      return { label: "Nothing to suggest", tone: "bg-kbc-success-25 text-kbc-success-600" };
  }
}

export function PersonaCard({ persona, index }: { persona: Persona; index: number }) {
  const t = teaser(persona);
  const img = PERSONA_IMAGES[persona.id];
  return (
    <Link
      href={`/demo/${persona.id}`}
      className="press group relative flex flex-col overflow-hidden rounded-kbc bg-white shadow-kbc outline-none hover:shadow-kbc-raised animate-rise"
      style={{ animationDelay: `${120 + index * 60}ms` }}
    >
      {/* The persona stands on a tint that matches their avatar tone. */}
      <div
        className="relative flex h-44 items-end justify-center overflow-hidden"
        style={{ background: `linear-gradient(180deg, ${img.tint} 0%, ${img.tint}00 100%)` }}
      >
        <Image
          src={img.figure}
          alt=""
          width={img.figureWidth}
          height={img.figureHeight}
          priority={index < 2}
          className="h-[152px] w-auto origin-bottom drop-shadow-[0_8px_12px_rgba(13,42,80,0.10)] transition-transform duration-300 ease-(--ease-out-strong) group-hover:scale-[1.06]"
        />
      </div>

      <div className="flex flex-1 flex-col gap-4 p-5">
        <div>
          <p className="text-lg font-bold leading-tight text-kbc-night">
            {persona.firstName}, {persona.age}
          </p>
          <p className="text-sm text-kbc-night-300">{persona.tagline}</p>
        </div>
        <div className="mt-auto flex items-center justify-between gap-3">
          <span className={`min-w-0 truncate rounded-kbc-sm px-2.5 py-1 text-xs font-bold ${t.tone}`}>{t.label}</span>
          <span className="flex shrink-0 items-center gap-1 whitespace-nowrap text-sm font-bold text-kbc-accent transition-transform duration-200 ease-(--ease-out-strong) group-hover:translate-x-0.5">
            Open demo
            <svg viewBox="0 0 16 16" className="size-4" aria-hidden>
              <path d="M6 3l5 5-5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
        </div>
      </div>
    </Link>
  );
}
