"""Website and app navigation (clickstream) for one customer.

Sessions come from four sources, so the web data stays coherent with the bank data:
- routine use of the app (check the balance, look at transactions), more often after payday;
- transfers the customer really made (the transaction id is on the confirmation event);
- interest in a topic, driven by life events (`hints` from the bank simulation), money situations
  (idle cash, upcoming trip, tax season) and background curiosity (noise);
- product applications and "my situation" declarations that exist in the bank data.
Only customers who accepted analytics cookies are tracked.
"""
import json

import numpy as np

from . import reference as R
from .calendar import DOW, MONTH, NDAYS, to_date
from .customers import pick

PAGE = {pid: {"path": path, "section": sec, "topic": topic, "type": ptype}
        for pid, path, sec, topic, ptype in R.PAGES}
PRODUCT_PAGE = {"pension_savings": "web_pension_savings", "long_term_savings": "web_long_term_savings",
                "investment_plan": "web_invest_plan", "credit_card": "web_credit_card", "savings": "web_savings_account",
                "child_savings": "web_child_savings", "home_loan": "web_home_loan", "car_loan": "web_car_loan",
                "home_insurance": "web_home_insurance", "car_insurance": "web_car_insurance",
                "family_liability": "web_family_liability", "hospitalisation": "web_hospitalisation",
                "outstanding_balance_insurance": "web_life_insurance", "life_insurance": "web_life_insurance",
                "rental_guarantee": "life_moving"}
BACKGROUND_TOPICS = ["savings", "investing", "pension_savings", "home_loan", "car_loan", "travel", "cards",
                     "home_insurance", "car_insurance", "baby_family", "retirement", "budgeting", "help",
                     "personal_loan", "hospitalisation", "life_insurance"]
CAMPAIGNS = [("CMP-2410-SAVINGS", "Savings rates update", "savings", "2024-10-15"),
             ("CMP-2411-PENSION", "Pension savings: last weeks for your tax benefit", "pension_savings", "2024-11-20"),
             ("CMP-2503-HOME", "Home loan rates", "home_loan", "2025-03-10"),
             ("CMP-2505-TRAVEL", "Travel insurance before summer", "travel", "2025-05-20"),
             ("CMP-2509-INVEST", "Start an investment plan", "investing", "2025-09-15"),
             ("CMP-2511-PENSION", "Pension savings: last weeks for your tax benefit", "pension_savings", "2025-11-18"),
             ("CMP-2602-CAR", "Car insurance check-up", "car_insurance", "2026-02-09"),
             ("CMP-2605-TRAVEL", "Travel insurance before summer", "travel", "2026-05-19"),
             ("CMP-2609-KATE", "Ask Kate about your budget", "budgeting", "2026-09-08")]
EXPLORE_DWELL = {"landing": 25, "product": 70, "life_moment": 90, "simulator": 150, "tool": 120, "article": 80,
                 "help": 45, "form": 60, "app_screen": 20}


class WebSim:
    def __init__(self, p, sim, bank_out, rng, id_base):
        self.p, self.sim, self.rng = p, sim, rng
        self.a = p["traits"]["digital_affinity"]
        self.lang = p["language"]
        self.os = "ios_app" if rng.random() < 0.45 else "android_app"
        self.sessions, self.events, self.links = [], [], []
        self.sid, self.eid = id_base * 100_000, id_base * 1_000_000
        self.bank = bank_out

    # ------------------------------------------------------------------ helpers
    def new_session(self, day, sec, platform, source, campaign=None, authenticated=True):
        self.sid += 1
        return {"session_id": self.sid, "customer_id": self.p["customer_id"], "day": day, "sec": sec, "cursor": sec,
                "platform": platform, "traffic_source": source, "campaign_id": campaign,
                "is_authenticated": authenticated, "events": []}

    def emit(self, s, event_type, page_id, step=None, element=None, query=None, kate=None, params=None,
             tx_id=None, dwell=None, ev=0, signal=None, topic=None):
        rng = self.rng
        pg = PAGE.get(page_id, {"path": None, "section": None, "topic": topic, "type": step})
        if dwell is None:
            base = EXPLORE_DWELL.get(pg["type"], 30)
            dwell = int(max(3, base * np.exp(rng.normal(0, 0.6))))
        self.eid += 1
        e = {"event_id": self.eid, "session_id": s["session_id"], "customer_id": self.p["customer_id"],
             "ts": s["day"] * 86400 + s["cursor"], "event_type": event_type, "page_id": page_id,
             "page_path": pg["path"], "section": pg["section"], "topic": topic or pg["topic"],
             "step": step or pg["type"], "element": element, "search_query": query, "kate_intent": kate,
             "params": json.dumps(params, separators=(",", ":")) if params else None, "transaction_id": tx_id,
             "dwell_seconds": dwell}
        s["events"].append(e)
        s["cursor"] += dwell + int(rng.integers(1, 6))
        if ev:
            self.links.append({"event_id": ev, "web_event_id": self.eid, "signal": signal or "topic_interest"})
        return e

    def close(self, s):
        if not s["events"] or s["day"] < 0 or s["day"] >= NDAYS:
            self.eid -= 0
            return
        first, last = s["events"][0], s["events"][-1]
        self.sessions.append({
            "session_id": s["session_id"], "customer_id": s["customer_id"],
            "start_ts": first["ts"], "end_ts": last["ts"] + last["dwell_seconds"],
            "duration_seconds": last["ts"] + last["dwell_seconds"] - first["ts"], "platform": s["platform"],
            "is_authenticated": s["is_authenticated"], "traffic_source": s["traffic_source"],
            "campaign_id": s["campaign_id"], "entry_page": first["page_id"], "exit_page": last["page_id"],
            "n_events": len(s["events"]), "language": self.lang})
        self.events.extend(s["events"])

    def session_sec(self):
        h = pick(self.rng, {7.8: .22, 12.5: .2, 17.5: .15, 20.5: .33, 22.5: .1})
        return int(np.clip(self.rng.normal(h, 0.9), 0.2, 23.8) * 3600)

    def platform(self, explore=False):
        r = self.rng.random()
        if explore:
            return "web_desktop" if r < 0.45 else self.os if r < 0.8 else "web_mobile"
        return self.os if r < 0.85 or self.a > 0.6 else "web_desktop"

    # ------------------------------------------------------------------ interest model
    def build_interest(self):
        p, sim, rng = self.p, self.sim, self.rng
        comps = []                  # (topic, start, end, weight, event_id, params, ramp)
        for topic, a, b, w, ev, params in sim.hints:
            comps.append((topic, a, b, w, ev, params, True))
        for topic in rng.choice(BACKGROUND_TOPICS, size=3, replace=False):
            comps.append((str(topic), 0, NDAYS, float(rng.uniform(0.01, 0.05)), 0, {}, False))
        age = p["age_start"]
        if 25 <= age <= 58 and "pension_savings" not in sim.accounts and p["employment"] != "student":
            comps.append(("pension_savings", 0, NDAYS, 0.03, 0, {}, False))
        for k, (y, m) in enumerate([(2025, 5), (2026, 5)]):
            a = (to_date(0).replace(year=y, month=m, day=1) - to_date(0)).days
            comps.append(("tax", a, a + 75, 0.08, 0, {}, False))
        # idle cash: current balance far above 6 months of spending
        for m_end, cur_bal, spend in self.bank["idle_months"]:
            if cur_bal > 6 * spend + 10_000:
                comps.append(("investing", m_end, m_end + 31, min(0.2, cur_bal / 600_000), 0, {}, False))
        for start, book in self.bank["trips"]:
            comps.append(("travel", book - 5, start, 0.25, 0, {}, False))
        self.comps = comps

    def interest_at(self, d):
        out = []
        for c in self.comps:
            topic, a, b, w, ev, params, ramp = c
            if a <= d < b:
                x = w * (0.35 + 0.65 * (d - a) / max(1, b - a)) if ramp else w
                out.append((x, c))
        return out

    # ------------------------------------------------------------------ session types
    def balance_session(self, d, sec, source="app_launch"):
        rng = self.rng
        s = self.new_session(d, sec, self.platform(), source)
        self.emit(s, "page_view", "app_home", dwell=int(rng.integers(3, 15)))
        self.banner(s, d)
        if rng.random() < 0.75:
            self.emit(s, "page_view", "app_accounts", dwell=int(rng.integers(4, 25)))
            if rng.random() < 0.55:
                self.emit(s, "page_view", "app_transactions", dwell=int(rng.integers(8, 60)))
                if rng.random() < 0.2:
                    self.emit(s, "page_view", "app_tx_detail", dwell=int(rng.integers(5, 30)))
        extra = rng.random()
        if extra < 0.06 and "savings" in self.sim.accounts:
            self.emit(s, "page_view", "app_savings")
        elif extra < 0.10 and "investment_plan" in self.sim.accounts:
            self.emit(s, "page_view", "app_investments")
            if rng.random() < 0.3:
                self.emit(s, "page_view", "app_fund_detail")
        elif extra < 0.13:
            self.emit(s, "page_view", "app_cards")
        elif extra < 0.16:
            self.emit(s, "page_view", "app_budget")
        elif extra < 0.19 and self.p["city"] in ("Antwerpen", "Gent", "Brussel", "Leuven", "Liège", "Mechelen"):
            self.emit(s, "page_view", pick(rng, ["app_mobility_parking", "app_mobility_ticket"]))
        elif extra < 0.21:
            self.emit(s, "page_view", "app_documents")
        elif extra < 0.235:
            self.emit(s, "page_view", "app_kate")
            self.emit(s, "kate_message", "app_kate", step="kate",
                      kate=pick(rng, R.KATE_INTENTS["daily_banking"] + R.KATE_INTENTS["budgeting"]))
        elif extra < 0.25:
            self.emit(s, "page_view", "app_offers")
        self.close(s)

    def banner(self, s, d):
        rng = self.rng
        bid, btopic = R.GENERIC_BANNERS[rng.integers(len(R.GENERIC_BANNERS))]
        self.emit(s, "offer_impression", "app_home", element=bid, dwell=0, topic=btopic)
        active = sum(x for x, c in self.interest_at(d) if c[0] == btopic)
        p_click = 0.004 + 0.12 * min(1.0, active)
        r = rng.random()
        if r < p_click:
            self.emit(s, "offer_click", "app_home", element=bid, dwell=1, topic=btopic)
            funnel = R.TOPIC_FUNNELS.get(btopic, [])
            if funnel:
                self.emit(s, "page_view", funnel[0])
        elif r < p_click + 0.04:
            self.emit(s, "offer_dismiss", "app_home", element=bid, dwell=1, topic=btopic)

    def transfer_session(self, d, sec, tx_id):
        rng = self.rng
        s = self.new_session(d, max(0, sec - int(rng.integers(40, 240))), self.platform(), "app_launch")
        self.emit(s, "page_view", "app_home", dwell=int(rng.integers(2, 8)))
        if rng.random() < 0.3:
            self.emit(s, "page_view", "app_accounts", dwell=int(rng.integers(3, 12)))
        self.emit(s, "page_view", "app_transfer", dwell=int(rng.integers(20, 70)))
        self.emit(s, "transfer_confirmed", "app_transfer_confirm", element="confirm_button", tx_id=tx_id,
                  dwell=int(rng.integers(3, 10)))
        self.close(s)

    def explore_session(self, d, sec, comp, source=None, campaign=None):
        rng, lang = self.rng, self.lang
        topic, a, b, w, ev, params, ramp = comp
        intensity = min(1.0, w * 1.5)
        source = source or pick(rng, {"search_engine": .40, "direct": .30, "app_launch": .20, "social": .05,
                                      "display_ad": .05})
        platform = self.os if source == "app_launch" else self.platform(explore=True)
        s = self.new_session(d, sec, platform, source, campaign,
                             authenticated=source == "app_launch" or rng.random() < 0.35)
        funnel = R.TOPIC_FUNNELS.get(topic, ["web_home"])
        sig = f"{topic}_interest"
        if source == "direct":
            self.emit(s, "page_view", "web_home", ev=ev, signal=sig)
        if rng.random() < 0.22 + 0.2 * intensity and topic in R.SEARCH_QUERIES:
            qs = R.SEARCH_QUERIES[topic].get(lang) or R.SEARCH_QUERIES[topic]["en"]
            self.emit(s, "search", "web_home", step="search", query=pick(rng, qs), topic=topic, dwell=int(rng.integers(5, 20)),
                      ev=ev, signal=sig)
        depth = 1 + rng.binomial(len(funnel) - 1, min(0.9, 0.25 + 0.55 * intensity)) if len(funnel) > 1 else 1
        for pid in funnel[:depth]:
            self.emit(s, "page_view", pid, ev=ev, signal=sig)
            if PAGE[pid]["type"] == "product" and rng.random() < 0.3:
                self.emit(s, "click", pid, element="cta_more_info", dwell=2, ev=ev, signal=sig)
        sim_page = R.TOPIC_SIMULATOR.get(topic)
        if sim_page and rng.random() < 0.12 + 0.55 * intensity:
            prm = {}
            if "loan_amount" in params:
                prm["amount"] = round(params["loan_amount"] * float(rng.uniform(0.85, 1.15)), -3)
                prm["duration_years"] = int(pick(rng, [20, 25, 25, 30])) if topic == "home_loan" else int(pick(rng, [3, 4, 5]))
            elif topic in ("pension_savings", "retirement", "savings", "child_savings"):
                prm["monthly_amount"] = float(pick(rng, [25, 50, 87.5, 100, 150]))
            self.emit(s, "simulator_start", sim_page, step="simulator", ev=ev, signal="simulator_use")
            if rng.random() < 0.65:
                self.emit(s, "simulator_submit", sim_page, step="simulator", params=prm or None, ev=ev,
                          signal="simulator_use")
        if topic in ("home_loan", "investing", "retirement", "inheritance", "car_loan") and rng.random() < 0.08 * intensity + 0.005:
            self.emit(s, "page_view", "appointment_book", ev=ev, signal="appointment")
            self.emit(s, "form_start", "appointment_book", step="form", ev=ev, signal="appointment")
            if rng.random() < 0.6:
                self.emit(s, "appointment_booked", "appointment_confirm", step="form",
                          params={"topic": topic, "channel": pick(rng, ["branch", "video", "phone"])}, ev=ev,
                          signal="appointment")
        if topic in R.KATE_INTENTS and source == "app_launch" and rng.random() < 0.15:
            self.emit(s, "page_view", "app_kate")
            self.emit(s, "kate_message", "app_kate", step="kate", kate=pick(rng, R.KATE_INTENTS[topic]), topic=topic,
                      ev=ev, signal="kate_question")
        self.close(s)

    def application_session(self, d, product, ev):
        rng = self.rng
        page = PRODUCT_PAGE.get(product)
        if not page:
            return
        if rng.random() < 0.6:
            dd = d - int(rng.integers(1, 15))
            if dd >= 0:
                self.explore_session(dd, self.session_sec(), (PAGE[page]["topic"], 0, 1, 0.5, ev, {}, False))
        s = self.new_session(d, self.session_sec(), self.platform(explore=True), "direct")
        self.emit(s, "page_view", page, ev=ev, signal="application")
        self.emit(s, "form_start", "apply_start", step="form", params={"product": product}, ev=ev, signal="application")
        self.emit(s, "application_submitted", "apply_done", step="form", params={"product": product}, ev=ev,
                  signal="application")
        self.close(s)

    def declaration_session(self, d, situation, ev):
        rng = self.rng
        s = self.new_session(d, self.session_sec(), self.os, "app_launch")
        self.emit(s, "page_view", "app_home", dwell=int(rng.integers(2, 8)))
        self.emit(s, "page_view", "app_settings_profile")
        self.emit(s, "page_view", "app_situation", ev=ev, signal="declaration")
        self.emit(s, "form_submit", "app_situation", step="form", params={"situation": situation}, ev=ev,
                  signal="declaration")
        self.close(s)

    # ------------------------------------------------------------------ run
    def run(self):
        p, rng = self.p, self.rng
        if not p["consent_analytics"] or self.a <= 0:
            return [], [], []
        self.build_interest()
        a = self.a
        base = 0.03 + 0.85 * a ** 2
        payday = np.zeros(NDAYS)
        for d in self.bank["income_days"]:
            payday[d:d + 2] += 1.0
        explore_base = 0.035 + 0.04 * a
        for d in range(NDAYS):
            rate = base * (1.1 if DOW[d] < 5 else 0.85) * (1 + 0.8 * min(payday[d], 1))
            for _ in range(rng.poisson(rate)):
                self.balance_session(d, self.session_sec())
            interest = self.interest_at(d)
            total = sum(x for x, _ in interest)
            n_explore = rng.poisson(explore_base * (0.4 + 1.8 * total) * (0.5 + a))
            for _ in range(n_explore):
                weights = np.array([x for x, _ in interest])
                comp = interest[rng.choice(len(interest), p=weights / weights.sum())][1]
                self.explore_session(d, self.session_sec(), comp)
        # transfers the customer made in the app
        for d, sec, tx_id in self.bank["transfers"]:
            if rng.random() < 0.3 + 0.65 * a:
                self.transfer_session(d, sec, tx_id)
        for d, product, ev in self.sim.openings:
            if 0 <= d < NDAYS and rng.random() < 0.3 + 0.6 * a:
                self.application_session(d, product, ev)
        for d, situation, ev in self.sim.declared:
            if d is not None and 0 <= d < NDAYS:
                self.declaration_session(d, situation, ev)
        if p["consent_marketing"]:
            for cid, _, topic, day in CAMPAIGNS:
                d = (to_date(0).fromisoformat(day) - to_date(0)).days
                active = sum(x for x, c in self.interest_at(d) if c[0] == topic)
                if rng.random() < 0.015 + 0.25 * min(1, active):
                    dd = d + int(rng.integers(0, 4))
                    if dd < NDAYS:
                        ev = next((c[4] for x, c in self.interest_at(d) if c[0] == topic and c[4]), 0)
                        self.explore_session(dd, self.session_sec(), (topic, 0, 1, 0.3 + active, ev, {}, False),
                                             source="email", campaign=cid)
        return self.sessions, self.events, self.links


def campaign_rows():
    return [{"campaign_id": c, "name": n, "topic": t, "send_date": d, "channel": "email"} for c, n, t, d in CAMPAIGNS]


def page_rows():
    return [{"page_id": pid, "path": path, "section": sec, "topic": topic, "page_type": ptype}
            for pid, path, sec, topic, ptype in R.PAGES]
