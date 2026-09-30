import { z } from "zod";
import type { Persona, PersonaId } from "@/lib/engine/types";

// Seed data. 100% synthetic. P2 wraps this with Firestore and keeps it as the fallback.

export const PERSONA_IDS = ["lucas", "thomas", "monique", "claire"] as const satisfies readonly PersonaId[];

export const personaIdSchema = z.enum(PERSONA_IDS);

const PERSONAS: Record<PersonaId, Persona> = {
  lucas: {
    id: "lucas",
    firstName: "Lucas",
    age: 24,
    tagline: "First salary, first real savings",
    chips: ["24 years old", "Employee", "First job", "Renting"],
    accounts: [
      { id: "lucas-current", label: "KBC Current Account", last4: "4821", balance: 2340, kind: "current" },
      { id: "lucas-savings", label: "Savings Account", last4: "7730", balance: 1800, kind: "savings" },
    ],
    signals: [
      {
        id: "lucas-salary",
        label: "A salary arrives every month",
        detail: "Same employer for 7 months, €2,450 net",
        source: "transactions",
        weight: 0.3,
      },
      {
        id: "lucas-no-pension",
        label: "No supplementary pension",
        detail: "No pension savings product held",
        source: "products",
        weight: 0.45,
      },
      {
        id: "lucas-margin",
        label: "Money left at the end of the month",
        detail: "About €600 left on average after expenses",
        source: "transactions",
        weight: 0.25,
      },
    ],
    scenario: {
      kind: "savings-goal",
      goalLabel: "Retirement at 64",
      target: 100_000,
      horizonYears: 40,
      currentSavings: 1800,
      monthlyMargin: 600,
      product: "pension savings",
    },
  },
  thomas: {
    id: "thomas",
    firstName: "Thomas",
    age: 31,
    tagline: "Just became a father",
    chips: ["31 years old", "Employee", "New parent", "Homeowner"],
    accounts: [
      { id: "thomas-current", label: "KBC Current Account", last4: "1954", balance: 3120, kind: "current" },
      { id: "thomas-savings", label: "Savings Account", last4: "6602", balance: 2400, kind: "savings" },
    ],
    signals: [
      {
        id: "thomas-saves",
        label: "You already save every month",
        detail: "A monthly transfer to savings since 2024",
        source: "transactions",
        weight: 0.3,
      },
      {
        id: "thomas-declared-child",
        label: "Situation you told us about",
        detail: "You told us your first child was just born",
        source: "declared",
        weight: 0.45,
      },
      {
        id: "thomas-no-long-term",
        label: "No long-term savings",
        detail: "Only a savings account, nothing for 10+ years",
        source: "products",
        weight: 0.25,
      },
    ],
    scenario: {
      kind: "savings-goal",
      goalLabel: "Your child at 18",
      target: 20_000,
      horizonYears: 18,
      currentSavings: 2400,
      monthlyMargin: 400,
      product: "long-term savings",
    },
  },
  monique: {
    id: "monique",
    firstName: "Monique",
    age: 66,
    tagline: "Retired, cash sitting idle",
    chips: ["66 years old", "Retired", "Pension income", "Homeowner"],
    accounts: [
      { id: "monique-current", label: "KBC Current Account", last4: "3307", balance: 54_400, kind: "current" },
      { id: "monique-savings", label: "Savings Account", last4: "9115", balance: 3200, kind: "savings" },
    ],
    signals: [
      {
        id: "monique-balance",
        label: "High balance on the current account",
        detail: "€54,400, far above monthly spending",
        source: "products",
        weight: 0.3,
      },
      {
        id: "monique-few-movements",
        label: "Very few movements",
        detail: "About €2,400 spent a month, stable for 2 years",
        source: "transactions",
        weight: 0.45,
      },
      {
        id: "monique-pension",
        label: "Regular pension income",
        detail: "Pension paid every month",
        source: "transactions",
        weight: 0.25,
      },
    ],
    scenario: { kind: "idle-cash", balance: 54_400, monthlyExpenses: 2400, cushionMonths: 6 },
  },
  claire: {
    id: "claire",
    firstName: "Claire",
    age: 38,
    tagline: "Already well covered",
    chips: ["38 years old", "Self-employed", "Two children", "Homeowner"],
    accounts: [
      { id: "claire-current", label: "KBC Current Account", last4: "5540", balance: 4870, kind: "current" },
      { id: "claire-savings", label: "Savings Account", last4: "2268", balance: 18_500, kind: "savings" },
      { id: "claire-invest", label: "Investment Portfolio", last4: "8841", balance: 32_900, kind: "investment" },
      { id: "claire-pension", label: "Pension Savings", last4: "0417", balance: 21_300, kind: "pension" },
    ],
    signals: [
      {
        id: "claire-invested",
        label: "Savings are invested",
        detail: "Portfolio active, monthly plan running",
        source: "products",
        weight: 0.3,
      },
      {
        id: "claire-cushion",
        label: "Healthy emergency cushion",
        detail: "About 6 months of expenses in savings",
        source: "transactions",
        weight: 0.45,
      },
      {
        id: "claire-insured",
        label: "Home and family insured",
        detail: "Home, family and income insurance in place",
        source: "products",
        weight: 0.25,
      },
    ],
    scenario: {
      kind: "none",
      checks: [
        "Emergency cushion: 6 months of expenses, fine",
        "Pension savings: active, contributions this year",
        "Savings invested for the long term",
        "Home and family insurance in place",
        "No money sitting idle on the current account",
      ],
    },
  },
};

export function getPersona(id: PersonaId): Persona {
  return PERSONAS[id];
}

export function listPersonas(): Persona[] {
  return PERSONA_IDS.map((id) => PERSONAS[id]);
}
