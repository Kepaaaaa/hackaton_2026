import type { Account, Persona } from "@/lib/engine/types";

// One persona as exported from the synthetic bank database (datasets/export_personas.py).
// The same shape is stored in Firestore (collection `personas`) and bundled as the fallback.
export interface PersonaRecord {
  customerId: string;
  firstName: string;
  age: number;
  city: string;
  accounts: Account[];
  facts: {
    salary?: { employer: string; monthsWithEmployer: number; netMonthly: number };
    pension?: { payer: string; netMonthly: number };
    savingsOrder?: { since: string; monthly: number };
    avgMonthlyLeft?: number;
    avgMonthlySpent: number;
    avgMovementsPerMonth: number;
    cushionMonths: number;
    investmentPlanMonthly?: number;
    kbcInsurance: string[];
    heldProducts: string[];
    declared?: { situation: string; date: string };
    childBenefitSince?: string;
  };
  recentTransactions: { date: string; label: string; amount: number; category: string }[];
  transactionCount: number;
}

const eur = (x: number) => `€${Math.round(x).toLocaleString("en-US")}`;
const round = (x: number, step: number) => Math.round(x / step) * step;
const month = (ym: string) =>
  new Date(`${ym}-01T00:00:00Z`).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
const day = (iso: string) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "long", timeZone: "UTC" });

// Signal details written from the persona's real transactions and products.
function details(r: PersonaRecord): Record<string, string> {
  const f = r.facts;
  const current = r.accounts.find((a) => a.kind === "current")?.balance ?? 0;
  const invest = r.accounts.find((a) => a.kind === "investment")?.balance;
  const d: Record<string, string> = {};
  if (f.salary) d["lucas-salary"] = `Same employer for ${f.salary.monthsWithEmployer} months, ${eur(f.salary.netMonthly)} net`;
  if (!f.heldProducts.includes("pension_savings")) d["lucas-no-pension"] = "No pension savings product held";
  if (f.avgMonthlyLeft) d["lucas-margin"] = `About ${eur(round(f.avgMonthlyLeft, 50))} left on average after expenses`;
  if (f.savingsOrder)
    d["thomas-saves"] = `${eur(f.savingsOrder.monthly)} to savings every month since ${month(f.savingsOrder.since)}`;
  if (f.declared) d["thomas-declared-child"] = `You told us on ${day(f.declared.date)} that your child was born`;
  if (!f.heldProducts.includes("long_term_savings"))
    d["thomas-no-long-term"] = "Only a savings account, nothing for 10+ years";
  d["monique-balance"] = `${eur(current)}, far above the ${eur(round(f.avgMonthlySpent, 100))} spent a month`;
  d["monique-few-movements"] = `About ${eur(round(f.avgMonthlySpent, 100))} spent a month, ${f.avgMovementsPerMonth} movements a month`;
  if (f.pension) d["monique-pension"] = `${eur(f.pension.netMonthly)} paid every month by ${f.pension.payer}`;
  if (invest !== undefined)
    d["claire-invested"] = `Portfolio of ${eur(invest)}${f.investmentPlanMonthly ? `, ${eur(f.investmentPlanMonthly)} monthly plan running` : ""}`;
  d["claire-cushion"] = `About ${Math.round(f.cushionMonths)} months of expenses in savings`;
  if (f.kbcInsurance.length) d["claire-insured"] = `${f.kbcInsurance.length} KBC Insurance policies in place`;
  return d;
}

// The narrative (tagline, chips, scenario) stays in personas.ts; accounts and facts come from the database.
export function withDatabase(p: Persona, r: PersonaRecord | undefined): Persona {
  if (!r) return p;
  const d = details(r);
  const savings = r.accounts.find((a) => a.kind === "savings")?.balance;
  const current = r.accounts.find((a) => a.kind === "current")?.balance;
  const scenario =
    p.scenario.kind === "savings-goal" && savings !== undefined
      ? { ...p.scenario, currentSavings: savings }
      : p.scenario.kind === "idle-cash" && current !== undefined
        ? { ...p.scenario, balance: current }
        : p.scenario;
  return {
    ...p,
    accounts: r.accounts.map((a) => ({ ...a, id: p.accounts.find((x) => x.kind === a.kind)?.id ?? a.id })),
    signals: p.signals.map((s) => (d[s.id] ? { ...s, detail: d[s.id] } : s)),
    scenario,
  };
}
