"use client";

import type { Persona, Recommendation } from "@/lib/engine/types";
import { AccountList } from "./AccountList";
import { AppHeader } from "./AppChrome";
import { ConsentToggle } from "./ConsentToggle";
import { GoalCard } from "./GoalCard";
import { ChevronIcon } from "./icons";
import { IdleCashCard } from "./IdleCashCard";
import { LowConfidenceCard, NoConsentCard, NothingCard } from "./StatusCards";
import { WhyThisGoal } from "./WhyThisGoal";

interface AfterScreenProps {
  persona: Persona;
  rec: Recommendation;
  consent: boolean;
  disabledSignals: string[];
  onConsent: (v: boolean) => void;
  onToggleSignal: (id: string, on: boolean) => void;
  onMonthly: (v: number) => void;
  onRate: (v: number) => void;
  onNextStep: () => void;
  onBack: () => void;
}

function subtitle(rec: Recommendation): string {
  switch (rec.status) {
    case "proposal":
      return "One thing that could help you";
    case "nothing-to-suggest":
      return "All good today";
    case "low-confidence":
      return "Nothing we are sure about today";
    case "no-consent":
      return "Personalisation is off";
  }
}

export function AfterScreen(props: AfterScreenProps) {
  const { persona, rec } = props;
  const whyTitle =
    persona.scenario.kind === "none"
      ? "What we looked at"
      : persona.scenario.kind === "idle-cash"
        ? "Why this suggestion?"
        : "Why this goal?";

  return (
    <div className="h-full overflow-y-auto pb-28 [scrollbar-width:none]">
      <AppHeader
        title={`Hi ${persona.firstName}`}
        subtitle={subtitle(rec)}
        badge={
          <span className="rounded-full bg-kbc-accent px-2.5 py-1 text-[11px] font-extrabold uppercase tracking-[0.06em]">
            Fit on
          </span>
        }
      />
      <div className="-mt-1 bg-kbc-night px-5 pb-5">
        <ul className="flex flex-wrap gap-1.5" aria-label="Your situation">
          {persona.chips.map((c) => (
            <li key={c} className="rounded-kbc-sm bg-white/10 px-2 py-1 text-[11.5px] font-bold text-white/90">
              {c}
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3 px-4 pt-4">
        <div className="animate-rise" key={rec.status}>
          <MainCard {...props} />
        </div>

        {rec.status !== "no-consent" ? (
          <div className="animate-rise" style={{ animationDelay: "60ms" }}>
            <WhyThisGoal
              title={whyTitle}
              signals={persona.signals}
              disabled={props.disabledSignals}
              confidence={rec.confidence}
              onToggle={props.onToggleSignal}
            />
          </div>
        ) : null}

        <div className="animate-rise" style={{ animationDelay: "120ms" }}>
          <ConsentToggle consent={props.consent} onChange={props.onConsent} />
        </div>

        <details className="group animate-rise rounded-kbc bg-white shadow-kbc" style={{ animationDelay: "180ms" }}>
          <summary className="flex cursor-pointer list-none items-center justify-between p-4 text-[14px] font-extrabold text-kbc-night [&::-webkit-details-marker]:hidden">
            My accounts
            <ChevronIcon className="size-4 text-kbc-night-300 transition-transform duration-200 group-open:rotate-90" />
          </summary>
          <div className="px-2 pb-2">
            <AccountList accounts={persona.accounts} />
          </div>
        </details>

        <button
          type="button"
          onClick={props.onBack}
          className="press w-full rounded-full border border-kbc-night-100 bg-white py-3 text-[13.5px] font-bold text-kbc-night-300 hover:text-kbc-night"
        >
          Back to today&apos;s app
        </button>
      </div>
    </div>
  );
}

function MainCard({ rec, persona, onMonthly, onRate, onNextStep }: AfterScreenProps) {
  switch (rec.status) {
    case "no-consent":
      return <NoConsentCard />;
    case "low-confidence":
      return <LowConfidenceCard confidence={rec.confidence} />;
    case "nothing-to-suggest":
      return <NothingCard checks={rec.checks} />;
    case "proposal":
      return rec.proposal.kind === "savings-goal" ? (
        <GoalCard proposal={rec.proposal} onMonthly={onMonthly} onNextStep={onNextStep} key={persona.id} />
      ) : (
        <IdleCashCard proposal={rec.proposal} onRate={onRate} onNextStep={onNextStep} />
      );
  }
}
