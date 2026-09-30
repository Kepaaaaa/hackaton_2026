// Frozen contract between the engine (P1), the data (P2) and the front end (P3).
// Change it only after a team sync.

export const THRESHOLD = 0.6;
export const ANNUAL_RATE = 0.03;
export const MARGIN_CAP = 0.4;
export const CUSHION_MONTHS = 6;
export const IDLE_RATE_MIN = 0;
export const IDLE_RATE_MAX = 0.02;
export const IDLE_RATE_DEFAULT = 0.01;

export type PersonaId = "lucas" | "julie" | "marc" | "claire";

export type SignalSource = "transactions" | "products" | "declared";

export interface Signal {
  id: string;
  label: string;
  detail: string;
  source: SignalSource;
  weight: number;
}

export interface Account {
  id: string;
  label: string;
  last4: string;
  balance: number;
  kind: "current" | "savings" | "investment" | "pension";
}

export type Scenario =
  | {
      kind: "savings-goal";
      goalLabel: string;
      target: number;
      horizonYears: number;
      currentSavings: number;
      monthlyMargin: number;
      product: string;
    }
  | { kind: "idle-cash"; balance: number; monthlyExpenses: number; cushionMonths: number }
  | { kind: "none"; checks: string[] };

export interface Persona {
  id: PersonaId;
  firstName: string;
  age: number;
  tagline: string;
  chips: string[];
  accounts: Account[];
  signals: Signal[];
  scenario: Scenario;
}

export interface EvalInput {
  consent: boolean;
  disabledSignals: string[];
  monthlyOverride?: number;
  annualRateOverride?: number;
}

export type StepId = "read" | "measure" | "decide" | "compose" | "explain";

export interface Step {
  id: StepId;
  label: string;
  detail: string;
  state: "done" | "skipped";
}

export interface SavingsProposal {
  kind: "savings-goal";
  title: string;
  reason: string;
  nextStep: string;
  target: number;
  horizonYears: number;
  recommendedMonthly: number;
  monthly: number;
  minMonthly: number;
  maxMonthly: number;
  /** ISO date (yyyy-mm-dd) when the target is reached at `monthly`, or null if beyond twice the horizon */
  reachDate: string | null;
  /** Share of the target reached at the horizon with `monthly`, 0..1 */
  coverage: number;
  /** Share of the target reached at the horizon if nothing changes, 0..1 */
  coverageIfNothing: number;
}

export interface IdleCashProposal {
  kind: "idle-cash";
  title: string;
  reason: string;
  nextStep: string;
  balance: number;
  idle: number;
  cushion: number;
  inactiveShare: number;
  annualRate: number;
  yearlyGain: number;
}

export type Proposal = SavingsProposal | IdleCashProposal;

export type Recommendation =
  | { status: "no-consent"; confidence: 0; steps: Step[] }
  | { status: "nothing-to-suggest"; confidence: number; steps: Step[]; checks: string[] }
  | { status: "low-confidence"; confidence: number; steps: Step[] }
  | { status: "proposal"; confidence: number; steps: Step[]; proposal: Proposal };
