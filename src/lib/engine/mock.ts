// Mock engine for the front end. P1 replaces this file with the real engine;
// only `src/lib/engine/index.ts` needs to point to the new implementation.

import {
  ANNUAL_RATE,
  IDLE_RATE_DEFAULT,
  IDLE_RATE_MAX,
  IDLE_RATE_MIN,
  MARGIN_CAP,
  THRESHOLD,
  type EvalInput,
  type IdleCashProposal,
  type Persona,
  type Recommendation,
  type SavingsProposal,
  type Scenario,
  type Step,
  type StepId,
} from "./types";

const MIN_MONTHLY = 10;
const eur = (n: number) => `€${Math.round(n).toLocaleString("en-US")}`;
const pct = (x: number) => `${Math.round(x * 100)}%`;
const ceil10 = (n: number) => Math.ceil(n / 10) * 10;
const floor10 = (n: number) => Math.floor(n / 10) * 10;
const clamp = (n: number, min: number, max: number) => Math.min(max, Math.max(min, n));

const STEP_LABELS: Record<StepId, string> = {
  read: "Read",
  measure: "Measure the gap",
  decide: "Decide",
  compose: "Compose",
  explain: "Explain",
};

function step(id: StepId, detail: string, state: Step["state"] = "done"): Step {
  return { id, label: STEP_LABELS[id], detail, state };
}

function skippedSteps(detail: string): Step[] {
  return (Object.keys(STEP_LABELS) as StepId[]).map((id) => step(id, detail, "skipped"));
}

/** Value after `months` of monthly compounding, starting from `start` and adding `monthly` each month. */
function futureValue(start: number, monthly: number, months: number): number {
  const r = ANNUAL_RATE / 12;
  const growth = (1 + r) ** months;
  return start * growth + monthly * ((growth - 1) / r);
}

function reachDate(start: number, monthly: number, target: number, maxMonths: number): string | null {
  for (let m = 0; m <= maxMonths; m++) {
    if (futureValue(start, monthly, m) >= target) {
      const d = new Date();
      d.setDate(1);
      d.setMonth(d.getMonth() + m);
      return d.toISOString().slice(0, 10);
    }
  }
  return null;
}

function savingsProposal(
  s: Extract<Scenario, { kind: "savings-goal" }>,
  monthlyOverride: number | undefined,
): SavingsProposal {
  const months = s.horizonYears * 12;
  const fvNow = futureValue(s.currentSavings, 0, months);
  const annuity = futureValue(0, 1, months);
  const needed = Math.max(0, (s.target - fvNow) / annuity);
  const maxMonthly = Math.max(MIN_MONTHLY, floor10(s.monthlyMargin * MARGIN_CAP));
  const recommendedMonthly = clamp(ceil10(needed), MIN_MONTHLY, maxMonthly);
  const monthly = clamp(Math.round(monthlyOverride ?? recommendedMonthly), MIN_MONTHLY, maxMonthly);

  return {
    kind: "savings-goal",
    title: `${s.goalLabel}: ${eur(s.target)}`,
    reason: `Without changing anything, you would reach ${pct(fvNow / s.target)} of the goal. About ${eur(recommendedMonthly)} a month closes the gap and stays within ${pct(MARGIN_CAP)} of what you have left each month.`,
    nextStep: `Start ${s.product}`,
    target: s.target,
    horizonYears: s.horizonYears,
    recommendedMonthly,
    monthly,
    minMonthly: MIN_MONTHLY,
    maxMonthly,
    reachDate: reachDate(s.currentSavings, monthly, s.target, months * 2),
    coverage: Math.min(1, futureValue(s.currentSavings, monthly, months) / s.target),
    coverageIfNothing: Math.min(1, fvNow / s.target),
  };
}

function idleCashProposal(
  s: Extract<Scenario, { kind: "idle-cash" }>,
  annualRateOverride: number | undefined,
): IdleCashProposal {
  const cushion = s.monthlyExpenses * s.cushionMonths;
  const idle = Math.max(0, s.balance - cushion);
  const annualRate = clamp(annualRateOverride ?? IDLE_RATE_DEFAULT, IDLE_RATE_MIN, IDLE_RATE_MAX);

  return {
    kind: "idle-cash",
    title: `${eur(idle)} sitting idle`,
    reason: `You keep ${eur(cushion)} as a cushion (${s.cushionMonths} months of expenses). The remaining ${pct(idle / s.balance)} of your balance has not moved in months.`,
    nextStep: "Prepare my appointment",
    balance: s.balance,
    idle,
    cushion,
    inactiveShare: s.balance > 0 ? idle / s.balance : 0,
    annualRate,
    yearlyGain: Math.round(idle * annualRate),
  };
}

export function evaluate(persona: Persona, input: EvalInput): Recommendation {
  if (!input.consent) {
    return { status: "no-consent", confidence: 0, steps: skippedSteps("No consent: nothing is read") };
  }

  const active = persona.signals.filter((s) => !input.disabledSignals.includes(s.id));
  const confidence = Math.round(active.reduce((sum, s) => sum + s.weight, 0) * 100) / 100;
  const read = step("read", `${active.length} of ${persona.signals.length} signals, with your consent`);
  const s = persona.scenario;

  if (s.kind === "none") {
    return {
      status: "nothing-to-suggest",
      confidence,
      checks: s.checks,
      steps: [
        read,
        step("measure", "No gap found"),
        step("decide", "Nothing useful to propose"),
        step("compose", "Nothing to suggest today"),
        step("explain", `${s.checks.length} checks shown`),
      ],
    };
  }

  const gap =
    s.kind === "savings-goal"
      ? `${pct(Math.min(1, futureValue(s.currentSavings, 0, s.horizonYears * 12) / s.target))} of ${eur(s.target)} if nothing changes`
      : `${eur(Math.max(0, s.balance - s.monthlyExpenses * s.cushionMonths))} above the cushion`;

  if (confidence < THRESHOLD) {
    return {
      status: "low-confidence",
      confidence,
      steps: [
        read,
        step("measure", gap),
        step("decide", `Confidence ${pct(confidence)} < ${pct(THRESHOLD)}: hide the card`),
        step("compose", "Card hidden", "skipped"),
        step("explain", "Not sure enough to suggest anything", "skipped"),
      ],
    };
  }

  const proposal =
    s.kind === "savings-goal"
      ? savingsProposal(s, input.monthlyOverride)
      : idleCashProposal(s, input.annualRateOverride);

  return {
    status: "proposal",
    confidence,
    proposal,
    steps: [
      read,
      step("measure", gap),
      step("decide", `Confidence ${pct(confidence)} ≥ ${pct(THRESHOLD)}: propose`),
      step("compose", proposal.title),
      step("explain", `${active.length} signals shown, each can be switched off`),
    ],
  };
}
