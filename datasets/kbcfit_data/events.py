"""Life events (ground truth) and distractors.

Each event has a `trace` level that controls how many signals it leaves in the bank and web data:
  strong  -> the full set of signals
  medium  -> most signals, weaker and with gaps
  weak    -> one or two faint signals only (paid by a partner elsewhere, second-hand, cash...)
  none    -> nothing observable at all
Distractors are real behaviours that look like a life event but are not one (grandparents buying
baby gifts, business trips, renovation, browsing a home-loan simulator without buying...).
They make a detector show false positives, which is the point: 100% detection proves nothing.

Rates are inflated compared with Belgian statistics so that each event has enough positives for ML.
"""
from datetime import date

import numpy as np

from .calendar import NDAYS, day_of, to_date
from .customers import pick

TARGET_EVENTS = ["birth", "home_purchase", "first_job", "moving_out", "cohabitation", "wedding", "car_purchase",
                 "job_loss", "new_job", "retirement", "inheritance", "separation", "child_to_higher_education"]
DISTRACTORS = ["grandchild_born", "baby_gift_friend", "business_trips", "home_browsing_only", "car_browsing_only",
               "renovation", "big_one_off_purchase"]

TRACE_MIX = {
    "birth": {"strong": .45, "medium": .30, "weak": .15, "none": .10},
    "home_purchase": {"strong": .55, "medium": .25, "weak": .12, "none": .08},
    "default": {"strong": .50, "medium": .30, "weak": .13, "none": .07},
}
DECLARE_P = {"birth": .40, "home_purchase": .30, "moving_out": .35, "cohabitation": .25, "wedding": .30,
             "job_loss": .20, "new_job": .15, "separation": .20, "retirement": .30}


def _ev(p, etype, day, rng, klass="life_event", **details):
    mix = TRACE_MIX.get(etype, TRACE_MIX["default"])
    trace = pick(rng, mix) if klass == "life_event" else "medium"
    return {"customer_idx": p["idx"], "customer_id": p["customer_id"], "event_type": etype, "day": int(day),
            "klass": klass, "trace": trace, "declared": False, "declared_day": None, "details": details}


def _declare(ev, rng, earliest, latest):
    if ev["event_type"] in DECLARE_P and ev["trace"] != "none" and rng.random() < DECLARE_P[ev["event_type"]]:
        lo, hi = max(0, earliest), min(NDAYS - 1, latest)
        if lo <= hi:
            ev["declared"] = True
            ev["declared_day"] = int(rng.integers(lo, hi + 1))


def sample_events(p: dict, rng) -> list:
    if p["demo_persona"]:
        return demo_events(p, rng)
    ev = []
    age, t = p["age_start"], p["traits"]
    emp, partner, kids = p["employment"], p["partner"], p["children"]
    working = emp in ("employee", "civil_servant", "self_employed")
    fam_age = p["gender"] != "X" and 24 <= age <= 42

    # --- first job, moving out, cohabitation --------------------------------------------------------
    first_job = None
    if emp == "student" and age >= 20 and rng.random() < 0.45:
        # most graduates start in July-October
        base = pick(rng, [day_of(date(2025, 9, 1)), day_of(date(2025, 7, 1)), day_of(date(2026, 9, 1)),
                          day_of(date(2026, 7, 1)), day_of(date(2025, 2, 1))])
        first_job = _ev(p, "first_job", base + rng.integers(0, 45), rng)
        ev.append(first_job)
    if p["housing"] == "with_parents" and 20 <= age <= 32:
        can_move = working or first_job is not None
        if can_move and rng.random() < (0.30 if first_job else 0.22):
            lo = first_job["day"] + 60 if first_job else 20
            if lo < NDAYS - 10:
                e = _ev(p, "moving_out", rng.integers(lo, NDAYS), rng)
                _declare(e, rng, e["day"] - 20, e["day"] + 30)
                ev.append(e)
    if not partner and 23 <= age <= 45 and emp != "student" and rng.random() < 0.10:
        e = _ev(p, "cohabitation", rng.integers(30, NDAYS - 10), rng)
        _declare(e, rng, e["day"] - 10, e["day"] + 40)
        ev.append(e)

    has_partner_now = partner or any(e["event_type"] == "cohabitation" for e in ev)

    # --- wedding -------------------------------------------------------------------------------------
    if partner and p["marital_status"] == "cohabiting" and 25 <= age <= 45 and rng.random() < 0.08:
        e = _ev(p, "wedding", rng.integers(120, NDAYS + 60), rng)
        _declare(e, rng, e["day"] - 30, e["day"] + 30)
        ev.append(e)

    # --- birth (pregnancy starts 280 days before) ----------------------------------------------------
    if fam_age and len(kids) < 3:
        pb = (0.22 if not kids and 26 <= age <= 37 else 0.12) if has_partner_now else 0.015
        if rng.random() < pb:
            birth = int(rng.integers(-40, NDAYS + 200))       # > NDAYS: still pregnant on END
            e = _ev(p, "birth", birth, rng, pregnancy_start_day=birth - 280)
            _declare(e, rng, birth - 280 + 84, birth - 280 + 150)   # weeks 12-21 of pregnancy
            ev.append(e)

    # --- home purchase -------------------------------------------------------------------------------
    if p["housing"] == "tenant" and 25 <= age <= 50 and working and rng.random() < (0.16 if has_partner_now else 0.08):
        deed = int(rng.integers(60, NDAYS + 120))
        price = round(float(rng.uniform(230_000, 420_000)) * (1.15 if p["region"] == "BR" else 1.0), -3)
        e = _ev(p, "home_purchase", deed, rng, price=price, compromis_day=deed - int(rng.integers(75, 120)),
                search_start_day=deed - int(rng.integers(150, 330)))
        _declare(e, rng, e["details"]["compromis_day"], deed + 30)
        ev.append(e)

    # --- car ------------------------------------------------------------------------------------------
    if 20 <= age <= 78 and emp != "student" and rng.random() < 0.10:
        price = round(float(rng.uniform(9_000, 42_000)) * (1.2 if p["income"] > 3200 else 1.0), -2)
        e = _ev(p, "car_purchase", rng.integers(30, NDAYS + 45), rng, price=price, with_loan=bool(rng.random() < 0.45),
                first_car=not p["has_car"])
        ev.append(e)

    # --- work: job loss, new job, retirement ---------------------------------------------------------
    job_loss = None
    if emp == "employee" and 23 <= age <= 62 and rng.random() < 0.045:
        job_loss = _ev(p, "job_loss", rng.integers(40, NDAYS - 30), rng, severance=bool(rng.random() < 0.5))
        _declare(job_loss, rng, job_loss["day"], job_loss["day"] + 60)
        ev.append(job_loss)
        if rng.random() < 0.55:
            e = _ev(p, "new_job", job_loss["day"] + int(rng.integers(60, 280)), rng, after_unemployment=True,
                    raise_pct=float(rng.uniform(-0.1, 0.12)))
            if e["day"] < NDAYS:
                ev.append(e)
    elif emp in ("employee", "civil_servant") and age <= 60 and rng.random() < 0.07:
        e = _ev(p, "new_job", rng.integers(30, NDAYS - 20), rng, after_unemployment=False,
                raise_pct=float(rng.uniform(0.03, 0.2)))
        _declare(e, rng, e["day"] - 10, e["day"] + 30)
        ev.append(e)
    if working and age >= 61:
        # legal age 66 (65 before 2025) or early retirement after a long career
        p_ret = 0.9 if age >= 64.5 else 0.45 if age >= 62.5 else 0.2
        if rng.random() < p_ret:
            turns_66 = day_of(date(p["birth_date"].year + 66, p["birth_date"].month, 1))
            d = min(turns_66, int(rng.integers(20, NDAYS + 200))) if age < 64 else min(turns_66, NDAYS + 60)
            d = max(d, 20)
            e = _ev(p, "retirement", d, rng, group_insurance_payout=round(float(rng.uniform(15_000, 140_000)), -2)
                    if emp == "employee" and rng.random() < 0.55 else 0.0)
            ev.append(e)

    # --- inheritance, separation, children going to higher education ---------------------------------
    if 35 <= age <= 78 and rng.random() < 0.02:
        ev.append(_ev(p, "inheritance", rng.integers(30, NDAYS - 10), rng,
                      amount=round(float(np.exp(rng.normal(np.log(60_000), 0.8))), -2)))
    if partner and 27 <= age <= 65 and rng.random() < 0.025:
        e = _ev(p, "separation", rng.integers(40, NDAYS - 20), rng)
        _declare(e, rng, e["day"], e["day"] + 60)
        ev.append(e)
    for b in kids:
        for year in (2025, 2026):
            if b.year + 18 == year and rng.random() < 0.65:
                ev.append(_ev(p, "child_to_higher_education", day_of(date(year, 9, 15)), rng,
                              student_room=bool(rng.random() < 0.45), child_birth=b.isoformat()))

    # --- distractors ---------------------------------------------------------------------------------
    if age >= 48 and (p["adult_children"] or age > 55) and rng.random() < 0.14:
        ev.append(_ev(p, "grandchild_born", rng.integers(0, NDAYS), rng, klass="distractor"))
    if 21 <= age <= 50 and rng.random() < 0.12:
        ev.append(_ev(p, "baby_gift_friend", rng.integers(0, NDAYS), rng, klass="distractor"))
    if working and p["sector"] in ("services", "ict", "finance", "industry") and rng.random() < 0.18:
        ev.append(_ev(p, "business_trips", 0, rng, klass="distractor", per_year=int(rng.integers(2, 7))))
    if p["housing"] == "tenant" and not any(e["event_type"] == "home_purchase" for e in ev) and rng.random() < 0.10:
        ev.append(_ev(p, "home_browsing_only", rng.integers(0, NDAYS - 60), rng, klass="distractor"))
    if not any(e["event_type"] == "car_purchase" for e in ev) and rng.random() < 0.07:
        ev.append(_ev(p, "car_browsing_only", rng.integers(0, NDAYS - 30), rng, klass="distractor"))
    if p["housing"] in ("owner", "owner_mortgage") and rng.random() < 0.09:
        ev.append(_ev(p, "renovation", rng.integers(0, NDAYS - 60), rng, klass="distractor",
                      budget=round(float(rng.uniform(4_000, 30_000)), -2)))
    if rng.random() < 0.06:
        ev.append(_ev(p, "big_one_off_purchase", rng.integers(0, NDAYS), rng, klass="distractor",
                      what=pick(rng, ["kitchen_appliances", "sofa", "e_bike", "laptop", "holiday_package"])))
    return ev


def demo_events(p: dict, rng) -> list:
    persona = p["demo_persona"]
    ev = []
    if persona == "lucas":
        e = _ev(p, "first_job", day_of(date(2026, 3, 1)), rng)
        e["trace"] = "strong"
        ev.append(e)
        e = _ev(p, "moving_out", day_of(date(2026, 4, 15)), rng)
        e["trace"] = "strong"
        ev.append(e)
    elif persona == "thomas":
        birth = day_of(date(2026, 8, 24))
        e = _ev(p, "birth", birth, rng, pregnancy_start_day=birth - 280)
        e.update(trace="strong", declared=True, declared_day=day_of(date(2026, 9, 2)))
        ev.append(e)
    return ev


def to_label_rows(events: list) -> list:
    rows = []
    for e in events:
        d = e["day"]
        rows.append({
            "event_id": e["event_id"], "customer_id": e["customer_id"], "event_type": e["event_type"],
            "event_class": e["klass"], "event_date": to_date(d).isoformat(),
            "status": "upcoming" if d >= NDAYS else "past",
            "trace_level": e["trace"], "declared_by_customer": e["declared"],
            "declared_date": to_date(e["declared_day"]).isoformat() if e["declared_day"] is not None else None,
            "details": ";".join(f"{k.removesuffix('_day')}={_fmt(k, v)}" for k, v in e["details"].items()),
        })
    return rows


def _fmt(key, v):
    return to_date(int(v)).isoformat() if key.endswith("_day") else v   # day indexes become dates
