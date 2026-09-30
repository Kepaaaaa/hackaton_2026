import { evaluate, type Persona } from "@/lib/engine";
import { eur, pct } from "@/lib/format";

// Copy for the side panel: what is wrong with today's app, and what KBC Fit changes.

export interface Problem {
  id: string;
  title: string;
  fixedTitle: string;
  today: string;
  withFit: string;
}

export const PROBLEMS: Problem[] = [
  {
    id: "same-for-everyone",
    title: "No personalisation",
    fixedTitle: "Personalised screen",
    today: "A 24-year-old on a first salary and a retiree see the same screen and the same two banners.",
    withFit: "The screen recomposes around this customer's own situation.",
  },
  {
    id: "irrelevant-offers",
    title: "Offers that don't fit",
    fixedTitle: "Offers that fit",
    today: "A home loan and home insurance are pushed to everyone, whether they rent, own or are already insured.",
    withFit: "One suggestion, chosen from this customer's real gap.",
  },
  {
    id: "no-number",
    title: "No number, no reason",
    fixedTitle: "A number and a reason",
    today: "Banners never say how much, by when, or why this customer should care.",
    withFit: "A quantified goal, a date and the signals behind it.",
  },
  {
    id: "unused-data",
    title: "Data the bank already has, unused",
    fixedTitle: "Data put to use",
    today: "Salary, balances and products held are known to the bank, yet the screen ignores them.",
    withFit: "Signals read with consent, each one shown to the customer.",
  },
  {
    id: "missed-moments",
    title: "Gaps go unnoticed",
    fixedTitle: "Gaps raised in time",
    today: "Idle cash, a missing pension or a new child change nothing on screen. The customer has to find out alone.",
    withFit: "The gap is measured and raised at the right moment.",
  },
  {
    id: "never-says-fine",
    title: "Always something to sell",
    fixedTitle: "Honest when nothing is needed",
    today: "Even customers who need nothing get ads. That erodes trust.",
    withFit: "When nothing is useful, it says so.",
  },
  {
    id: "no-control",
    title: "No transparency, no control",
    fixedTitle: "Transparent and in control",
    today: "Customers cannot see what is used about them, or switch it off.",
    withFit: "Every signal has a switch, and consent turns everything off.",
  },
  {
    id: "does-not-scale",
    title: "Doesn't scale",
    fixedTitle: "Built to scale",
    today: "Personal suggestions are triggers built one by one. More than 140 situations, each hand-made.",
    withFit: "One rule engine, a tiny calculation per customer, ready for 2.3 million.",
  },
];

export interface Spotlight {
  today: string;
  withFit: string;
}

// What this customer misses today, with their own numbers from the engine.
export function spotlight(persona: Persona): Spotlight {
  const rec = evaluate(persona, { consent: true, disabledSignals: [] });
  const name = persona.firstName;
  const declared = persona.signals.some((s) => s.source === "declared");

  if (rec.status === "proposal" && rec.proposal.kind === "savings-goal") {
    const p = rec.proposal;
    const told = declared ? `${name} told us about a new child, and the screen did not change. ` : "";
    return {
      today: `${told}Without changing anything, ${name} reaches only ${pct(p.coverageIfNothing)} of ${eur(p.target)}. The app never says so, and shows a home loan instead.`,
      withFit: `About ${eur(p.recommendedMonthly)} a month closes the gap. ${name} sees the goal, the date and why.`,
    };
  }
  if (rec.status === "proposal" && rec.proposal.kind === "idle-cash") {
    const p = rec.proposal;
    return {
      today: `${eur(p.idle)}, ${pct(p.inactiveShare)} of ${name}'s balance, has not moved in months and earns nothing. The app never flags it.`,
      withFit: `${name} sees the idle amount above a ${eur(p.cushion)} cushion, and can prepare an advisor appointment.`,
    };
  }
  return {
    today: `${name} already saves, invests and is insured, yet still gets loan and insurance ads.`,
    withFit: `Nothing to suggest today. ${name} is told so, with the list of what was checked.`,
  };
}
