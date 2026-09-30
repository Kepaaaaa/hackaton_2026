import type { Account } from "@/lib/engine/types";

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
