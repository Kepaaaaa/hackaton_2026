# KBC Fit front end: design

Scope: the P3 mission of `KBC_Context_Tectonic_Hackathon.md` (front end), plus the minimum needed to run it:
a frozen engine contract, a **mock engine** that P1 replaces, and seed data for the four personas that P2 replaces.
Out of scope: `/how-it-works` (P4), Firestore (P2), login.

Visual identity: KBC Design Language, see `docs/kbc-brand.md`.

## 1. Architecture

- Next.js App Router, React 19, strict TypeScript, Tailwind CSS v4, Zod, Vitest.
- `/demo/[persona]` is a server component: validates the id with Zod against the known ids (else `notFound()`),
  loads the persona from `lib/data`, passes it to one client component, `DemoExperience`.
- The engine is a pure function called **on the client** on every interaction (slider, switch):
  `evaluate(persona, input) => Recommendation`. Instant feedback, no network. Replacing the mock is a one-line import change.

```
src/
  app/
    layout.tsx, globals.css        fonts, KDL tokens as Tailwind theme
    page.tsx                       persona picker
    demo/[persona]/page.tsx        server: validate id, load persona
  components/
    brand/KbcLogo.tsx
    demo/DemoExperience.tsx        client: state (active, consent, disabled signals, monthly, rate) + transition
    demo/ActivatePanel.tsx         left column
    demo/BehindTheScenes.tsx       right column: 5 steps + confidence gauge (60% mark)
    phone/PhoneFrame.tsx
    phone/BeforeScreen.tsx         today's app: accounts, payment card, 2 generic banners, tab bar
    phone/AfterScreen.tsx          greeting, chips, card by status, accounts collapsed
    phone/GoalCard.tsx             ring + monthly slider (Lucas, Julie)
    phone/IdleCashCard.tsx         idle amount + return slider 0-2% (Marc)
    phone/NothingCard.tsx          "nothing to suggest" + "See what we checked" (Claire)
    phone/WhyThisGoal.tsx          signals, one switch each
    phone/ConsentToggle.tsx
    phone/NextStepSheet.tsx        bottom sheet, "simulation only"
  lib/
    engine/types.ts                FROZEN CONTRACT
    engine/mock.ts                 mock evaluate() (P1 replaces)
    engine/mock.test.ts
    engine/index.ts                re-exports evaluate from mock (the only line to change)
    data/personas.ts               seed data (P2 replaces / wraps with Firestore)
    format.ts                      EUR and date formatting (en-BE)
```

## 2. Frozen contract (`lib/engine/types.ts`)

```ts
type PersonaId = "lucas" | "julie" | "marc" | "claire";
type SignalSource = "transactions" | "products" | "declared";
interface Signal { id: string; label: string; detail: string; source: SignalSource; weight: number }
interface Account { id: string; label: string; last4: string; balance: number; kind: "current" | "savings" | "investment" | "pension" }
type Scenario =
  | { kind: "savings-goal"; goalLabel: string; target: number; horizonYears: number; currentSavings: number; monthlyMargin: number; product: string }
  | { kind: "idle-cash"; balance: number; monthlyExpenses: number; cushionMonths: number }
  | { kind: "none"; checks: string[] };
interface Persona { id: PersonaId; firstName: string; age: number; tagline: string; chips: string[]; accounts: Account[]; signals: Signal[]; scenario: Scenario }

interface EvalInput { consent: boolean; disabledSignals: string[]; monthlyOverride?: number; annualRateOverride?: number }

type StepId = "read" | "measure" | "decide" | "compose" | "explain";
interface Step { id: StepId; label: string; detail: string; state: "done" | "skipped" }

type Recommendation =
  | { status: "no-consent"; confidence: 0; steps: Step[] }
  | { status: "nothing-to-suggest"; confidence: number; steps: Step[]; checks: string[] }
  | { status: "low-confidence"; confidence: number; steps: Step[] }
  | { status: "proposal"; confidence: number; steps: Step[]; proposal: SavingsProposal | IdleCashProposal };

interface SavingsProposal { kind: "savings-goal"; title: string; reason: string; nextStep: string;
  target: number; recommendedMonthly: number; monthly: number; maxMonthly: number;
  reachDate: string /* ISO */; coverage: number /* 0..1, with monthly */; coverageIfNothing: number }
interface IdleCashProposal { kind: "idle-cash"; title: string; reason: string; nextStep: string;
  idle: number; cushion: number; inactiveShare: number; annualRate: number; yearlyGain: number }
```

Constants: `THRESHOLD = 0.6`, `ANNUAL_RATE = 0.03`, `MARGIN_CAP = 0.4`, rounding up to the next €10.

## 3. Engine rules (mock)

- No consent → `no-consent`, every step `skipped`.
- Confidence = sum of weights of enabled signals.
- Scenario `none` → `nothing-to-suggest` (whatever the confidence).
- Confidence < 0.60 → `low-confidence`.
- Savings goal, monthly compounding at 3%/12:
  `fvNow = currentSavings × (1+r)^n`, `coverageIfNothing = fvNow / target`,
  `needed = (target − fvNow) / (((1+r)^n − 1)/r)`, `recommended = min(ceil10(needed), floor10(0.4 × margin))`.
  With a slider value `monthly`: months to reach target (capped at horizon×2), `reachDate`, `coverage` at horizon (max 1).
- Idle cash: `cushion = expenses × 6`, `idle = max(0, balance − cushion)`, `inactiveShare = idle / balance`,
  `yearlyGain = idle × rate` (rate slider 0–2%, default 1%).

Expected: Lucas €110, 6%. Julie €60, 21%, and switching off the declared signal (0.45) hides the card.
Marc €40,000 idle, 74%. Claire nothing to suggest.

## 4. Screens and interactions

- `/`: KBC header, headline, four persona cards (name, age, one-line situation) linking to `/demo/[id]`.
- `/demo/[id]`: three columns on desktop (≥1024px); stacked on small screens.
  - Left: big pill "Activate KBC Fit" + one line of explanation; becomes "Deactivate KBC Fit". Links to other personas.
  - Centre: phone. BEFORE = today's generic app. AFTER = recomposed screen.
  - Right: "Behind the scenes": the 5 steps light up one by one (~350 ms apart) after activation; confidence gauge with 60% mark; updates live on every change.
- Transition: `document.startViewTransition` (cross-fade on the phone screen) when supported and `prefers-reduced-motion` is not set; otherwise instant.
- AFTER shared: consent switch (off → "Nothing is read" state), signal switches, "Back to today's app" button.
- Next step button opens a bottom sheet inside the phone: summary + "This is a simulation. Nothing is subscribed." + Close.

## 5. Error handling

- Unknown persona id → 404 page in KBC style.
- Engine is total: every input combination returns a `Recommendation`; slider values are clamped.

## 6. Verification

- Vitest: mock engine figures for the 4 personas + consent + threshold cases.
- `tsc --noEmit`, `next lint`, `next build`.
- Playwright walk-through of the 4 personas with screenshots (desktop + mobile width).
