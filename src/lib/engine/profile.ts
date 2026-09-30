// Builds a customer profile (signals, scenario, chips) from one database record.
// Everything about the customer comes from the record. Only product rules live here.

import type { PersonaRecord } from "@/lib/data/fromDatabase";
import { CUSHION_MONTHS, type Persona, type PersonaId, type Scenario, type Signal } from "./types";

// Product rules: goals KBC Fit knows how to propose. Not customer data.
export const RULES = {
  retirement: { label: "Retirement at 64", target: 100_000, age: 64, product: "pension savings" },
  child: { label: "Your child at 18", target: 20_000, horizonYears: 18, product: "long-term savings" },
  idle: { minIdle: 10_000, minShare: 0.5 },
  weights: { strong: 0.45, medium: 0.3, light: 0.25 },
  wellCoveredCushionMonths: 3,
} as const;

const eur = (x: number) => `€${Math.round(x).toLocaleString("en-US")}`;
const round = (x: number, step: number) => Math.round(x / step) * step;
const monthName = (ym: string) =>
  new Date(`${ym.slice(0, 7)}-01T00:00:00Z`).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
const dayName = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "long", timeZone: "UTC" });

function balance(r: PersonaRecord, kind: string): number {
  return r.accounts.filter((a) => a.kind === kind).reduce((s, a) => s + a.balance, 0);
}

const holds = (r: PersonaRecord, product: string) => r.facts.heldProducts.includes(product);
const selfEmployed = (r: PersonaRecord) => r.recentTransactions.some((t) => t.category === "business_income");

/** Money above a cushion of CUSHION_MONTHS of spending on the current account. */
function idleCash(r: PersonaRecord): { idle: number; share: number } {
  const current = balance(r, "current");
  const idle = Math.max(0, current - r.facts.avgMonthlySpent * CUSHION_MONTHS);
  return { idle, share: current > 0 ? idle / current : 0 };
}

type Kind = "child" | "retirement" | "idle" | "none";

// Which situation the record shows, in order of priority.
function situation(r: PersonaRecord): Kind {
  const f = r.facts;
  if (f.declared?.situation === "new_child" && !holds(r, "long_term_savings")) return "child";
  if (f.salary && !holds(r, "pension_savings") && r.age < RULES.retirement.age - 10) return "retirement";
  const { idle, share } = idleCash(r);
  if (idle >= RULES.idle.minIdle && share >= RULES.idle.minShare) return "idle";
  return "none";
}

function signals(r: PersonaRecord, kind: Kind): Signal[] {
  const f = r.facts;
  const w = RULES.weights;
  const out: (Signal | false)[] = [];
  const spent = eur(round(f.avgMonthlySpent, 100));

  if (kind === "retirement") {
    out.push(
      !!f.salary && {
        id: "salary",
        label: "A salary arrives every month",
        detail: `Same employer for ${f.salary.monthsWithEmployer} months, ${eur(f.salary.netMonthly)} net`,
        source: "transactions",
        weight: w.medium,
      },
      {
        id: "no-pension",
        label: "No supplementary pension",
        detail: "No pension savings product held",
        source: "products",
        weight: w.strong,
      },
      !!f.avgMonthlyLeft &&
        f.avgMonthlyLeft > 0 && {
          id: "margin",
          label: "Money left at the end of the month",
          detail: `About ${eur(round(f.avgMonthlyLeft, 50))} left on average after expenses`,
          source: "transactions",
          weight: w.light,
        },
    );
  } else if (kind === "child") {
    out.push(
      !!f.savingsOrder && {
        id: "saves",
        label: "You already save every month",
        detail: `${eur(f.savingsOrder.monthly)} to savings every month since ${monthName(f.savingsOrder.since)}`,
        source: "transactions",
        weight: w.medium,
      },
      !!f.declared && {
        id: "declared-child",
        label: "Situation you told us about",
        detail: `You told us on ${dayName(f.declared.date)} that your child was born`,
        source: "declared",
        weight: w.strong,
      },
      {
        id: "no-long-term",
        label: "No long-term savings",
        detail: "Only a savings account, nothing for 10+ years",
        source: "products",
        weight: w.light,
      },
    );
  } else if (kind === "idle") {
    out.push(
      {
        id: "balance",
        label: "High balance on the current account",
        detail: `${eur(balance(r, "current"))}, far above the ${spent} spent a month`,
        source: "products",
        weight: w.medium,
      },
      {
        id: "few-movements",
        label: "Steady, predictable spending",
        detail: `About ${spent} spent a month, ${f.avgMovementsPerMonth} movements a month`,
        source: "transactions",
        weight: w.strong,
      },
      !!f.pension && {
        id: "pension",
        label: "Regular pension income",
        detail: `${eur(f.pension.netMonthly)} paid every month by ${f.pension.payer}`,
        source: "transactions",
        weight: w.light,
      },
    );
  } else {
    const invest = balance(r, "investment");
    out.push(
      invest > 0 && {
        id: "invested",
        label: "Savings are invested",
        detail: `Portfolio of ${eur(invest)}${f.investmentPlanMonthly ? `, ${eur(f.investmentPlanMonthly)} monthly plan running` : ""}`,
        source: "products",
        weight: w.medium,
      },
      {
        id: "cushion",
        label: "Emergency cushion in place",
        detail: `About ${f.cushionMonths.toFixed(1)} months of expenses in savings`,
        source: "transactions",
        weight: w.strong,
      },
      f.kbcInsurance.length > 0 && {
        id: "insured",
        label: "Home and family insured",
        detail: `${f.kbcInsurance.length} KBC Insurance policies in place`,
        source: "products",
        weight: w.light,
      },
    );
  }
  return out.filter((s): s is Signal => s !== false);
}

function scenario(r: PersonaRecord, kind: Kind): Scenario {
  const f = r.facts;
  const margin = Math.max(0, f.avgMonthlyLeft ?? 0);
  switch (kind) {
    case "retirement":
      return {
        kind: "savings-goal",
        goalLabel: RULES.retirement.label,
        target: RULES.retirement.target,
        horizonYears: RULES.retirement.age - r.age,
        currentSavings: balance(r, "savings"),
        monthlyMargin: margin,
        product: RULES.retirement.product,
      };
    case "child":
      return {
        kind: "savings-goal",
        goalLabel: RULES.child.label,
        target: RULES.child.target,
        horizonYears: RULES.child.horizonYears,
        currentSavings: balance(r, "savings"),
        monthlyMargin: margin,
        product: RULES.child.product,
      };
    case "idle":
      return { kind: "idle-cash", balance: balance(r, "current"), monthlyExpenses: f.avgMonthlySpent, cushionMonths: CUSHION_MONTHS };
    case "none":
      return { kind: "none", checks: checks(r) };
  }
}

// What was checked before deciding there is nothing to suggest.
function checks(r: PersonaRecord): string[] {
  const f = r.facts;
  const out: string[] = [];
  const cushionOk = f.cushionMonths >= RULES.wellCoveredCushionMonths;
  out.push(`Emergency cushion: ${f.cushionMonths.toFixed(1)} months of expenses${cushionOk ? ", fine" : ""}`);
  if (holds(r, "pension_savings")) out.push("Pension savings: active");
  if (holds(r, "long_term_savings")) out.push("Long-term savings in place");
  if (f.investmentPlanMonthly) out.push(`Investment plan running, ${eur(f.investmentPlanMonthly)} a month`);
  if (f.kbcInsurance.length) out.push(`${f.kbcInsurance.length} KBC Insurance policies in place`);
  if (idleCash(r).idle < RULES.idle.minIdle) out.push("No money sitting idle on the current account");
  return out;
}

function chips(r: PersonaRecord): string[] {
  const f = r.facts;
  const work = f.pension ? "Retired" : f.salary ? "Employee" : selfEmployed(r) ? "Self-employed" : null;
  const family = f.declared?.situation === "new_child" ? "New parent" : f.childBenefitSince ? "Parent" : null;
  const home = holds(r, "home_loan") ? "Homeowner" : holds(r, "rental_guarantee") ? "Renting" : null;
  return [`${r.age} years old`, work, family, home, r.city].filter((c): c is string => !!c);
}

function tagline(r: PersonaRecord, kind: Kind): string {
  switch (kind) {
    case "child":
      return "Just became a parent";
    case "retirement":
      return r.facts.salary && r.facts.salary.monthsWithEmployer < 12 ? "First salary, first real savings" : "Saving without a pension plan";
    case "idle":
      return r.facts.pension ? "Retired, cash sitting idle" : "Cash sitting idle";
    case "none":
      return "Already well covered";
  }
}

/** One persona, built entirely from its database record. */
export function personaFromRecord(id: PersonaId, r: PersonaRecord): Persona {
  const kind = situation(r);
  return {
    id,
    firstName: r.firstName,
    age: r.age,
    tagline: tagline(r, kind),
    chips: chips(r),
    accounts: r.accounts,
    signals: signals(r, kind),
    scenario: scenario(r, kind),
  };
}
