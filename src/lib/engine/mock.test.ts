import { describe, expect, it } from "vitest";
import { evaluate } from "./mock";
import type { IdleCashProposal, Recommendation, SavingsProposal } from "./types";
import { getPersona } from "@/lib/data/personas";

const on = { consent: true, disabledSignals: [] as string[] };

function savings(r: Recommendation): SavingsProposal {
  if (r.status !== "proposal" || r.proposal.kind !== "savings-goal") throw new Error(`expected savings proposal, got ${r.status}`);
  return r.proposal;
}

function idle(r: Recommendation): IdleCashProposal {
  if (r.status !== "proposal" || r.proposal.kind !== "idle-cash") throw new Error(`expected idle-cash proposal, got ${r.status}`);
  return r.proposal;
}

describe("mock engine", () => {
  it("Lucas: about €110/month, 6% if nothing changes", () => {
    const p = savings(evaluate(getPersona("lucas"), on));
    expect(p.recommendedMonthly).toBe(110);
    expect(p.monthly).toBe(110);
    expect(Math.round(p.coverageIfNothing * 100)).toBe(6);
    expect(p.coverage).toBe(1);
  });

  it("Thomas: about €60/month, 21% if nothing changes", () => {
    const p = savings(evaluate(getPersona("thomas"), on));
    expect(p.recommendedMonthly).toBe(60);
    expect(Math.round(p.coverageIfNothing * 100)).toBe(21);
  });

  it("Thomas: switching off the declared situation hides the card", () => {
    const persona = getPersona("thomas");
    const declared = persona.signals.find((s) => s.source === "declared");
    expect(declared).toBeDefined();
    const r = evaluate(persona, { ...on, disabledSignals: [declared!.id] });
    expect(r.status).toBe("low-confidence");
    expect(r.confidence).toBeCloseTo(0.55);
  });

  it("switching off a light signal keeps the card", () => {
    const persona = getPersona("lucas");
    const r = evaluate(persona, { ...on, disabledSignals: ["lucas-margin"] });
    expect(r.status).toBe("proposal");
    expect(r.confidence).toBeCloseTo(0.75);
  });

  it("Monique: €40,000 idle above a €14,400 cushion, 74% inactive", () => {
    const p = idle(evaluate(getPersona("monique"), on));
    expect(p.idle).toBe(40_000);
    expect(p.cushion).toBe(14_400);
    expect(Math.round(p.inactiveShare * 100)).toBe(74);
    expect(p.annualRate).toBe(0.01);
    expect(p.yearlyGain).toBe(400);
  });

  it("Monique: return slider changes the yearly scenario and is clamped", () => {
    expect(idle(evaluate(getPersona("monique"), { ...on, annualRateOverride: 0.02 })).yearlyGain).toBe(800);
    expect(idle(evaluate(getPersona("monique"), { ...on, annualRateOverride: 0.5 })).annualRate).toBe(0.02);
    expect(idle(evaluate(getPersona("monique"), { ...on, annualRateOverride: -1 })).yearlyGain).toBe(0);
  });

  it("Claire: nothing to suggest, with the list of checks", () => {
    const r = evaluate(getPersona("claire"), on);
    expect(r.status).toBe("nothing-to-suggest");
    if (r.status !== "nothing-to-suggest") throw new Error();
    expect(r.checks.length).toBeGreaterThan(0);
  });

  it("no consent: nothing is read", () => {
    const r = evaluate(getPersona("lucas"), { ...on, consent: false });
    expect(r.status).toBe("no-consent");
    expect(r.confidence).toBe(0);
    expect(r.steps.every((s) => s.state === "skipped")).toBe(true);
  });

  it("always returns the five steps in order", () => {
    const r = evaluate(getPersona("monique"), on);
    expect(r.steps.map((s) => s.id)).toEqual(["read", "measure", "decide", "compose", "explain"]);
  });

  it("monthly slider moves the reach date and is clamped", () => {
    const persona = getPersona("lucas");
    const a = savings(evaluate(persona, { ...on, monthlyOverride: 110 }));
    const b = savings(evaluate(persona, { ...on, monthlyOverride: 200 }));
    const c = savings(evaluate(persona, { ...on, monthlyOverride: 99_999 }));
    const d = savings(evaluate(persona, { ...on, monthlyOverride: 20 }));
    expect(a.reachDate).not.toBeNull();
    expect(b.reachDate! < a.reachDate!).toBe(true);
    expect(c.monthly).toBe(c.maxMonthly);
    expect(c.maxMonthly).toBe(240);
    expect(d.coverage).toBeLessThan(1);
  });
});
