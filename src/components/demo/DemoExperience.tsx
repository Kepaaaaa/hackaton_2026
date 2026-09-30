"use client";

import { startTransition, useCallback, useMemo, useState, ViewTransition } from "react";
import { AfterScreen } from "@/components/phone/AfterScreen";
import { TabBar } from "@/components/phone/AppChrome";
import { BeforeScreen } from "@/components/phone/BeforeScreen";
import { NextStepSheet, type SheetContent } from "@/components/phone/NextStepSheet";
import { PhoneFrame } from "@/components/phone/PhoneFrame";
import { evaluate, type Persona, type Proposal } from "@/lib/engine";
import { eur, monthYear, pct } from "@/lib/format";
import { ActivatePanel } from "./ActivatePanel";
import { ProblemsPanel } from "./ProblemsPanel";

interface DemoExperienceProps {
  persona: Persona;
  personas: Pick<Persona, "id" | "firstName" | "age" | "tagline">[];
}

export function DemoExperience({ persona, personas }: DemoExperienceProps) {
  const [active, setActive] = useState(false);
  const [consent, setConsent] = useState(true);
  const [disabledSignals, setDisabledSignals] = useState<string[]>([]);
  const [monthly, setMonthly] = useState<number | undefined>(undefined);
  const [rate, setRate] = useState<number | undefined>(undefined);
  const [sheetOpen, setSheetOpen] = useState(false);

  const rec = useMemo(
    () => evaluate(persona, { consent, disabledSignals, monthlyOverride: monthly, annualRateOverride: rate }),
    [persona, consent, disabledSignals, monthly, rate],
  );

  const setActiveWithTransition = useCallback((next: boolean) => {
    setSheetOpen(false);
    startTransition(() => setActive(next));
  }, []);

  const toggleSignal = useCallback((id: string, on: boolean) => {
    setDisabledSignals((d) => (on ? d.filter((x) => x !== id) : [...d, id]));
  }, []);

  const closeSheet = useCallback(() => setSheetOpen(false), []);
  const sheet = rec.status === "proposal" ? sheetFor(rec.proposal) : null;

  return (
    <div className="mx-auto grid max-w-[1320px] items-start gap-10 px-6 py-10 lg:grid-cols-[minmax(0,1fr)_384px_minmax(0,1fr)] lg:gap-12 lg:py-12">
      <div className="lg:sticky lg:top-10">
        <ActivatePanel persona={persona} personas={personas} active={active} onToggle={() => setActiveWithTransition(!active)} />
      </div>

      <div className="relative">
        <p className="mb-4 text-center text-[12px] font-extrabold uppercase tracking-[0.08em] text-kbc-night-300">
          {active ? "With KBC Fit" : "Today's app"}
        </p>
        <PhoneFrame>
          <ViewTransition key={active ? "after" : "before"} name="phone-screen" share="auto" enter="auto" default="none">
            <div className="h-full">
              {active ? (
                <AfterScreen
                  persona={persona}
                  rec={rec}
                  consent={consent}
                  disabledSignals={disabledSignals}
                  onConsent={setConsent}
                  onToggleSignal={toggleSignal}
                  onMonthly={setMonthly}
                  onRate={setRate}
                  onNextStep={() => setSheetOpen(true)}
                  onBack={() => setActiveWithTransition(false)}
                />
              ) : (
                <BeforeScreen persona={persona} />
              )}
            </div>
          </ViewTransition>
          <TabBar />
          <NextStepSheet open={sheetOpen && sheet !== null} content={sheet} onClose={closeSheet} />
        </PhoneFrame>
      </div>

      <div className="lg:sticky lg:top-10">
        <ProblemsPanel persona={persona} active={active} />
      </div>
    </div>
  );
}

function sheetFor(p: Proposal): SheetContent {
  if (p.kind === "savings-goal") {
    return {
      title: p.nextStep,
      rows: [
        { label: "Goal", value: p.title },
        { label: "Monthly amount", value: eur(p.monthly) },
        { label: "Goal reached", value: p.reachDate ? monthYear(p.reachDate) : "Beyond the horizon" },
        { label: "Assumption", value: "3% a year, not guaranteed" },
      ],
      confirmLabel: "Confirm (simulation)",
      doneText: `In the real app, this would open the ${p.nextStep.replace(/^Start |^Open /, "").toLowerCase()} flow, prefilled with ${eur(p.monthly)} a month.`,
    };
  }
  return {
    title: p.nextStep,
    rows: [
      { label: "Topic", value: `${eur(p.idle)} sitting idle` },
      { label: "Cushion kept", value: eur(p.cushion) },
      { label: "Scenario", value: `${pct(p.annualRate, 2)}: +${eur(p.yearlyGain)} a year` },
      { label: "With", value: "A KBC advisor, branch or video" },
    ],
    confirmLabel: "Request appointment (simulation)",
    doneText: "In the real app, your advisor would receive this summary before the meeting.",
  };
}
