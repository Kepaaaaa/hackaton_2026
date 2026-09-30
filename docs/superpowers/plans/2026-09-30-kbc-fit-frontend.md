# KBC Fit front end: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A demo site where each persona's phone switches from today's generic KBC app (BEFORE) to a personalised KBC Fit screen (AFTER), driven live by a rules engine.

**Architecture:** Next.js App Router. The server page validates the persona id and passes seed data to one client component. A pure TS engine (`evaluate`) runs on the client on every interaction. Styling uses KDL tokens exposed as a Tailwind v4 theme.

**Tech Stack:** Next.js 15+, React 19, TypeScript strict, Tailwind CSS v4, Zod, Vitest, Playwright (verification).

Spec: `docs/superpowers/specs/2026-09-30-kbc-fit-frontend-design.md`. Brand: `docs/kbc-brand.md`.

---

### Task 1: Scaffold

**Files:** `package.json`, `tsconfig.json`, `next.config.ts`, `src/app/*`, `vitest.config.ts`, `.gitignore`

- [ ] `npx create-next-app@latest kbc-tmp --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --turbopack --yes`, move its content to the repo root (keep existing `README.md`, `docs/`, `public/brand/`).
- [ ] `npm i zod` and `npm i -D vitest`. Add `"test": "vitest run"` to scripts.
- [ ] `vitest.config.ts` with the `@` alias pointing to `src`.
- [ ] Add security headers in `next.config.ts`: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
- [ ] Verify: `npm run build` succeeds. Commit `chore: scaffold Next.js app`.

### Task 2: Contract + seed data

**Files:** `src/lib/engine/types.ts`, `src/lib/data/personas.ts`

- [ ] `types.ts`: exactly the contract in spec section 2 plus constants `THRESHOLD`, `ANNUAL_RATE`, `MARGIN_CAP`, `CUSHION_MONTHS`.
- [ ] `personas.ts`: the four personas. Figures:
  - Lucas 24: savings-goal, target 100000, horizon 40, currentSavings 1800, monthlyMargin 600. Signals: salary (transactions, 0.30), no pension product (products, 0.45), stable job (transactions, 0.25).
  - Thomas 31: savings-goal, target 20000, horizon 18, currentSavings 2400, monthlyMargin 400. Signals: savings pattern (transactions, 0.30), expecting a child (declared, 0.45), no long-term product (products, 0.25).
  - Monique 66: idle-cash, balance 54400, monthlyExpenses 2400, cushionMonths 6. Signals: large balance (products, 0.30), few movements (transactions, 0.45), pension income (transactions, 0.25).
  - Claire 38: none, with checks (savings invested, insurance in place, pension plan active, emergency cushion ok). Signals weights 0.30/0.45/0.25.
  - `getPersona(id)`, `PERSONA_IDS`, `personaIdSchema` (Zod enum).
- [ ] Verify: `npx tsc --noEmit`. Commit.

### Task 3: Mock engine (TDD)

**Files:** `src/lib/engine/mock.ts`, `src/lib/engine/mock.test.ts`, `src/lib/engine/index.ts`

- [ ] Write failing tests first:

```ts
import { describe, expect, it } from "vitest";
import { evaluate } from "./mock";
import { getPersona } from "@/lib/data/personas";

const on = { consent: true, disabledSignals: [] as string[] };

describe("mock engine", () => {
  it("Lucas: about €110/month, 6% if nothing changes", () => {
    const r = evaluate(getPersona("lucas"), on);
    expect(r.status).toBe("proposal");
    if (r.status !== "proposal" || r.proposal.kind !== "savings-goal") throw new Error();
    expect(r.proposal.recommendedMonthly).toBe(110);
    expect(Math.round(r.proposal.coverageIfNothing * 100)).toBe(6);
  });
  it("Thomas: about €60/month, 21%", () => {
    const r = evaluate(getPersona("thomas"), on);
    if (r.status !== "proposal" || r.proposal.kind !== "savings-goal") throw new Error();
    expect(r.proposal.recommendedMonthly).toBe(60);
    expect(Math.round(r.proposal.coverageIfNothing * 100)).toBe(21);
  });
  it("Thomas: switching off the declared situation hides the card", () => {
    const p = getPersona("thomas");
    const declared = p.signals.find((s) => s.source === "declared")!;
    expect(evaluate(p, { ...on, disabledSignals: [declared.id] }).status).toBe("low-confidence");
  });
  it("Monique: €40,000 idle, 74% inactive", () => {
    const r = evaluate(getPersona("monique"), on);
    if (r.status !== "proposal" || r.proposal.kind !== "idle-cash") throw new Error();
    expect(r.proposal.idle).toBe(40000);
    expect(r.proposal.cushion).toBe(14400);
    expect(Math.round(r.proposal.inactiveShare * 100)).toBe(74);
  });
  it("Monique: return slider changes the yearly scenario", () => {
    const r = evaluate(getPersona("monique"), { ...on, annualRateOverride: 0.02 });
    if (r.status !== "proposal" || r.proposal.kind !== "idle-cash") throw new Error();
    expect(r.proposal.yearlyGain).toBe(800);
  });
  it("Claire: nothing to suggest", () => {
    expect(evaluate(getPersona("claire"), on).status).toBe("nothing-to-suggest");
  });
  it("no consent: nothing is read", () => {
    const r = evaluate(getPersona("lucas"), { ...on, consent: false });
    expect(r.status).toBe("no-consent");
    expect(r.steps.every((s) => s.state === "skipped")).toBe(true);
  });
  it("monthly slider is clamped and moves the reach date", () => {
    const p = getPersona("lucas");
    const a = evaluate(p, { ...on, monthlyOverride: 110 });
    const b = evaluate(p, { ...on, monthlyOverride: 200 });
    const c = evaluate(p, { ...on, monthlyOverride: 99999 });
    if (a.status !== "proposal" || b.status !== "proposal" || c.status !== "proposal") throw new Error();
    if (a.proposal.kind !== "savings-goal" || b.proposal.kind !== "savings-goal" || c.proposal.kind !== "savings-goal") throw new Error();
    expect(b.proposal.reachDate < a.proposal.reachDate).toBe(true);
    expect(c.proposal.monthly).toBe(c.proposal.maxMonthly);
  });
});
```

- [ ] `npm test` fails (module missing). Implement `mock.ts` per spec section 3 (monthly rate `ANNUAL_RATE/12`, templates for title/reason/nextStep, 5 steps). `index.ts`: `export { evaluate } from "./mock"; export * from "./types";`.
- [ ] `npm test` passes. Commit `feat: mock engine with persona figures`.

### Task 4: Brand foundation

**Files:** `src/app/globals.css`, `src/app/layout.tsx`, `src/components/brand/KbcLogo.tsx`, `src/components/brand/SiteHeader.tsx`, `src/components/brand/SiteFooter.tsx`, `src/lib/format.ts`

- [ ] `globals.css`: `@theme` with every KDL colour in `docs/kbc-brand.md` (`--color-kbc-night`, `--color-kbc-accent`, …), `--font-sans` stack, radius and shadow tokens. View-transition CSS for `::view-transition-old/new(phone-screen)`, disabled under `prefers-reduced-motion`.
- [ ] `layout.tsx`: Nunito Sans via `next/font/google` (weights 300/500/700) as CSS variable; metadata; `lang="en"`.
- [ ] `KbcLogo` renders `/brand/kbc-logo.svg` with `next/image`. Header: logo + "Fit" wordmark + links. Footer: "Built for the KBC challenge at Tectonic Hackathon · 100% synthetic data".
- [ ] `format.ts`: `eur(n)` (en-BE, no decimals), `monthYear(iso)`, `pct(x)`.
- [ ] Verify: `npm run build`. Commit.

### Task 5: Persona picker `/`

**Files:** `src/app/page.tsx`, `src/components/home/PersonaCard.tsx`

- [ ] Headline "The one thing that helps. Or nothing at all.", sub-line from the pitch, four cards (initial avatar, name + age, tagline, "Open demo →") linking to `/demo/[id]`.
- [ ] Verify in browser. Commit.

### Task 6: Phone + BEFORE screen

**Files:** `src/components/phone/PhoneFrame.tsx`, `src/components/phone/BeforeScreen.tsx`, `src/components/phone/AppChrome.tsx` (status bar, navy header, tab bar)

- [ ] Phone 390×780 frame with rounded 48px bezel, screen area with `view-transition-name: phone-screen`.
- [ ] BEFORE: navy header "Good morning, {name}", account cards (label, `BE•• •••• •••• {last4}`, balance), payment card tile, two generic banners ("Dream home? Apply for a home loan", "Protect what matters: home insurance"), tab bar (Home, Pay, Products, Kate, More).
- [ ] Commit.

### Task 7: AFTER screen and cards

**Files:** `src/components/phone/AfterScreen.tsx`, `GoalCard.tsx`, `Ring.tsx`, `IdleCashCard.tsx`, `NothingCard.tsx`, `WhyThisGoal.tsx`, `ConsentToggle.tsx`, `NextStepSheet.tsx`, `Switch.tsx`

- [ ] AfterScreen: greeting + chips; card by `status` (proposal → GoalCard or IdleCashCard; nothing-to-suggest → NothingCard; low-confidence → "Not sure enough to suggest anything" note; no-consent → "Nothing is read" note); WhyThisGoal (hidden when no-consent); ConsentToggle; collapsible "My accounts"; "Back to today's app".
- [ ] GoalCard: animated SVG ring (coverage), monthly amount, reach date, range slider (step 10, 10..maxMonthly), "Without changing anything: X%", CTA opens NextStepSheet. Assumption note "3% a year, illustrative, not guaranteed".
- [ ] IdleCashCard: idle amount, cushion, inactive share bar, rate slider 0–2% (step 0.25), yearly scenario, "Prepare my appointment" CTA.
- [ ] NothingCard: success-tinted "Nothing to suggest today", expandable "See what we checked".
- [ ] NextStepSheet: bottom sheet in the phone, `role="dialog"`, Escape closes, "This is a simulation. Nothing is subscribed."
- [ ] Commit.

### Task 8: Demo page, activate panel, behind the scenes, transition

**Files:** `src/app/demo/[persona]/page.tsx`, `src/app/not-found.tsx`, `src/components/demo/DemoExperience.tsx`, `ActivatePanel.tsx`, `BehindTheScenes.tsx`, `ConfidenceGauge.tsx`

- [ ] Page: `personaIdSchema.safeParse(params.persona)` → `notFound()` on failure; `generateStaticParams` for the 4 ids.
- [ ] DemoExperience state: `active`, `consent`, `disabledSignals`, `monthly`, `rate`, `sheetOpen`. `rec = useMemo(() => evaluate(...))`. Toggle wraps state change in `document.startViewTransition` (with `flushSync`) when available and reduced motion is off.
- [ ] BehindTheScenes: steps reveal one by one (350 ms) after activation, re-render live; gauge with 60% threshold marker; idle state before activation.
- [ ] Verify: `npm run build`, `npm test`. Commit.

### Task 9: Verification

- [ ] `npx tsc --noEmit && npm run lint && npm test && npm run build`.
- [ ] Playwright: open each persona at 1440×900 and 390×844, activate, screenshot; Lucas slider; Thomas declared switch; Monique rate; Claire expand; consent off. Check no console errors.
- [ ] Fix issues, commit.
