import Link from "next/link";
import { PersonaAvatar } from "@/components/home/PersonaAvatar";
import type { Persona } from "@/lib/engine/types";
import { SparkIcon } from "@/components/phone/icons";

interface ActivatePanelProps {
  persona: Persona;
  personas: Pick<Persona, "id" | "firstName" | "age" | "tagline">[];
  active: boolean;
  onToggle: () => void;
}

export function ActivatePanel({ persona, personas, active, onToggle }: ActivatePanelProps) {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="text-[12px] font-extrabold uppercase tracking-[0.08em] text-kbc-night-300">Customer</p>
        <div className="mt-3 flex items-center gap-3.5">
          <PersonaAvatar id={persona.id} name={persona.firstName} size="lg" />
          <div>
            <p className="text-[22px] font-extrabold leading-tight text-kbc-night">
              {persona.firstName}, {persona.age}
            </p>
            <p className="text-[14px] text-kbc-night-300">{persona.tagline}</p>
          </div>
        </div>
      </div>

      <div>
        <button
          type="button"
          onClick={onToggle}
          aria-pressed={active}
          className={`press group flex w-full items-center justify-center gap-2.5 rounded-full px-7 py-5 text-[18px] font-extrabold shadow-kbc-raised ${
            active
              ? "border-2 border-kbc-night bg-white text-kbc-night hover:bg-kbc-night-25"
              : "bg-kbc-accent text-white hover:bg-kbc-accent-600"
          }`}
        >
          <SparkIcon className={`size-5 transition-transform duration-500 ease-(--ease-out-strong) ${active ? "rotate-90" : "group-hover:rotate-45"}`} strokeWidth={2.4} />
          {active ? "Deactivate KBC Fit" : "Activate KBC Fit"}
        </button>
        <p className="mt-3 text-[14px] leading-relaxed text-kbc-night-300">
          {active
            ? "You are seeing the same customer, understood. Play with the phone: the engine reruns on every change."
            : "Today, everyone sees the same blocks. Activate to read this customer's signals, with consent, and show the one useful thing."}
        </p>
      </div>

      <nav aria-label="Other customers" className="hidden lg:block">
        <p className="text-[12px] font-extrabold uppercase tracking-[0.08em] text-kbc-night-300">Switch customer</p>
        <ul className="mt-3 grid gap-1.5">
          {personas.map((p) => {
            const current = p.id === persona.id;
            return (
              <li key={p.id}>
                <Link
                  href={`/demo/${p.id}`}
                  aria-current={current ? "page" : undefined}
                  className={`press flex items-center gap-3 rounded-kbc px-2.5 py-2 ${current ? "bg-white shadow-kbc" : "hover:bg-white/70"}`}
                >
                  <PersonaAvatar id={p.id} name={p.firstName} size="sm" />
                  <span className="min-w-0">
                    <span className="block text-[14px] font-bold text-kbc-night">
                      {p.firstName}, {p.age}
                    </span>
                    <span className="block truncate text-[12px] text-kbc-night-300">{p.tagline}</span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}
