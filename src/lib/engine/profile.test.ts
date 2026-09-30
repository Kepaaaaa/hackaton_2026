import { describe, expect, it } from "vitest";
import { SNAPSHOT } from "@/lib/data/personas";
import { personaFromRecord } from "./profile";
import { persona } from "./testPersonas";

describe("profile built from the database record", () => {
  it("takes name, age and accounts from the record", () => {
    const r = SNAPSHOT.records.lucas;
    const p = persona("lucas");
    expect(p.firstName).toBe(r.firstName);
    expect(p.age).toBe(r.age);
    expect(p.accounts).toEqual(r.accounts);
  });

  it("detects each customer's situation from the facts", () => {
    expect(persona("lucas").scenario).toMatchObject({ kind: "savings-goal", goalLabel: "Retirement at 64", horizonYears: 40 });
    expect(persona("thomas").scenario).toMatchObject({ kind: "savings-goal", goalLabel: "Your child at 18" });
    expect(persona("monique").scenario).toMatchObject({ kind: "idle-cash", balance: 54_400, monthlyExpenses: 2491 });
    expect(persona("claire").scenario.kind).toBe("none");
  });

  it("reads savings and monthly margin from the database", () => {
    const s = persona("lucas").scenario;
    if (s.kind !== "savings-goal") throw new Error();
    expect(s.currentSavings).toBe(1800);
    expect(s.monthlyMargin).toBe(656);
  });

  it("derives chips from facts", () => {
    expect(persona("lucas").chips).toEqual(["24 years old", "Employee", "Renting", "Gent"]);
    expect(persona("thomas").chips).toEqual(["31 years old", "Employee", "New parent", "Homeowner", "Leuven"]);
    expect(persona("monique").chips).toContain("Retired");
    expect(persona("claire").chips).toContain("Self-employed");
  });

  it("keeps the declared situation as the strongest signal", () => {
    const declared = persona("thomas").signals.find((s) => s.source === "declared");
    expect(declared?.weight).toBe(0.45);
  });

  it("drops a signal when its fact is missing", () => {
    const r = SNAPSHOT.records.lucas;
    const p = personaFromRecord("lucas", { ...r, facts: { ...r.facts, avgMonthlyLeft: undefined } });
    expect(p.signals.map((s) => s.id)).toEqual(["salary", "no-pension"]);
  });

  it("proposes nothing once the gap is closed", () => {
    const r = SNAPSHOT.records.lucas;
    const p = personaFromRecord("lucas", { ...r, facts: { ...r.facts, heldProducts: [...r.facts.heldProducts, "pension_savings"] } });
    expect(p.scenario.kind).toBe("none");
  });
});
