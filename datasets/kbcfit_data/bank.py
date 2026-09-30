"""Bank simulation for one customer: accounts, insurance contracts and every transaction.

Design rules
- Every euro has a reason: income streams, housing, bills, children, events, trips and day-to-day spending.
- Spending is calibrated on the customer's income so balances stay plausible, and savings absorb shocks.
- A life event changes the streams (salary stops, rent stops, child benefit starts...) and the spending
  mix (baby shops, DIY...). Its `trace` level scales these signals; `none` leaves nothing behind.
- Rows caused by an event carry its id in `event_id` / `signal`. Those two columns go to the labels
  database only, never to the bank database.
"""
from collections import defaultdict

import numpy as np

from . import reference as R
from .calendar import (DOW, EPOCH0, IS_BUSINESS, MONTH, MONTHS, NDAYS, SCHOOL_HOLIDAY, YEAR, business_on_or_after,
                       business_on_or_before, to_date)
from .customers import OTHER_BANKS, new_employer, pick
from .merchants import registry

TRACE_I = {"strong": 1.0, "medium": 0.6, "weak": 0.25, "none": 0.0}
FAR = 10 ** 6

# category: (purchases per month, mean amount EUR, lognormal sigma)
SPEND = {
    "groceries": (7.0, 42, 0.65), "bakery": (3.0, 9, 0.5), "drugstore": (1.3, 21, 0.6), "pharmacy": (0.7, 19, 0.7),
    "restaurant": (1.2, 58, 0.55), "cafe_bar": (2.2, 17, 0.6), "fast_food": (1.3, 16, 0.45),
    "food_delivery": (0.9, 29, 0.4), "clothing": (0.9, 58, 0.7), "electronics": (0.12, 160, 1.0),
    "diy_garden": (0.45, 48, 0.9), "furniture": (0.07, 230, 0.9), "discount_store": (0.9, 19, 0.6),
    "marketplace": (1.0, 34, 0.8), "secondhand": (0.2, 22, 0.6), "books_news": (0.5, 14, 0.6),
    "sports": (0.25, 55, 0.8), "entertainment": (0.45, 36, 0.6), "public_transport": (0.8, 11, 0.7),
    "taxi_mobility": (0.25, 17, 0.5), "fuel": (2.3, 62, 0.3), "parking": (1.0, 4.5, 0.6),
    "hair_beauty": (0.55, 38, 0.5), "medical": (0.35, 33, 0.3), "dentist": (0.08, 70, 0.6), "pets": (0.8, 28, 0.6),
    "vet": (0.1, 75, 0.7), "baby": (0.0, 42, 0.8), "toys": (0.12, 29, 0.7), "gifts_flowers": (0.28, 32, 0.6),
    "jewelry": (0.02, 120, 0.8), "lottery": (1.5, 8, 0.4), "atm": (1.3, 70, 0.5), "p2p_out": (1.2, 25, 0.8),
    "p2p_in": (0.6, 30, 0.8),
}
LOCAL_CATS = {"bakery": .85, "restaurant": .8, "cafe_bar": .8, "fast_food": .6, "pharmacy": .8, "hair_beauty": 1.0,
              "medical": 1.0, "dentist": 1.0, "vet": 1.0, "gifts_flowers": .7, "jewelry": .8}
AWAY_CATS = {"groceries", "bakery", "restaurant", "cafe_bar", "fast_food", "food_delivery", "public_transport",
             "parking", "fuel", "hair_beauty", "medical", "pets", "atm", "p2p_out"}
_DOW_W = {}
for _cat, (_, _w) in R.CATEGORY_TIME.items():
    _w = np.array(_w, dtype=float)
    _DOW_W[_cat] = _w / _w.mean()
COMMUNICATIONS = ["restaurant", "tickets", "cadeau", "weekend", "pizza", "concert", "terug", "merci", "voetbal",
                  "loyer garage", "benzine", "cinema", "verjaardag", "anniversaire", "vakantie", "courses"]
FIRST_NAMES_ALL = sorted({n for names in R.FIRST_NAMES.values() for n in names})


def _month_k(y, m):
    return next((i for i, mm in enumerate(MONTHS) if mm[0] == y and mm[1] == m), None)


def structured_comm(rng):
    n = int(rng.integers(10 ** 9, 10 ** 10))
    c = n % 97 or 97
    s = f"{n:010d}{c:02d}"
    return f"+++{s[:3]}/{s[3:7]}/{s[7:]}+++"


class Ledger:
    COLS = ("account", "day", "sec", "amount", "category", "channel", "counterparty", "cp_type", "description",
            "merchant_id", "city", "country", "event_id", "signal", "recurring", "orig_currency", "orig_amount")

    def __init__(self):
        self.c = {k: [] for k in self.COLS}

    def add(self, account, day, sec, amount, category, channel, counterparty, cp_type, description,
            merchant_id=0, city=None, country="BE", event_id=0, signal=None, recurring=False,
            orig_currency=None, orig_amount=None):
        day = int(day)
        if day < 0 or day >= NDAYS or amount == 0:
            return
        c = self.c
        c["account"].append(account); c["day"].append(day); c["sec"].append(int(sec))
        c["amount"].append(round(float(amount), 2)); c["category"].append(category); c["channel"].append(channel)
        c["counterparty"].append(counterparty); c["cp_type"].append(cp_type); c["description"].append(description)
        c["merchant_id"].append(int(merchant_id)); c["city"].append(city); c["country"].append(country)
        c["event_id"].append(int(event_id)); c["signal"].append(signal); c["recurring"].append(bool(recurring))
        c["orig_currency"].append(orig_currency); c["orig_amount"].append(orig_amount)


class CustomerSim:
    def __init__(self, p, events, rng):
        self.p, self.t, self.rng, self.M = p, p["traits"], rng, registry()
        self.events = sorted(events, key=lambda e: e["day"])
        self.L = Ledger()
        self.region = p["region"]
        self.mult = defaultdict(lambda: np.ones(NDAYS))
        self.mult_ev = defaultdict(lambda: np.zeros(NDAYS, dtype=np.int64))
        self.extra = defaultdict(lambda: np.zeros(NDAYS))
        self.extra_ev = defaultdict(lambda: np.zeros(NDAYS, dtype=np.int64))
        self.spend_level = np.ones(NDAYS)
        self.away = np.zeros(NDAYS, dtype=bool)
        self.no_trip = np.zeros(NDAYS, dtype=bool)
        self.fund_needs = np.zeros(NDAYS)
        self.accounts = {}
        self.contracts = []
        self.openings = []          # (day, product, event_id) for the web simulation
        self.hints = []             # (topic, start, end, weight, event_id, params)
        self.external = []          # insurance or loans held outside KBC (latent truth)
        self.declared = []
        self.friends = [f"{pick(rng, FIRST_NAMES_ALL)} {pick(rng, R.LAST_NAMES['nl' if p['language'] == 'nl' else 'fr'])}"
                        for _ in range(8)]
        self.parent_name = f"{pick(rng, ['J.', 'M.', 'P.', 'A.', 'L.'])} {p['last_name']}"
        self.partner_name = (f"{pick(rng, FIRST_NAMES_ALL)} {pick(rng, R.LAST_NAMES['nl' if p['language'] == 'nl' else 'fr'])}")
        self.car_from = -FAR if p["has_car"] else FAR
        self.kids = []              # [birth_day, visible_benefit, event_id]
        for b in p["children"]:
            self.kids.append([(b - to_date(0)).days, rng.random() < 0.6, 0])
        self.hh_adults = 1 + int(p["partner"])
        self.partner_from, self.partner_to = (-FAR, FAR) if p["partner"] else (FAR, FAR)
        arr = pick(rng, {"pays_all": .45, "split": .40, "partner_pays_most": .15}) if p["partner"] else "alone"
        self.arrangement = arr
        self.share = {"pays_all": 1.0, "split": 0.5, "partner_pays_most": 0.3, "alone": 1.0}[arr]
        self.city = p["city"]
        self.sec_base = int(rng.integers(0, 3600))
        self.salary_dom = pick(rng, {"last": .7, 25: .15, 1: .15})
        self.pay_account_fee = float(pick(rng, [2.95, 3.10, 3.10, 4.95, 5.20]))
        self.targets = p.get("demo_targets")
        self.demo = p["demo_persona"]

    # ------------------------------------------------------------------ helpers
    def rsec(self, mean_h=12.0, sd=3.0, lo=6.0, hi=23.9):
        h = float(np.clip(self.rng.normal(mean_h, sd), lo, hi))
        return int(h * 3600 + self.rng.integers(0, 60))

    def boost(self, cat, a, b, factor, ev_id=0):
        a, b = max(0, int(a)), min(NDAYS, int(b))
        if a >= b:
            return
        self.mult[cat][a:b] *= factor
        if ev_id and factor > 1:
            self.mult_ev[cat][a:b] = ev_id

    def add_rate(self, cat, a, b, per_month, ev_id=0):
        a, b = max(0, int(a)), min(NDAYS, int(b))
        if a >= b or per_month <= 0:
            return
        self.extra[cat][a:b] += per_month / 30.44
        if ev_id:
            self.extra_ev[cat][a:b] = ev_id

    def hint(self, topic, a, b, weight, ev_id=0, **params):
        if weight > 0 and b > 0 and a < NDAYS:
            self.hints.append((topic, int(a), int(b), float(weight), int(ev_id), params))

    def open_account(self, key, day, provider="KBC", opening=0.0, event_id=0, product_name=None):
        if key in self.accounts:
            return
        self.accounts[key] = {"opened_day": int(day), "provider": provider, "opening": float(opening),
                              "event_id": event_id, "product_name": product_name,
                              "last4": f"{self.rng.integers(0, 10000):04d}"}
        if 0 <= day < NDAYS:
            self.openings.append((int(day), key, event_id))

    def merchant(self, cat, online=None, city=None):
        M, rng = self.M, self.rng
        if cat in LOCAL_CATS and online is not True and rng.random() < LOCAL_CATS[cat]:
            c = city or (self.city if rng.random() < 0.8 else pick(rng, R.CITIES)[0])
            ids = M.local.get((c, cat)) or M.local.get((self.city, cat))
            if ids:
                return ids[rng.integers(len(ids))]
        ids = M.chain_ids(cat, self.region, online)
        if not ids:
            ids = M.chain_ids(cat, self.region) or M.local.get((self.city, cat), [])
        return ids[rng.integers(len(ids))] if ids else 0

    def pay_card(self, day, sec, amount, mid, event_id=0, signal=None, country="BE", orig=None, allow_credit=True):
        m = self.M.get(mid)
        amount = abs(amount)
        if m["is_online"]:
            channel = "card_online"
        elif amount <= 50 and self.rng.random() < 0.72:
            channel = "card_contactless"
        elif m["category"] in ("bakery", "cafe_bar", "fast_food") and self.rng.random() < 0.12:
            channel = "mobile_payment"
        else:
            channel = "card_pos"
        acct = "current"
        if allow_credit and "credit_card" in self.accounts and self.accounts["credit_card"]["opened_day"] <= day:
            r = self.rng.random()
            if (m["is_online"] and amount > 30 and r < 0.45) or (country != "BE" and r < 0.7) or (amount > 150 and r < 0.3):
                acct, channel = "credit_card", "credit_card"
        city = m["city"] or (self.city if not m["is_online"] and country == "BE" else None)
        d = to_date(day)
        if channel == "card_online":
            desc = f"ONLINE PAYMENT {m['name'].upper()} REF {self.rng.integers(10 ** 7, 10 ** 8)}"
        elif channel == "mobile_payment":
            desc = f"PAYCONIQ PAYMENT {m['name'].upper()} {d.strftime('%d/%m')}"
        else:
            where = f" {city.upper()}" if city else f" {country}"
            desc = (f"{'CONTACTLESS' if channel == 'card_contactless' else 'CARD'} PAYMENT {m['name'].upper()}{where} "
                    f"{d.strftime('%d/%m')} {sec // 3600:02d}.{sec % 3600 // 60:02d} CARD {self.p['card_last4']}")
        oc, oa = (orig if orig else (None, None))
        self.L.add(acct, day, sec, -amount, m["category"], channel, m["name"], "merchant", desc, mid, city, country,
                   event_id, signal, orig_currency=oc, orig_amount=oa)

    def transfer_out(self, day, amount, cp, cp_type, category, text, event_id=0, signal=None, instant=False,
                     sec=None, account="current", recurring=False, channel=None):
        ch = channel or ("instant_transfer_out" if instant else "transfer_out")
        label = {"instant_transfer_out": "INSTANT TRANSFER TO", "standing_order": "STANDING ORDER TO",
                 "direct_debit": "DIRECT DEBIT", "transfer_out": "TRANSFER TO", "loan_repayment": "LOAN REPAYMENT"}[ch]
        self.L.add(account, day, sec if sec is not None else self.rsec(10, 4), -abs(amount), category, ch, cp,
                   cp_type, f"{label} {cp.upper()} {text}".strip(), event_id=event_id, signal=signal, recurring=recurring)

    def transfer_in(self, day, amount, cp, cp_type, category, text, event_id=0, signal=None, sec=None,
                    account="current", recurring=False, channel="transfer_in"):
        self.L.add(account, day, sec if sec is not None else self.rsec(7, 2, 1, 12), abs(amount), category, channel,
                   cp, cp_type, f"CREDIT TRANSFER FROM {cp.upper()} {text}".strip(), event_id=event_id,
                   signal=signal, recurring=recurring)

    def internal(self, day, amount, src, dst, text, event_id=0, signal=None, sec=None, recurring=False,
                 channel="internal_transfer"):
        sec = sec if sec is not None else self.rsec(9, 3)
        self.L.add(src, day, sec, -abs(amount), "own_transfer", channel, f"Own {dst.replace('_', ' ')} account",
                   "own_account", f"TRANSFER TO OWN ACCOUNT {dst.upper()} {text}".strip(), event_id=event_id,
                   signal=signal, recurring=recurring)
        self.L.add(dst, day, sec, abs(amount), "own_transfer", channel, f"Own {src.replace('_', ' ')} account",
                   "own_account", f"TRANSFER FROM OWN ACCOUNT {src.upper()} {text}".strip(), event_id=event_id,
                   signal=signal, recurring=recurring)

    def monthly(self, start, end, dom, amount, fn, every=1, phase=0, months=None, business="after"):
        """Call fn(day, amount, month_index) once per matching month inside [start, end]."""
        for k, (y, m, first, last) in enumerate(MONTHS):
            if months and m not in months:
                continue
            if every > 1 and (k - phase) % every:
                continue
            d = last if dom == "last" else min(first + dom - 1, last)
            if business == "after":
                d = business_on_or_after(d)
            elif business == "before":
                d = business_on_or_before(d)
            if d >= NDAYS or d < max(0, start) or d > end:
                continue
            a = amount(k, d) if callable(amount) else amount
            if a:
                fn(d, a, k)

    # ------------------------------------------------------------------ build
    def run(self):
        p, t, rng = self.p, self.t, self.rng
        self.setup_accounts()
        self.build_jobs()
        self.build_housing()
        for e in self.events:
            getattr(self, "ev_" + e["event_type"])(e)
        self.emit_jobs()
        self.emit_housing()
        self.emit_bills()
        self.emit_children()
        self.emit_savings_orders()
        self.emit_trips()
        self.emit_spending()
        self.emit_card_settlement()
        return self.finalize()

    def setup_accounts(self):
        p, rng = self.p, self.rng
        prods = p["products"]
        since = (p["customer_since"] - to_date(0)).days
        self.open_account("current", since, opening=p["current_start"])
        if "savings" in prods:
            self.open_account("savings", since + int(rng.integers(0, 400)), opening=p["savings_start"])
        years = max(1.0, min(20.0, p["age_start"] - 25))
        if "pension_savings" in prods:
            self.open_account("pension_savings", -int(years * 365), opening=round(years * float(rng.uniform(700, 1050)), 2))
        if "long_term_savings" in prods:
            self.open_account("long_term_savings", -int(rng.integers(365, 3650)),
                              opening=round(float(rng.uniform(2000, 25000)), 2))
        if "investment_plan" in prods:
            self.open_account("investment_plan", -int(rng.integers(200, 3650)),
                              opening=round(float(rng.uniform(3000, 60000)), 2))
        if "credit_card" in prods:
            self.open_account("credit_card", -int(rng.integers(100, 3650)))
        if p["mortgage"]:
            m = p["mortgage"]
            outstanding = round(m["monthly"] * m["remaining_years"] * 12 * 0.78, -2)
            if m["lender"] == "KBC":
                self.open_account("home_loan", -int(rng.integers(365, 7000)), opening=-outstanding)
            else:
                self.external.append(("home_loan", m["lender"]))
        if "car_loan" in prods:
            months_left = int(rng.integers(6, 48))
            self.car_loan = {"monthly": round(float(rng.uniform(190, 420)), 2), "end": months_left * 30,
                             "lender": "KBC" if prods["car_loan"] == "KBC" else pick(rng, OTHER_BANKS)}
            if prods["car_loan"] == "KBC":
                self.open_account("car_loan", -int(rng.integers(100, 1400)),
                                  opening=-round(self.car_loan["monthly"] * months_left * 0.92, -1))
            else:
                self.external.append(("car_loan", self.car_loan["lender"]))
        else:
            self.car_loan = None
        if self.targets:
            for key, (_, last4) in self.targets.items():
                if key not in self.accounts:
                    self.open_account(key, since + 30)
                self.accounts[key]["last4"] = last4

    # ------------------------------------------------------------------ income
    def build_jobs(self):
        p, rng = self.p, self.rng
        emp = p["employment"]
        kind = {"employee": "salary", "civil_servant": "civil", "self_employed": "self", "student": "student_job",
                "unemployed": "unemployment", "retired": "pension"}[emp]
        payer = p["employer"]
        if kind == "unemployment":
            payer = pick(rng, R.UNEMPLOYMENT_PAYERS[self.region])
        elif kind == "pension":
            payer = R.PENSION_PAYER[self.region]
        self.jobs = [{"kind": kind, "payer": payer, "net": p["income"], "start": -FAR, "end": FAR, "event_id": 0}]
        self.suspend = []           # (start, end, replacement, event_id) e.g. maternity leave
        self.allowance = (-FAR, FAR) if emp == "student" else None

    def current_job(self, day):
        for j in self.jobs:
            if j["start"] <= day < j["end"]:
                return j
        return None

    def change_job(self, day, kind, payer, net, event_id):
        for j in self.jobs:
            if j["start"] <= day < j["end"]:
                j["end"] = day
        self.jobs.append({"kind": kind, "payer": payer, "net": round(net, 0), "start": day, "end": FAR,
                          "event_id": event_id})

    def income_at(self, day):
        j = self.current_job(day)
        return j["net"] if j else 0.0

    def emit_jobs(self):
        rng = self.rng
        for j in self.jobs:
            kind, payer, net, a, b, ev = j["kind"], j["payer"], j["net"], j["start"], j["end"], j["event_id"]
            sig = "income_change" if ev else None
            if kind in ("salary", "civil"):
                dom = "last" if kind == "civil" else self.salary_dom
                def amt(k, d, a=a, b=b, net=net, dom=dom):
                    if dom == 1:                  # paid at the start of the month for the month before
                        if k == 0:
                            return 0
                        k -= 1
                    y, m, first, last = MONTHS[k]
                    worked = (min(last, b - 1) - max(first, a) + 1) / (last - first + 1)
                    if worked <= 0:
                        return 0
                    for s0, s1, _, _ in self.suspend:
                        overlap = min(last, s1) - max(first, s0) + 1
                        if overlap > 0:
                            worked -= overlap / (last - first + 1)
                    return round(net * max(0.0, worked) * (1 + 0.012 * rng.standard_normal()), 2) if worked > 0.02 else 0
                def pay(d, x, k, payer=payer, kind=kind, ev=ev, sig=sig, dom=dom):
                    y, m, _, _ = MONTHS[k - 1 if dom == 1 else k]
                    self.transfer_in(d, x, payer, "employer", "salary", f"SALARY {m:02d}/{y}", ev, sig,
                                     recurring=True)
                self.monthly(a, b + 35, dom, amt, pay, business="before" if dom == "last" else "after")
                for k, (y, m, first, last) in enumerate(MONTHS):
                    if m == 5 and a < first - 120 and b > last:
                        d = business_on_or_before(last)
                        self.transfer_in(d, round(net * (0.85 if kind == "salary" else 0.55), 2), payer, "employer",
                                         "salary", f"HOLIDAY PAY {y}", ev, None)
                    if m == 12 and b > last and a < last - 60:
                        months_worked = min(12, (last - max(a, first - 334)) / 30.4)
                        bonus = net * (0.9 if kind == "salary" else 0.35) * months_worked / 12
                        d = business_on_or_before(first + 19)
                        self.transfer_in(d, round(bonus, 2), payer, "employer", "salary", f"END OF YEAR BONUS {y}", ev)
            elif kind == "self":
                clients = [f"{pick(rng, R.EMPLOYER_PREFIX)} {pick(rng, ['Group', 'Partners', 'Studio', 'Services', 'Solutions'])} "
                           f"{pick(rng, R.EMPLOYER_FORMS)}" for _ in range(6)]
                for k, (y, m, first, last) in enumerate(MONTHS):
                    if last < a or first >= b:
                        continue
                    n = max(1, rng.poisson(3))
                    total = net * 1.45 * float(rng.uniform(0.65, 1.35)) * (0.6 if m == 8 else 1.0)
                    parts = rng.dirichlet(np.ones(n)) * total
                    for x in parts:
                        d = business_on_or_after(int(rng.integers(first, last + 1)))
                        if a <= d < b:
                            self.transfer_in(d, round(x, 2), pick(rng, clients), "client", "business_income",
                                             f"INVOICE {y}{m:02d}{rng.integers(100, 999)}", ev)
                    if m in (3, 6, 9, 12):
                        self.transfer_out(business_on_or_after(first + 14), round(net * 0.62, 2),
                                          pick(rng, R.SOCIAL_FUNDS), "social_security", "social_contributions",
                                          f"SOCIAL CONTRIBUTIONS Q{(m - 1) // 3 + 1} {structured_comm(rng)}",
                                          channel="direct_debit", recurring=True)
                        self.transfer_out(business_on_or_after(first + 9), round(net * 0.7, 2),
                                          R.TAX_AUTHORITY[self.region], "government", "tax",
                                          f"ADVANCE TAX PAYMENT {structured_comm(rng)}", recurring=True)
            elif kind == "student_job":
                for d in range(max(0, a), min(NDAYS, b)):
                    if DOW[d] == 4:
                        summer = MONTH[d] in (7, 8)
                        if rng.random() < (0.85 if summer else 0.35):
                            x = net / 4 * float(rng.uniform(0.5, 1.5)) * (2.3 if summer else 1.0)
                            self.transfer_in(d, round(x, 2), payer, "employer", "salary",
                                             f"STUDENT JOB WEEK {to_date(d).isocalendar()[1]}", ev)
            elif kind == "pension":
                dom = int(rng.integers(1, 3)) if not hasattr(self, "_pdom") else self._pdom
                self.monthly(a, b, dom, lambda k, d: round(net * (1 + 0.004 * (YEAR[d] - 2024)), 2),
                             lambda d, x, k: self.transfer_in(d, x, payer, "government", "pension",
                                                              f"PENSION {MONTHS[k][1]:02d}/{MONTHS[k][0]}", ev, sig,
                                                              recurring=True))
                for k, (y, m, first, last) in enumerate(MONTHS):
                    if m == 5 and a < first and b > last:
                        self.transfer_in(business_on_or_after(first + 2), round(float(rng.uniform(250, 900)), 2),
                                         payer, "government", "pension", f"PENSION HOLIDAY ALLOWANCE {y}", ev)
            elif kind == "unemployment":
                self.monthly(a + 20, b + 25, int(rng.integers(3, 9)), lambda k, d: round(net * float(rng.uniform(0.96, 1.04)), 2),
                             lambda d, x, k: self.transfer_in(d, x, payer, "social_security", "unemployment_benefit",
                                                              f"UNEMPLOYMENT BENEFIT {MONTHS[k - 1][1]:02d}/{MONTHS[k - 1][0]}",
                                                              ev, sig or "unemployment_benefit", recurring=True))
        for s0, s1, amount, ev in self.suspend:
            mut = self.mutuality
            for d in range(max(0, s0 + 14), min(NDAYS, s1 + 14), 15):
                self.transfer_in(business_on_or_after(d), round(amount / 2, 2), mut, "social_security",
                                 "maternity_benefit", "MATERNITY BENEFIT", ev, "maternity_benefit")
        if self.allowance:
            a, b = self.allowance
            amt = float(pick(rng, [100, 150, 150, 200, 250, 300]))
            self.monthly(a, b, int(rng.integers(1, 5)), amt,
                         lambda d, x, k: self.transfer_in(d, x, self.parent_name, "person", "family_support",
                                                          "ZAKGELD" if self.p["language"] == "nl" else "ARGENT DE POCHE",
                                                          recurring=True))

    @property
    def mutuality(self):
        if not hasattr(self, "_mut"):
            self._mut = pick(self.rng, R.MUTUALITIES[self.region])
        return self._mut

    # ------------------------------------------------------------------ housing
    def build_housing(self):
        p = self.p
        self.housing = [{"kind": p["housing"], "start": -FAR, "end": FAR, "rent": p["rent"], "landlord": p["landlord"],
                         "event_id": 0}]
        self.mortgage = None
        if p["mortgage"]:
            self.mortgage = {"monthly": p["mortgage"]["monthly"], "lender": p["mortgage"]["lender"], "start": -FAR,
                             "event_id": 0}
        self.guarantee = None

    def housing_at(self, day):
        for h in self.housing:
            if h["start"] <= day < h["end"]:
                return h
        return self.housing[-1]

    def move(self, day, kind, rent, event_id):
        for h in self.housing:
            if h["start"] <= day < h["end"]:
                h["end"] = day
        landlord = self.p["landlord"] if kind != "tenant" else pick(self.rng, ["Immo Vastgoedbeheer BV", "Woonhaven",
                                                                               "Home Invest Belgium", f"L. {pick(self.rng, R.LAST_NAMES['nl'])}",
                                                                               f"M. {pick(self.rng, R.LAST_NAMES['fr'])}"])
        self.housing.append({"kind": kind, "start": day, "end": FAR, "rent": round(rent, 0), "landlord": landlord,
                             "event_id": event_id})

    def emit_housing(self):
        rng = self.rng
        dom = int(rng.integers(1, 6))
        for h in self.housing:
            if h["kind"] in ("tenant", "student_room") and h["rent"]:
                rent = h["rent"] * (self.share if h["kind"] == "tenant" else 1.0)
                self.monthly(h["start"], h["end"] + 25, dom, round(rent, 2),
                             lambda d, x, k, h=h: self.transfer_out(d, x, h["landlord"], "landlord", "rent",
                                                                    f"RENT {MONTHS[k][1]:02d}/{MONTHS[k][0]}",
                                                                    h["event_id"], "rent" if h["event_id"] else None,
                                                                    sec=self.rsec(5, 1, 3, 8), channel="standing_order",
                                                                    recurring=True))
            elif h["kind"] == "with_parents" and h["rent"]:
                self.monthly(h["start"], h["end"], dom, h["rent"],
                             lambda d, x, k: self.transfer_out(d, x, self.parent_name, "person", "family_support",
                                                               "KOSTGELD" if self.p["language"] == "nl" else "PENSION",
                                                               channel="standing_order", recurring=True))
        if self.mortgage:
            m = self.mortgage
            amount = round(m["monthly"] * (self.share if self.arrangement != "pays_all" else 1.0), 2)
            mdom = int(rng.integers(1, 11))
            if m["lender"] == "KBC":
                def pay(d, x, k):
                    self.L.add("current", d, self.rsec(4, 1, 1, 7), -x, "mortgage", "loan_repayment", "KBC Bank",
                               "bank", f"HOME LOAN REPAYMENT {MONTHS[k][1]:02d}/{MONTHS[k][0]}", event_id=m["event_id"],
                               signal="mortgage_repayment" if m["event_id"] else None, recurring=True)
                    self.L.add("home_loan", d, self.rsec(4, 1, 1, 7), round(x * 0.62, 2), "mortgage", "loan_repayment",
                               "Own current account", "own_account", "PRINCIPAL REPAYMENT", recurring=True)
            else:
                def pay(d, x, k):
                    self.transfer_out(d, x, m["lender"], "bank", "mortgage", f"HOME LOAN {structured_comm(rng)}",
                                      m["event_id"], "mortgage_repayment" if m["event_id"] else None,
                                      channel="direct_debit", recurring=True)
            self.monthly(m["start"] + 25, FAR, mdom, amount, pay)
        if self.car_loan:
            c = self.car_loan
            end = c["end"]
            if c["lender"] == "KBC":
                def cpay(d, x, k):
                    self.L.add("current", d, self.rsec(4, 1, 1, 7), -x, "car_loan", "loan_repayment", "KBC Bank",
                               "bank", "CAR LOAN REPAYMENT", event_id=c.get("event_id", 0), recurring=True)
                    self.L.add("car_loan", d, self.rsec(4, 1, 1, 7), round(x * 0.92, 2), "car_loan", "loan_repayment",
                               "Own current account", "own_account", "PRINCIPAL REPAYMENT", recurring=True)
            else:
                def cpay(d, x, k):
                    self.transfer_out(d, x, c["lender"], "bank", "car_loan", f"CAR LOAN {structured_comm(rng)}",
                                      c.get("event_id", 0), channel="direct_debit", recurring=True)
            self.monthly(c.get("start", -FAR) + 25, end, int(rng.integers(1, 28)), c["monthly"], cpay)

    # ------------------------------------------------------------------ bills
    def own_home_periods(self):
        return [(h["start"], h["end"], h["kind"]) for h in self.housing if h["kind"] != "with_parents"]

    def emit_bills(self):
        p, t, rng, region = self.p, self.t, self.rng, self.region
        sh = self.share if self.p["partner"] else 1.0
        energy = pick(rng, R.ENERGY)
        water = pick(rng, R.WATER[region])
        telecom = pick(rng, R.TELECOM[region])
        hh = 1 + int(p["partner"]) + len(p["children"])
        for a, b, kind in self.own_home_periods():
            house = kind in ("owner", "owner_mortgage")
            if kind == "student_room":
                continue                                # utilities included in the student room rent
            adv = round((70 + 32 * hh + (55 if house else 0)) * float(rng.uniform(0.8, 1.25)) * sh, 0)
            edom = int(rng.integers(12, 26))
            self.monthly(a, b, edom, adv, lambda d, x, k: self.transfer_out(
                d, x, energy, "utility", "energy", f"ADVANCE INVOICE {structured_comm(rng)}", channel="direct_debit",
                recurring=True))
            settle_month = int(rng.integers(1, 13))
            self.monthly(a + 330, b, edom, lambda k, d: round(float(rng.normal(-40, 260)) * sh, 2),
                         lambda d, x, k: (self.transfer_out(d, -x, energy, "utility", "energy",
                                                            f"ANNUAL SETTLEMENT {structured_comm(rng)}", channel="direct_debit")
                                          if x < 0 else self.transfer_in(d, x, energy, "utility", "energy",
                                                                         "ANNUAL SETTLEMENT REFUND")),
                         months=[settle_month])
            wamt = round((30 + 14 * hh) * float(rng.uniform(0.8, 1.2)) * sh, 0)
            self.monthly(a, b, int(rng.integers(5, 25)), wamt, lambda d, x, k: self.transfer_out(
                d, x, water, "utility", "water", f"WATER INVOICE {structured_comm(rng)}", channel="direct_debit",
                recurring=True), every=3, phase=int(rng.integers(0, 3)))
        # telecom: phone only when living with parents or in a student room
        tele_amt = round((42 + 14 * hh + float(rng.uniform(-8, 35))) * sh, 2)
        phone_amt = round(float(rng.uniform(10, 25)), 2)
        tdom = int(rng.integers(5, 25))
        for h in self.housing:
            amt = phone_amt if h["kind"] in ("with_parents", "student_room") else tele_amt
            self.monthly(h["start"], h["end"], tdom, amt, lambda d, x, k: self.transfer_out(
                d, x, telecom, "telecom", "telecom", f"INVOICE {MONTHS[k][1]:02d}/{MONTHS[k][0]}",
                channel="direct_debit", recurring=True))
        # subscriptions
        n_subs = int(np.clip(rng.poisson(2.2 if p["age_start"] < 35 else 1.4 if p["age_start"] < 60 else 0.5), 0, 5))
        for name, price in [R.STREAMING[i] for i in rng.choice(len(R.STREAMING), n_subs, replace=False)]:
            self.monthly(0, FAR, int(rng.integers(1, 29)), price, lambda d, x, k, name=name: self.L.add(
                "current" if "credit_card" not in self.accounts or rng.random() < 0.5 else "credit_card",
                d, self.rsec(3, 1, 0, 6), -x, "streaming", "card_online", name, "subscription",
                f"ONLINE PAYMENT {name.upper()} SUBSCRIPTION", recurring=True), business=None)
        if t["sporty"] and rng.random() < 0.6:
            gname, gprice = R.GYMS[rng.integers(len(R.GYMS))]
            self.monthly(0, FAR, int(rng.integers(1, 28)), gprice, lambda d, x, k: self.transfer_out(
                d, x, gname, "subscription", "gym", "MEMBERSHIP", channel="direct_debit", recurring=True))
        if t["charity_donor"]:
            ch = pick(rng, R.CHARITIES)
            self.monthly(0, FAR, int(rng.integers(1, 28)), float(pick(rng, [5, 10, 10, 15, 20, 25])),
                         lambda d, x, k: self.transfer_out(d, x, ch, "charity", "charity", "MONTHLY GIFT",
                                                           channel="standing_order", recurring=True))
        # bank fees
        self.monthly(0, FAR, 1, self.pay_account_fee, lambda d, x, k: self.L.add(
            "current", d, 3600, -x, "bank_fees", "fee", "KBC Bank", "bank", "ACCOUNT PACKAGE FEE", recurring=True),
            business=None)
        if "credit_card" in self.accounts:
            self.monthly(self.accounts["credit_card"]["opened_day"], FAR, 1, float(pick(rng, [25, 32, 45])),
                         lambda d, x, k: self.L.add("current", d, 3600, -x, "bank_fees", "fee", "KBC Bank", "bank",
                                                    "CREDIT CARD ANNUAL FEE", recurring=True),
                         months=[int(rng.integers(1, 13))], business=None)
        # mutuality membership (+ refunds are generated with medical spending)
        self.monthly(0, FAR, int(rng.integers(5, 25)), round(float(rng.uniform(105, 135)) * (1 + 0.8 * int(p["partner"]) * (self.share < 1 and 0 or 1)), 2),
                     lambda d, x, k: self.transfer_out(d, x, self.mutuality, "social_security", "health_insurance",
                                                       f"MEMBERSHIP {MONTHS[k][0]} {structured_comm(rng)}",
                                                       channel="direct_debit", recurring=True), months=[1])
        # insurance premiums
        self.emit_insurance()
        # taxes
        tax = R.TAX_AUTHORITY[region]
        for y in (2025, 2026):
            k = _month_k(y, int(rng.integers(6, 12)))
            if k is None:
                continue
            d = business_on_or_after(MONTHS[k][2] + int(rng.integers(0, 25)))
            if d >= NDAYS:
                continue
            if p["employment"] != "student" and rng.random() < 0.9:
                if rng.random() < 0.62:
                    self.transfer_in(d, round(float(rng.uniform(80, 1400)), 2), tax, "government", "tax",
                                     f"TAX REFUND {y - 1}")
                else:
                    self.transfer_out(d, round(float(rng.uniform(120, 2400)), 2), tax, "government", "tax",
                                      f"PERSONAL INCOME TAX {y - 1} {structured_comm(rng)}")
            owner_since = min([h["start"] for h in self.housing if h["kind"] in ("owner", "owner_mortgage")] or [FAR])
            if owner_since < MONTHS[k][2] - 200:
                kk = _month_k(y, int(rng.integers(7, 11)))
                if kk is not None:
                    self.transfer_out(business_on_or_after(MONTHS[kk][2] + 10), round(float(rng.uniform(550, 1900)) * sh, 2),
                                  R.REGIONAL_TAX[region] if region == "FL" else tax, "government", "property_tax",
                                  f"PROPERTY TAX {y} {structured_comm(rng)}")
        # road tax for every car month of registration
        if self.car_from < NDAYS:
            regm = int(rng.integers(1, 13))
            self.monthly(self.car_from + 30, FAR, int(rng.integers(1, 28)), round(float(rng.uniform(90, 420)) * max(1, self.p["n_cars"]), 2),
                         lambda d, x, k: self.transfer_out(d, x, R.REGIONAL_TAX[region], "government", "road_tax",
                                                           f"ROAD TAX {structured_comm(rng)}"), months=[regm])

    def emit_insurance(self):
        rng, prods = self.rng, self.p["products"]
        premiums = {"home_insurance": (250, 620), "car_insurance": (430, 1150), "family_liability": (80, 135),
                    "hospitalisation": (300, 900), "outstanding_balance_insurance": (160, 520),
                    "life_insurance": (360, 1200), "income_protection_insurance": (600, 1500)}
        started = getattr(self, "new_insurance", [])
        items = [(k, v, -FAR, 0) for k, v in prods.items() if k in premiums] + started
        for key, provider, start, ev in items:
            if key == "home_insurance" and self.p["housing"] == "with_parents" and start < 0:
                continue
            if key == "car_insurance" and start < 0 and not self.p["has_car"]:
                continue
            yearly = float(rng.uniform(*premiums[key]))
            if key == "hospitalisation":
                yearly *= 1 + 0.25 * len(self.kids)
            name = "KBC Insurance" if provider == "KBC" else pick(rng, R.EXTERNAL_INSURERS)
            monthly = rng.random() < 0.5
            end = self._ins_end.get(key, FAR) if hasattr(self, "_ins_end") and start < 0 else FAR
            sig = "new_insurance" if ev else None
            if monthly:
                self.monthly(start, end, int(rng.integers(1, 28)), round(yearly / 12, 2),
                             lambda d, x, k, name=name, key=key: self.transfer_out(
                                 d, x, name, "insurer", "insurance", f"{key.replace('_', ' ').upper()} PREMIUM",
                                 ev, sig, channel="direct_debit", recurring=True))
            else:
                m = to_date(max(0, start)).month if start >= 0 else int(rng.integers(1, 13))
                self.monthly(start, end, int(rng.integers(1, 28)), round(yearly, 2),
                             lambda d, x, k, name=name, key=key: self.transfer_out(
                                 d, x, name, "insurer", "insurance",
                                 f"{key.replace('_', ' ').upper()} ANNUAL PREMIUM {structured_comm(rng)}",
                                 ev, sig, channel="direct_debit", recurring=True), months=[m])
            if provider == "KBC":
                self.contracts.append({"product_type": key, "start_day": start if start > -FAR else
                                       -int(rng.integers(100, 5000)), "end_day": end, "yearly_premium": round(yearly, 2),
                                       "frequency": "monthly" if monthly else "yearly", "event_id": ev})
            else:
                self.external.append((key, name))

    def new_policy(self, key, day, provider, ev, replaces=True):
        if not hasattr(self, "new_insurance"):
            self.new_insurance, self._ins_end = [], {}
        if replaces:
            self._ins_end[key] = day
        self.new_insurance.append((key, provider, day, ev))
        if provider == "KBC" and 0 <= day < NDAYS:
            self.openings.append((day, key, ev))

    # ------------------------------------------------------------------ children
    def emit_children(self):
        rng, region = self.rng, self.region
        payer = pick(rng, R.CHILD_BENEFIT_PAYERS[region])
        working = lambda d: (self.current_job(d) or {}).get("kind") in ("salary", "civil", "self")
        for birth, visible, ev in self.kids:
            if not visible:
                continue
            amount = round(float(rng.uniform(170, 195)), 2)
            end18 = birth + int(18 * 365.25)
            self.monthly(birth + 20, end18, int(rng.integers(6, 13)), amount,
                         lambda d, x, k, ev=ev: self.transfer_in(d, x, payer, "government", "child_benefit",
                                                                 f"CHILD BENEFIT {MONTHS[k][1]:02d}/{MONTHS[k][0]}", ev,
                                                                 "child_benefit" if ev else None, recurring=True))
            if region == "FL":
                self.monthly(birth + 3 * 365, end18, 20, round(float(rng.uniform(40, 160)), 2),
                             lambda d, x, k: self.transfer_in(d, x, payer, "government", "child_benefit", "SCHOOL BONUS"),
                             months=[8])
        # childcare for children aged 3 months - 3 years when the customer works
        cc = self.M.local.get((self.city, "childcare"), [])
        for birth, visible, ev in self.kids:
            if not cc or rng.random() > (0.72 if ev == 0 else 0.72 * self._trace_i.get(ev, 1)):
                continue
            mid = cc[rng.integers(len(cc))]
            name = self.M.get(mid)["name"]
            amount = round(float(rng.uniform(260, 560)) * (self.share if self.p["partner"] else 1), 2)
            self.monthly(birth + 100, birth + 3 * 365, int(rng.integers(3, 12)),
                         lambda k, d: amount if working(d) else 0,
                         lambda d, x, k, ev=ev: self.transfer_out(d, x, name, "childcare", "childcare",
                                                                  f"CHILDCARE {MONTHS[k][1]:02d}/{MONTHS[k][0]} {structured_comm(rng)}",
                                                                  ev, "childcare" if ev else None, recurring=True))
        # school invoices for children aged 3-17
        schools = self.M.local.get((self.city, "school"), [])
        for birth, visible, ev in self.kids:
            if not schools:
                break
            name = self.M.get(schools[rng.integers(len(schools))])["name"]
            self.monthly(birth + 3 * 365, birth + 18 * 365, int(rng.integers(5, 25)),
                         lambda k, d, birth=birth: round(float(rng.uniform(35, 120)) * (1.8 if d - birth > 12 * 365 else 1), 2),
                         lambda d, x, k: self.transfer_out(d, x * self.share, name, "school", "school",
                                                           f"SCHOOL INVOICE {structured_comm(rng)}"),
                         months=[10, 12, 3, 6])

    # ------------------------------------------------------------------ savings orders
    def emit_savings_orders(self):
        rng, t = self.rng, self.t
        if "savings" in self.accounts and t["saver"]:
            dom = int(rng.integers(2, 8))
            def amt(k, d):
                j = self.current_job(d)
                if not j or j["kind"] in ("unemployment",):
                    return 0
                return max(20.0, round(t["savings_rate"] * j["net"], -1))
            start = max(self.accounts["savings"]["opened_day"], getattr(self, "savings_order_from", -FAR))
            self.monthly(start, FAR, dom, amt, lambda d, x, k: self.internal(d, x, "current", "savings", "MONTHLY SAVINGS",
                                                                            sec=self.rsec(5, 1, 3, 8), recurring=True,
                                                                            channel="standing_order"))
        if "pension_savings" in self.accounts:
            opened = self.accounts["pension_savings"]["opened_day"]
            ev = self.accounts["pension_savings"]["event_id"]
            if rng.random() < 0.6 or opened >= 0:
                self.monthly(opened, FAR, 5, 87.50, lambda d, x, k: self.internal(
                    d, x, "current", "pension_savings", "PENSION SAVINGS", ev, "new_product" if ev else None,
                    recurring=True, channel="standing_order"))
            else:
                self.monthly(opened, FAR, 10, float(pick(rng, [1050, 1050, 1350, 800])), lambda d, x, k: self.internal(
                    d, x, "current", "pension_savings", f"PENSION SAVINGS {MONTHS[k][0]}"), months=[12])
        if "long_term_savings" in self.accounts:
            a = self.accounts["long_term_savings"]
            self.monthly(a["opened_day"], FAR, int(rng.integers(1, 28)), float(pick(rng, [50, 75, 100, 150, 200])),
                         lambda d, x, k: self.internal(d, x, "current", "long_term_savings", "LONG-TERM SAVINGS",
                                                       a["event_id"], "new_product" if a["event_id"] else None,
                                                       recurring=True, channel="standing_order"))
        if "investment_plan" in self.accounts:
            a = self.accounts["investment_plan"]
            amt = float(pick(rng, [50, 100, 150, 250, 500])) * (2 if self.p["income"] > 4000 else 1)
            self.monthly(a["opened_day"], FAR, int(rng.integers(1, 28)), amt,
                         lambda d, x, k: self.internal(d, x, "current", "investment_plan", "INVESTMENT PLAN",
                                                       a["event_id"], "new_product" if a["event_id"] else None,
                                                       recurring=True, channel="standing_order"))
        if "child_savings" in self.accounts:
            a = self.accounts["child_savings"]
            self.monthly(a["opened_day"], FAR, int(rng.integers(1, 28)), float(pick(rng, [25, 30, 50, 50, 75])),
                         lambda d, x, k: self.internal(d, x, "current", "child_savings", "SAVINGS FOR MY CHILD",
                                                       a["event_id"], "new_product", recurring=True,
                                                       channel="standing_order"))

    # ------------------------------------------------------------------ events
    @property
    def _trace_i(self):
        return {e["event_id"]: TRACE_I[e["trace"]] for e in self.events}

    def ev_birth(self, e):
        rng, M = self.rng, self.M
        B, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        P = B - 280
        female = self.p["gender"] == "F"
        if B < NDAYS:
            self.kids.append([B, rng.random() < 0.5 + 0.5 * I and I > 0, ev])
        if female and self.current_job(B) and self.current_job(B)["kind"] in ("salary", "civil"):
            net = self.current_job(B)["net"]
            self.suspend.append((B - 14, B + 91, round(net * 0.8, 2), ev))
        if e["declared"]:
            self.declared.append((e["declared_day"], "expecting_a_child" if e["declared_day"] < B else "new_child", ev))
        # web interest scales with the trace level too
        self.hint("baby_family", P + 50, B + 60, 1.0 * I, ev)
        self.hint("child_savings", P + 120, B + 240, 0.5 * I, ev)
        self.hint("hospitalisation", P + 140, B + 30, 0.35 * I, ev)
        self.hint("family_liability", P + 150, B + 60, 0.15 * I, ev)
        if I == 0:
            return
        for a, b, rate in [(P + 98, P + 189, 1.0), (P + 189, B, 2.8), (B, B + 90, 2.0), (B + 90, B + 365, 0.9),
                           (B + 365, B + 730, 0.4)]:
            self.add_rate("baby", a, b, rate * I ** 2, ev)      # weak traces: a purchase or two at most
        baby_shops = M.chain_ids("baby", online=False)
        for label, lo, hi, where in [("stroller", 450, 1250, "baby"), ("nursery", 250, 900, "furniture"),
                                     ("car_seat", 150, 400, "baby"), ("baby_monitor", 60, 200, "electronics")]:
            if rng.random() < I ** 1.5:
                d = int(rng.integers(P + 190, B - 5)) if label != "car_seat" else int(rng.integers(B - 60, B))
                mid = pick(rng, baby_shops) if where == "baby" else self.merchant(where)
                self.pay_card(d, self.rsec(15, 2.5, 9, 19), round(float(rng.uniform(lo, hi)), 2), mid, ev, label)
        self.boost("pharmacy", P + 30, B + 60, 1 + 0.7 * I, ev)
        if female:
            self.boost("clothing", P + 150, B, 1 + 0.5 * I, ev)
            hosp = M.hospital(self.region, rng)
            if rng.random() < I:
                for d in range(max(P + 56, 0), min(B, NDAYS), int(rng.integers(26, 34))):
                    x = round(float(rng.uniform(45, 80)), 2)
                    self.pay_card(d, self.rsec(11, 2, 8, 17), x, hosp, ev, "prenatal_visit", allow_credit=False)
                    self.transfer_in(d + int(rng.integers(6, 20)), round(x * 0.72, 2), self.mutuality,
                                     "social_security", "health_refund", "REFUND HEALTH CARE", ev, "health_refund")
            if rng.random() < 0.8 * I:
                bill = round(float(rng.uniform(250, 1400)), 2)
                self.transfer_out(B + int(rng.integers(25, 50)), bill, M.get(hosp)["name"], "healthcare", "hospital",
                                  f"HOSPITAL INVOICE {structured_comm(rng)}", ev, "hospital_bill")
                if "hospitalisation" in self.p["products"]:
                    self.transfer_in(B + int(rng.integers(55, 90)), round(bill * 0.8, 2), "KBC Insurance", "insurer",
                                     "health_refund", "HOSPITALISATION CLAIM REFUND", ev, "hospital_refund")
        self.boost("restaurant", B - 30, B + 180, 1 - 0.45 * I)
        self.boost("cafe_bar", B - 30, B + 180, 1 - 0.5 * I)
        self.no_trip[max(0, P + 200):max(0, min(NDAYS, B + 120))] = True
        self.boost("drugstore", B, B + 730, 1 + 1.4 * I, ev)
        self.boost("groceries", B, FAR, 1 + 0.12 * I, ev)
        self.boost("toys", B + 180, FAR, 1 + 2 * I, ev)
        if I < 1:
            self.boost("secondhand", P + 150, B + 365, 1 + 3 * (1 - I), ev)
        if rng.random() < (0.9 if I >= 0.6 else 0.3):
            region_amt = {"FL": 1300.0, "BR": 1340.0, "WA": 1150.0}[self.region]
            d = B - 60 if self.region == "FL" and rng.random() < 0.7 else B + int(rng.integers(10, 35))
            self.transfer_in(d, region_amt, pick(rng, R.CHILD_BENEFIT_PAYERS[self.region]), "government",
                             "child_benefit", "BIRTH ALLOWANCE", ev, "birth_allowance")
        if rng.random() < 0.7 * I:
            self.pay_card(B + int(rng.integers(5, 20)), self.rsec(21, 1.5, 12, 23.5),
                          round(float(rng.uniform(60, 220)), 2), pick(rng, M.chain_ids("photo_print")), ev, "birth_cards")
        if rng.random() < 0.6 * I:
            choc = [M.by_name[n] for n in ("Leonidas", "Neuhaus", "Jeff de Bruges")]
            self.pay_card(B + int(rng.integers(-20, 15)), self.rsec(14, 2.5, 9, 19),
                          round(float(rng.uniform(80, 350)), 2), pick(rng, choc), ev, "birth_sweets")
        if rng.random() < 0.5 * I:
            self.transfer_in(B + int(rng.integers(20, 45)), round(float(rng.uniform(100, 300)), 2), self.mutuality,
                             "social_security", "health_refund", "BIRTH PREMIUM", ev, "birth_premium")
        if not self.demo and rng.random() < 0.35 * I:
            self.open_account("child_savings", B + int(rng.integers(30, 240)), event_id=ev,
                              product_name="Savings account for my child")
        if not self.demo and "family_liability" not in self.p["products"] and rng.random() < 0.25 * I:
            self.new_policy("family_liability", B + int(rng.integers(10, 120)), "KBC", ev, replaces=False)

    def ev_home_purchase(self, e):
        rng, M = self.rng, self.M
        D, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        det = e["details"]
        C, S, price = det["compromis_day"], det["search_start_day"], det["price"]
        self.hint("home_loan", S, D, 1.0 * I, ev, loan_amount=round(price * 0.8, -3), price=price)
        self.hint("home_insurance", C, D + 30, 0.5 * I, ev)
        self.hint("renovation", D, D + 180, 0.25 * I, ev)
        if e["declared"]:
            self.declared.append((e["declared_day"], "buying_a_home", ev))
        if I == 0:
            return
        notary = self.merchant("legal_notary")
        notary_name = M.get(notary)["name"] if notary else "Notariskantoor"
        payer_share = self.share if self.p["partner"] else 1.0
        if rng.random() < (1.0 if I >= 0.6 else 0.3):
            dep = round(price * 0.10 * payer_share, -2)
            self.fund_needs[max(0, min(NDAYS - 1, C))] += dep
            self.transfer_out(C, dep, notary_name, "notary", "home_purchase", "DEPOSIT SALES AGREEMENT", ev,
                              "notary_deposit", sec=self.rsec(11, 2))
        costs_rate = {"FL": 0.045, "WA": 0.062, "BR": 0.078}[self.region]
        if rng.random() < (1.0 if I >= 0.6 else 0.3):
            fees = round(price * costs_rate * float(rng.uniform(0.9, 1.1)) * payer_share, 2)
            self.fund_needs[max(0, min(NDAYS - 1, D))] += fees
            self.transfer_out(D, fees, notary_name, "notary", "home_purchase",
                              f"DEED COSTS AND REGISTRATION DUTIES {structured_comm(rng)}", ev, "deed_costs")
        # housing switches to owner, rent stops after the notice month
        old = self.housing_at(D)
        for h in self.housing:
            if h["start"] <= D < h["end"]:
                h["end"] = D + 30
        self.housing.append({"kind": "owner_mortgage", "start": D + 30, "end": FAR, "rent": 0, "landlord": None,
                             "event_id": ev})
        lender = "KBC" if rng.random() < (0.75 if I == 1 else 0.45) else pick(rng, OTHER_BANKS)
        loan = round(price * 0.8, -3)
        monthly = round(loan * 0.00487, 2)
        self.mortgage = {"monthly": monthly, "lender": lender, "start": D, "event_id": ev}
        if lender == "KBC":
            self.open_account("home_loan", D, opening=0.0, event_id=ev, product_name="Home loan")
            self.L.add("home_loan", D, self.rsec(10, 1), -loan, "mortgage", "loan_disbursement", notary_name, "notary",
                       "HOME LOAN DISBURSEMENT TO NOTARY", event_id=ev, signal="loan_disbursement")
            if rng.random() < 0.8:
                self.new_policy("outstanding_balance_insurance", D, "KBC", ev, replaces=False)
        else:
            self.external.append(("home_loan", lender))
        self.new_policy("home_insurance", D, "KBC" if rng.random() < 0.6 else "external", ev)
        if self.guarantee and old["kind"] == "tenant":
            g_amt, _ = self.guarantee
            self.internal(D + int(rng.integers(45, 90)), g_amt, "rental_guarantee", "current",
                          "RELEASE RENTAL GUARANTEE", ev, "guarantee_release")
        if rng.random() < 0.55 * I:
            mover = self.merchant("moving_services")
            if mover:
                self.transfer_out(D + int(rng.integers(20, 50)), round(float(rng.uniform(400, 1600)), 2),
                                  M.get(mover)["name"], "merchant", "moving_services", "INVOICE MOVE", ev, "moving_company")
        self.boost("furniture", D - 10, D + 150, 1 + 4 * I, ev)
        self.boost("diy_garden", D - 30, D + 240, 1 + 2.5 * I, ev)
        self.boost("electronics", D, D + 90, 1 + 1.0 * I, ev)
        for _ in range(int(rng.integers(1, 4) * I + 0.5)):
            self.pay_card(D + int(rng.integers(10, 120)), self.rsec(14, 2.5, 10, 19), round(float(rng.uniform(300, 2500)), 2),
                          self.M.by_name["IKEA"], ev, "furnishing")

    def ev_first_job(self, e):
        rng = self.rng
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        net = 2450.0 if self.demo == "lucas" else round(float(np.exp(rng.normal(np.log(2150), 0.14))), 0)
        employer, sector = new_employer(rng, self.region)
        if self.demo == "lucas":
            employer = "Noordster Consulting BV"
        self.change_job(d, "salary", employer, net, ev)
        self.allowance = (-FAR, d + int(rng.integers(20, 90)))
        self.spend_level[d + 25:] *= min(2.0, (net / max(250, self.p["income"] + 150)) ** 0.45)
        self.savings_order_from = d + 45
        self.hint("first_job", d - 30, d + 120, 0.8 * max(I, 0.3), ev)
        self.hint("pension_savings", d + 30, d + 300, 0.3 * I, ev)
        self.hint("cards", d, d + 150, 0.2 * I, ev)
        if not self.demo:
            if rng.random() < 0.3 and "credit_card" not in self.accounts:
                self.open_account("credit_card", d + int(rng.integers(20, 150)), event_id=ev, product_name="Credit card")
            if rng.random() < 0.2 and "pension_savings" not in self.accounts:
                self.open_account("pension_savings", d + int(rng.integers(40, 300)), event_id=ev,
                                  product_name="Pension savings fund")
            if "savings" not in self.accounts and rng.random() < 0.5:
                self.open_account("savings", d + int(rng.integers(30, 120)), event_id=ev, product_name="Savings account")
        if self.p["housing"] == "student_room" and not any(x["event_type"] == "moving_out" for x in self.events):
            self.housing[0]["end"] = min(self.housing[0]["end"], d + 300)

    def ev_moving_out(self, e):
        rng = self.rng
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        rent = (820.0 if self.demo == "lucas" else
                round({"FL": 1.0, "BR": 1.18, "WA": 0.88}[self.region] * float(rng.uniform(640, 950)), 0))
        self.move(d, "tenant", rent, ev)
        self.hint("moving", d - 60, d + 20, 0.9 * max(I, 0.3), ev)
        self.hint("home_insurance", d - 30, d + 30, 0.4 * I, ev)
        if e["declared"]:
            self.declared.append((e["declared_day"], "moving", ev))
        self.boost("groceries", d, FAR, 1.9, ev if I > 0 else 0)
        self.boost("bakery", d, FAR, 1.4)
        if I == 0:
            return
        if rng.random() < I:
            g = round(rent * 2, 0)
            self.open_account("rental_guarantee", d - 15, event_id=ev, product_name="Rental guarantee account")
            self.fund_needs[max(0, d - 15)] += g
            self.internal(d - 15, g, "current", "rental_guarantee", "RENTAL GUARANTEE", ev, "rental_guarantee")
            self.guarantee = (g, d - 15)
        self.boost("furniture", d - 20, d + 60, 1 + 5 * I, ev)
        self.boost("diy_garden", d - 20, d + 60, 1 + 1.5 * I, ev)
        self.boost("discount_store", d - 10, d + 60, 1 + 1.0 * I, ev)
        if rng.random() < 0.8 * I:
            self.pay_card(d - int(rng.integers(0, 15)), self.rsec(14, 2.5, 10, 19), round(float(rng.uniform(250, 1400)), 2),
                          self.M.by_name["IKEA"], ev, "furnishing")
        if not self.demo and rng.random() < 0.45 * I and "home_insurance" not in self.p["products"]:
            self.new_policy("home_insurance", d, "KBC" if rng.random() < 0.55 else "external", ev, replaces=False)

    def ev_cohabitation(self, e):
        rng = self.rng
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        self.partner_from, self.partner_to = d, FAR
        self.arrangement = pick(rng, {"pays_all": .45, "split": .40, "partner_pays_most": .15})
        new_share = {"pays_all": 1.0, "split": 0.5, "partner_pays_most": 0.3}[self.arrangement]
        h = self.housing_at(d)
        if h["kind"] in ("with_parents", "student_room", "tenant"):
            rent = round({"FL": 1.0, "BR": 1.18, "WA": 0.88}[self.region] * float(rng.uniform(850, 1250)), 0)
            self.move(d, "tenant", rent * new_share / max(self.share, 0.01), ev)
        self.hint("living_together", d - 60, d + 30, 0.8 * I, ev)
        if e["declared"]:
            self.declared.append((e["declared_day"], "living_together", ev))
        if I == 0:
            return
        if self.arrangement == "pays_all":
            contrib = round(float(rng.uniform(350, 800)), 0)
            self.monthly(d, FAR, int(rng.integers(1, 6)), contrib, lambda dd, x, k: self.transfer_in(
                dd, x, self.partner_name, "person", "household_contribution", "HOUSEHOLD", ev, "partner_contribution",
                recurring=True))
        self.boost("furniture", d - 15, d + 45, 1 + 2.5 * I, ev)
        self.boost("groceries", d, FAR, 1 + 0.3 * I, ev)

    def ev_wedding(self, e):
        rng, M = self.rng, self.M
        W, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        self.hint("wedding", W - 240, W, 0.9 * I, ev)
        if e["declared"]:
            self.declared.append((e["declared_day"], "getting_married", ev))
        if I == 0:
            return
        venue = [m for m in M.local.get((self.city, "wedding_services"), [])]
        items = [("wedding_venue_deposit", W - int(rng.integers(120, 200)), 1000, 3500),
                 ("wedding_rings", W - int(rng.integers(60, 150)), 800, 3500),
                 ("wedding_photographer", W - int(rng.integers(20, 60)), 800, 2200),
                 ("wedding_catering", W - int(rng.integers(3, 30)), 3000, 12000)]
        for label, d, lo, hi in items:
            if rng.random() < I:
                x = round(float(rng.uniform(lo, hi)) * self.share, 2)
                if label == "wedding_rings":
                    self.pay_card(d, self.rsec(14, 2), x, self.merchant("jewelry"), ev, label)
                else:
                    self.fund_needs[max(0, min(NDAYS - 1, d))] += x
                    self.transfer_out(d, x, M.get(pick(rng, venue))["name"] if venue else "Feestzaal", "merchant",
                                      "wedding_services", label.replace("_", " ").upper(), ev, label)
        self.boost("clothing", W - 90, W - 5, 1 + 2 * I, ev)
        self.boost("hair_beauty", W - 14, W, 1 + 3 * I, ev)
        for _ in range(int(rng.integers(6, 22) * I)):
            self.transfer_in(W + int(rng.integers(-5, 20)), float(pick(rng, [25, 50, 50, 75, 100, 150, 250])),
                             pick(rng, self.friends), "person", "gift_received",
                             "HUWELIJKSCADEAU" if self.p["language"] == "nl" else "CADEAU MARIAGE", ev, "wedding_gift")
        self.forced_trips = getattr(self, "forced_trips", []) + [(W + 2, int(rng.integers(7, 15)), ev, "honeymoon")]

    def ev_car_purchase(self, e):
        rng = self.rng
        C, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        price, with_loan = e["details"]["price"], e["details"]["with_loan"]
        self.hint("car_loan", C - 90, C, 0.9 * I, ev, loan_amount=round(price * 0.8, -2), price=price)
        self.hint("car_insurance", C - 30, C + 15, 0.4 * I, ev)
        first = self.car_from > C
        self.car_from = min(self.car_from, C)
        if first:
            self.boost("public_transport", C, FAR, 0.4)
        if I == 0:
            return
        dealer = self.merchant("car_dealer")
        dname = self.M.get(dealer)["name"] if dealer else "Garage"
        down = price if not with_loan else round(price * 0.2, -2)
        if rng.random() < (1 if I >= 0.6 else 0.4):
            self.fund_needs[max(0, min(NDAYS - 1, C))] += down
            self.transfer_out(C, down, dname, "merchant", "car_dealer", f"INVOICE VEHICLE {structured_comm(rng)}", ev,
                              "car_payment")
        if with_loan:
            lender = "KBC" if rng.random() < 0.6 else pick(rng, OTHER_BANKS)
            months = int(rng.integers(36, 72))
            monthly = round((price - down) * (1 + 0.055 * months / 24) / months, 2)
            self.car_loan = {"monthly": monthly, "end": C + months * 30, "lender": lender, "start": C, "event_id": ev}
            if lender == "KBC":
                self.open_account("car_loan", C, event_id=ev, product_name="Car loan")
                self.L.add("car_loan", C, self.rsec(10, 1), -(price - down), "car_loan", "loan_disbursement", dname,
                           "merchant", "CAR LOAN DISBURSEMENT TO DEALER", event_id=ev, signal="loan_disbursement")
            else:
                self.external.append(("car_loan", lender))
        if first or rng.random() < 0.3:
            self.new_policy("car_insurance", C, "KBC" if rng.random() < 0.5 else "external", ev)
        self.boost("car_repair", C - 30, C, 1.0)

    def ev_job_loss(self, e):
        rng = self.rng
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        j = self.current_job(d)
        if not j:
            return
        net = j["net"]
        benefit = float(np.clip(net * 0.62, 1100, 1750))
        self.change_job(d, "unemployment", pick(rng, R.UNEMPLOYMENT_PAYERS[self.region]), benefit, ev)
        if e["details"].get("severance"):
            self.transfer_in(d + int(rng.integers(10, 30)), round(net * float(rng.uniform(2, 6)), 2), j["payer"],
                             "employer", "salary", "SEVERANCE PAY", ev, "severance")
        self.spend_level[d:] *= 0.78
        self.boost("restaurant", d, FAR, 0.6)
        self.boost("food_delivery", d, FAR, 0.6)
        self.hint("job_loss", d, d + 120, 0.9 * max(I, 0.3), ev)
        self.hint("budgeting", d, d + 180, 0.6 * max(I, 0.3), ev)
        if e["declared"]:
            self.declared.append((e["declared_day"], "lost_job", ev))

    def ev_new_job(self, e):
        rng = self.rng
        d, ev = e["day"], e["event_id"]
        prev = [j for j in self.jobs if j["kind"] in ("salary", "civil")]
        base = prev[-1]["net"] if prev else self.p["income"]
        employer, _ = new_employer(rng, self.region)
        self.change_job(d, "salary", employer, base * (1 + e["details"].get("raise_pct", 0.05)), ev)
        if e["details"].get("after_unemployment"):
            self.spend_level[d:] /= 0.78
        if e["declared"]:
            self.declared.append((e["declared_day"], "new_job", ev))

    def ev_retirement(self, e):
        rng = self.rng
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        j = self.current_job(d)
        self.hint("retirement", d - 300, d + 60, 0.8 * max(I, 0.3), ev)
        if not j:
            return
        pension = float(np.clip(j["net"] * float(rng.uniform(0.55, 0.72)), 1300, 2700))
        self.change_job(d, "pension", R.PENSION_PAYER[self.region], pension, ev)
        payout = e["details"].get("group_insurance_payout", 0)
        if payout:
            self.transfer_in(d + int(rng.integers(30, 80)), payout, pick(rng, R.EXTERNAL_INSURERS[:3] + ["KBC Insurance"]),
                             "insurer", "lump_sum", "GROUP INSURANCE CAPITAL", ev, "group_insurance_payout")
            self.hint("investing", d + 30, d + 365, 0.7 * max(I, 0.3), ev)
        self.boost("diy_garden", d, FAR, 1.3)
        self.boost("restaurant", d, FAR, 1.15)
        self.spend_level[d:] *= 0.9
        if "pension_savings" in self.accounts and e["declared"] is not None:
            pass
        if e["declared"]:
            self.declared.append((e["declared_day"], "retiring", ev))

    def ev_inheritance(self, e):
        rng = self.rng
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        self.hint("inheritance", d - 30, d + 120, 0.8 * I, ev)
        self.hint("investing", d, d + 240, 0.6 * I, ev)
        if I == 0:
            return
        notary = self.merchant("legal_notary")
        name = self.M.get(notary)["name"] if notary else "Notariskantoor"
        if rng.random() < 0.4:
            self.transfer_out(d - int(rng.integers(90, 200)), round(float(rng.uniform(3000, 6500)), 2),
                              f"Uitvaartzorg {pick(rng, R.LAST_NAMES['nl'])}" if self.p["language"] == "nl" else
                              f"Pompes funèbres {pick(rng, R.LAST_NAMES['fr'])}", "merchant", "funeral", "INVOICE", ev,
                              "funeral")
        self.transfer_in(d, e["details"]["amount"], name, "notary", "inheritance", "ESTATE SETTLEMENT", ev, "inheritance")

    def ev_separation(self, e):
        rng = self.rng
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        self.partner_to = d
        self.hint("separation", d - 60, d + 60, 0.8 * I, ev)
        self.hint("budgeting", d, d + 120, 0.4 * I, ev)
        if e["declared"]:
            self.declared.append((e["declared_day"], "separating", ev))
        h = self.housing_at(d)
        if h["kind"] == "tenant":
            self.move(d + 30, "tenant", round(float(rng.uniform(650, 950)), 0) / max(self.share, 0.3), ev)
        self.boost("groceries", d, FAR, 0.72)
        self.spend_level[d:] *= 0.92
        if I == 0:
            return
        lawyer = self.merchant("legal_notary")
        if lawyer and rng.random() < I:
            self.transfer_out(d + int(rng.integers(-30, 90)), round(float(rng.uniform(500, 2500)), 2),
                              self.M.get(lawyer)["name"], "notary", "legal", f"FEE NOTE {structured_comm(rng)}", ev,
                              "lawyer")
        self.boost("furniture", d + 20, d + 90, 1 + 2 * I, ev)

    def ev_child_to_higher_education(self, e):
        rng, M = self.rng, self.M
        d, I, ev = e["day"], TRACE_I[e["trace"]], e["event_id"]
        self.hint("studying", d - 120, d + 30, 0.7 * I, ev)
        if I == 0:
            return
        uni = M.university(self.region, rng)
        fee = 1168.0 if self.region == "FL" else 835.0
        child = f"{pick(rng, FIRST_NAMES_ALL)} {self.p['last_name']}"
        self.transfer_out(d, fee * (0.5 if rng.random() < 0.3 else 1), M.get(uni)["name"], "school", "education",
                          f"TUITION FEE {to_date(d).year}-{to_date(d).year + 1} {structured_comm(rng)}", ev, "tuition_fee")
        if e["details"].get("student_room"):
            rent = round(float(rng.uniform(420, 590)), 0)
            self.monthly(d - 15, FAR, 1, rent,
                         lambda dd, x, k: self.transfer_out(dd, x, f"Kotbaas {pick(rng, R.LAST_NAMES['nl'])}", "landlord",
                                                            "student_room", "HUUR KOT", ev, "student_room_rent",
                                                            channel="standing_order", recurring=True),
                         months=[9, 10, 11, 12, 1, 2, 3, 4, 5, 6])
        allowance = float(pick(rng, [100, 150, 200, 250]))
        self.monthly(d, FAR, int(rng.integers(1, 6)), allowance,
                     lambda dd, x, k: self.transfer_out(dd, x, child, "person", "family_support", "ZAKGELD", ev,
                                                        "allowance_to_child", channel="standing_order", recurring=True))

    # distractors ---------------------------------------------------------
    def ev_grandchild_born(self, e):
        rng, M = self.rng, self.M
        d, ev = e["day"], e["event_id"]
        shops = M.chain_ids("baby") + M.chain_ids("toys")
        for _ in range(int(rng.integers(1, 5))):
            self.pay_card(d + int(rng.integers(-60, 200)), self.rsec(14, 2.5, 9, 19), round(float(rng.uniform(25, 220)), 2),
                          pick(rng, shops), ev, "gift_for_grandchild")
        self.transfer_out(d + int(rng.integers(3, 30)), float(pick(rng, [100, 150, 250, 500])),
                          f"{pick(rng, FIRST_NAMES_ALL)} {self.p['last_name']}", "person", "gift",
                          "GEBOORTECADEAU" if self.p["language"] == "nl" else "CADEAU NAISSANCE", ev, "birth_gift")
        self.pay_card(d + int(rng.integers(1, 10)), self.rsec(11, 2), round(float(rng.uniform(25, 60)), 2),
                      self.merchant("gifts_flowers"), ev, "flowers")
        self.hint("child_savings", d, d + 120, 0.3, ev)
        self.hint("baby_family", d - 20, d + 30, 0.1, ev)

    def ev_baby_gift_friend(self, e):
        rng, M = self.rng, self.M
        d, ev = e["day"], e["event_id"]
        self.pay_card(d, self.rsec(14, 2.5, 9, 19), round(float(rng.uniform(25, 90)), 2),
                      pick(rng, M.chain_ids("baby") + M.chain_ids("toys")), ev, "baby_gift")

    def ev_business_trips(self, e):
        rng, M = self.rng, self.M
        ev = e["event_id"]
        employer = self.p["employer"] or "Employer"
        n = int(e["details"]["per_year"] * 2 * float(rng.uniform(0.7, 1.2)))
        for _ in range(n):
            d = int(rng.integers(0, NDAYS - 3))
            while DOW[d] >= 5:
                d += 1
            nights = int(rng.integers(1, 4))
            country = pick(rng, ["DE", "FR", "NL", "GB", "ES", "IT", "AT"])
            flight = round(float(rng.uniform(140, 480)), 2)
            self.pay_card(d - int(rng.integers(5, 30)), self.rsec(11, 3), flight,
                          pick(rng, [M.by_name["Brussels Airlines"], M.by_name["Eurostar"], M.by_name["Transavia"]]),
                          ev, "business_flight")
            hotel_ids = M.foreign.get((country, "travel_lodging"), [])
            hotel = round(float(rng.uniform(110, 240)) * nights, 2)
            if hotel_ids:
                self.pay_card(d + nights, self.rsec(8, 1), hotel, pick(rng, hotel_ids), ev, "business_hotel", country=country)
            self.pay_card(d, self.rsec(18, 2), round(float(rng.uniform(15, 60)), 2), M.by_name["Uber"], ev, "business_taxi")
            self.transfer_in(d + int(rng.integers(15, 45)), round(flight + hotel + 40, 2), employer, "employer",
                             "expense_refund", "EXPENSE CLAIM", ev, "expense_refund")

    def ev_home_browsing_only(self, e):
        d = e["day"]
        self.hint("home_loan", d, d + int(self.rng.integers(20, 90)), 0.6, e["event_id"],
                  loan_amount=round(float(self.rng.uniform(180_000, 380_000)), -3))

    def ev_car_browsing_only(self, e):
        d = e["day"]
        self.hint("car_loan", d, d + int(self.rng.integers(10, 50)), 0.6, e["event_id"],
                  loan_amount=round(float(self.rng.uniform(8_000, 35_000)), -2))

    def ev_renovation(self, e):
        rng = self.rng
        d, ev = e["day"], e["event_id"]
        budget = e["details"]["budget"]
        self.hint("renovation", d - 60, d + 30, 0.6, ev)
        self.boost("diy_garden", d, d + 120, 3.5, ev)
        contractor = pick(rng, [f"Bouwbedrijf {pick(rng, R.LAST_NAMES['nl'])}", f"Keukens {pick(rng, R.LAST_NAMES['nl'])}",
                                f"Rénovation {pick(rng, R.LAST_NAMES['fr'])} SRL", "Sanitair Center"])
        for share in rng.dirichlet(np.ones(int(rng.integers(1, 4)))):
            x = round(budget * share * 0.7, 2)
            dd = d + int(rng.integers(0, 120))
            self.fund_needs[max(0, min(NDAYS - 1, dd))] += x
            self.transfer_out(dd, x, contractor, "merchant", "home_improvement", f"INVOICE {structured_comm(rng)}", ev,
                              "contractor_invoice")

    def ev_big_one_off_purchase(self, e):
        rng, M = self.rng, self.M
        d, ev = e["day"], e["event_id"]
        what = e["details"]["what"]
        cat = {"kitchen_appliances": "electronics", "sofa": "furniture", "e_bike": "sports", "laptop": "electronics",
               "holiday_package": "travel_agency"}[what]
        x = round(float(rng.uniform(900, 4000)), 2)
        self.fund_needs[max(0, min(NDAYS - 1, d))] += x
        self.pay_card(d, self.rsec(15, 2.5, 10, 20), x, self.merchant(cat), ev, what)

    # ------------------------------------------------------------------ trips
    def emit_trips(self):
        p, t, rng, M = self.p, self.t, self.rng, self.M
        trips = []
        per_year = t["traveler"] * (1.8 if p["income"] > 3000 else 1.2) * (0.5 if p["employment"] in ("student", "unemployed") else 1)
        n = rng.poisson(per_year * NDAYS / 365)
        family = bool(self.kids)
        for _ in range(n):
            for _try in range(20):
                d = int(rng.integers(20, NDAYS - 5))
                month = MONTH[d]
                if family and not SCHOOL_HOLIDAY[d]:
                    continue
                if not family and month not in (5, 6, 7, 8, 9, 10, 12, 2, 4) and rng.random() < 0.6:
                    continue
                if self.no_trip[d]:
                    continue
                trips.append((d, int(rng.integers(4, 15)), 0, "holiday"))
                break
        trips += getattr(self, "forced_trips", [])
        self.trips = []
        hh = self.hh_adults + len(self.kids)
        for start, length, ev, kind in trips:
            by_car = self.car_from <= start and rng.random() < 0.4
            country = pick(rng, ["FR", "NL", "DE", "IT", "ES", "AT"] if by_car else R.COUNTRIES_ABROAD)
            book = start - int(rng.integers(20, 150))
            self.trips.append((start, book))
            if not by_car:
                airline = pick(rng, [M.by_name[n] for n in ("Ryanair", "Brussels Airlines", "TUI fly", "Transavia")])
                self.pay_card(book, self.rsec(20, 2.5), round(float(rng.uniform(90, 320)) * min(hh, 4) * self.share, 2),
                              airline, ev, "honeymoon" if kind == "honeymoon" else None)
            lodging = pick(rng, [M.by_name[n] for n in ("Booking.com", "Airbnb", "TUI", "Sunweb", "Center Parcs")])
            self.pay_card(book + int(rng.integers(0, 10)), self.rsec(21, 2),
                          round(float(rng.uniform(60, 180)) * length * (1 + 0.3 * (hh - 1)) * self.share, 2), lodging, ev,
                          "honeymoon" if kind == "honeymoon" else None)
            end = min(NDAYS, start + length)
            if start >= NDAYS:
                continue
            self.away[start:end] = True
            cur = {"GB": ("GBP", 0.85), "TR": ("TRY", 38.0), "MA": ("MAD", 10.8)}.get(country)
            for d in range(start, end):
                for cat, rate, lo, hi in [("restaurant", 0.9, 25, 90), ("cafe_bar", 1.2, 6, 25), ("groceries", 0.5, 15, 70),
                                          ("entertainment", 0.3, 10, 60), ("fuel", 0.3 if by_car else 0, 50, 95)]:
                    for _ in range(rng.poisson(rate)):
                        ids = M.foreign.get((country, cat)) or M.foreign.get(("FR", cat))
                        x = round(float(rng.uniform(lo, hi)) * (1 + 0.25 * (hh - 1)), 2)
                        orig = (cur[0], round(x * cur[1], 2)) if cur else None
                        self.pay_card(d, self.rsec(15, 4, 8, 23.5), x, pick(rng, ids), ev,
                                      "honeymoon" if kind == "honeymoon" else None, country=country, orig=orig)
            if rng.random() < 0.3:
                self.L.add("current", start + 1, self.rsec(12, 3), -float(pick(rng, [50, 100, 150, 200])), "atm",
                           "atm", "ATM abroad", "atm", f"CASH WITHDRAWAL ABROAD {country}", country=country)

    # ------------------------------------------------------------------ day-to-day spending
    def taste(self):
        p, t, rng = self.p, self.t, self.rng
        age = p["age_start"]
        hh = 1 + int(p["partner"]) + len(p["children"])
        young_kids = sum(1 for b in p["children"] if (to_date(0) - b).days < 12 * 365)
        student = p["employment"] == "student"
        at_parents = p["housing"] in ("with_parents",)
        tv = {c: float(np.exp(rng.normal(0, 0.4))) for c in SPEND}
        amt = {c: 1.0 for c in SPEND}
        inc_f = (max(p["income"], 900) / 2500) ** 0.3
        tv["groceries"] *= hh ** 0.3 * (0.35 if at_parents else 0.8 if student else 1)
        amt["groceries"] *= hh ** 0.45 * inc_f
        for c in ("restaurant", "cafe_bar", "fast_food", "food_delivery"):
            tv[c] *= t["eats_out"]
        tv["food_delivery"] *= 0.3 + 1.6 * t["online_shopper"]
        tv["marketplace"] *= 0.2 + 1.6 * t["online_shopper"]
        tv["secondhand"] *= 0.2 + 1.5 * t["online_shopper"]
        tv["clothing"] *= 1.25 if p["gender"] == "F" else 0.8
        tv["hair_beauty"] *= 1.3 if p["gender"] == "F" else 0.8
        tv["fuel"] *= max(1, p["n_cars"])
        tv["public_transport"] *= (0.35 if p["has_car"] else 2.2) * (1.4 if self.region == "BR" else 1)
        tv["pets"] *= 1 if t["has_pet"] else 0
        tv["vet"] *= 1 if t["has_pet"] else 0
        tv["lottery"] *= 1 if t["gambler"] else 0
        tv["books_news"] *= 2.2 if t["smokes"] else 1
        tv["atm"] *= 0.25 + 2.5 * t["cash_user"]
        tv["toys"] *= 1 + 1.5 * young_kids
        tv["entertainment"] *= 1.3 if p["children"] else 1
        tv["sports"] *= 2.5 if t["sporty"] else 0.5
        tv["p2p_out"] *= 1.6 if age < 35 else 0.7
        tv["p2p_in"] *= 1.6 if age < 35 else 0.5
        tv["medical"] *= 1 + max(0, age - 45) / 25
        tv["pharmacy"] *= 1 + max(0, age - 45) / 25
        if age >= 66:
            for c, f in (("fast_food", .3), ("food_delivery", .15), ("cafe_bar", .7), ("marketplace", .5), ("sports", .5)):
                tv[c] *= f
        if student:
            for c, f in (("cafe_bar", 1.6), ("fast_food", 1.6), ("restaurant", .5), ("furniture", .3), ("diy_garden", .2)):
                tv[c] *= f
        act = t.get("activity", 1.0 if not t["idle_cash"] else float(rng.uniform(0.5, 0.85)))
        for c in tv:
            tv[c] *= act
        return tv, amt

    def emit_spending(self):
        p, t, rng, M = self.p, self.t, self.rng, self.M
        tv, amt = self.taste()
        # budget: variable spending fits what is left after fixed costs and savings
        fixed = self._fixed_monthly()
        inc0 = self.income_at(0) + (p["rent"] if False else 0)
        if self.jobs[0]["kind"] == "student_job":
            inc0 += 180
        expected = sum(SPEND[c][0] * tv[c] * SPEND[c][1] * amt[c] for c in SPEND if c not in ("p2p_in",))
        target = p.get("spend_target_total", 0) - fixed if p.get("spend_target_total") else \
            (inc0 - fixed - (t["savings_rate"] * inc0 if t["saver"] else 0)) * float(rng.uniform(0.82, 1.0))
        target = max(target, 180.0)
        s = float(np.clip(target / max(expected, 1), 0.3, 8.0 if p.get("spend_target_total") else 2.2))
        # a demo spending target (Marc: few movements, ~2,400 EUR a month) scales amounts, not the number of purchases
        cnt_scale, amt_scale = (s ** 0.15, s ** 0.85) if p.get("spend_target_total") else (s ** 0.55, s ** 0.45)
        lvl = self.spend_level ** 0.8
        prefs = {}
        for cat, (per_month, mean, sigma) in SPEND.items():
            rate = per_month / 30.44 * tv[cat] * cnt_scale * self.mult[cat] * lvl
            if cat in _DOW_W:
                rate = rate * _DOW_W[cat][DOW]
            if cat == "fuel":
                rate = np.where(np.arange(NDAYS) >= self.car_from, rate if p["n_cars"] else per_month / 30.44 * cnt_scale * self.mult[cat], 0)
            if cat == "parking":
                rate = np.where(np.arange(NDAYS) >= self.car_from, rate, rate * 0.1)
            if cat in AWAY_CATS:
                rate = np.where(self.away, rate * 0.05, rate)
            extra = self.extra[cat] if cat in self.extra else None
            if extra is not None:
                rate = rate + extra
            counts = rng.poisson(np.maximum(rate, 0))
            days = np.repeat(np.arange(NDAYS), counts)
            if not len(days):
                continue
            n = len(days)
            m_amt = mean * amt[cat] * (amt_scale if cat not in ("baby",) else 1)
            amounts = m_amt * np.exp(sigma * rng.standard_normal(n) - sigma ** 2 / 2)
            (mh, sd), _ = R.CATEGORY_TIME.get(cat, ((13, 3.5), None))
            hours = np.clip(rng.normal(mh, sd, n), 6.5 if cat not in ("marketplace", "food_delivery", "secondhand") else 0, 23.9)
            secs = (hours * 3600).astype(int) + rng.integers(0, 60, n)
            ev_ids = np.zeros(n, dtype=np.int64)
            if cat in self.mult_ev or cat in self.extra_ev:
                base_part = (per_month / 30.44 * tv[cat] * cnt_scale * lvl)[days]
                boost_ev = self.mult_ev[cat][days] if cat in self.mult_ev else np.zeros(n, dtype=np.int64)
                m = self.mult[cat][days]
                ex = self.extra[cat][days] if cat in self.extra else np.zeros(n)
                ex_ev = self.extra_ev[cat][days] if cat in self.extra_ev else np.zeros(n, dtype=np.int64)
                total = base_part * m + ex
                p_extra = np.divide(ex, total, out=np.zeros(n), where=total > 0)
                p_boost = np.where(m > 1, base_part * (m - 1) / np.maximum(total, 1e-9), 0)
                u = rng.random(n)
                ev_ids = np.where((u < p_extra) & (ex_ev > 0), ex_ev,
                                  np.where((u >= p_extra) & (u < p_extra + p_boost) & (boost_ev > 0), boost_ev, 0))
            if cat == "atm":
                notes = rng.choice([20, 40, 50, 50, 60, 100, 100, 150, 200], n)
                for d, sc, x in zip(days, secs, notes):
                    self.L.add("current", d, sc, -float(x), "atm", "atm", f"Batopin ATM {self.city}", "atm",
                               f"CASH WITHDRAWAL BATOPIN {self.city.upper()} {to_date(d).strftime('%d/%m')}", city=self.city)
                continue
            if cat in ("p2p_out", "p2p_in"):
                for d, sc, x in zip(days, secs, amounts):
                    x = round(float(x) * 2) / 2
                    friend = pick(rng, self.friends)
                    comm = pick(rng, COMMUNICATIONS)
                    if cat == "p2p_out":
                        self.transfer_out(d, x, friend, "person", "p2p", comm, instant=True, sec=int(sc))
                    else:
                        self.transfer_in(d, x, friend, "person", "p2p", comm, sec=int(sc), channel="instant_transfer_in")
                continue
            if cat not in prefs:
                prefs[cat] = self._prefs(cat)
            ids, w = prefs[cat]
            if not len(ids):
                continue
            chosen = rng.choice(ids, n, p=w)
            for d, sc, x, mid, e in zip(days, secs, amounts, chosen, ev_ids):
                self.pay_card(int(d), int(sc), round(float(x), 2), int(mid), int(e), f"{cat}_increase" if e else None)
                if cat in ("medical", "dentist"):
                    self.transfer_in(int(d) + int(rng.integers(4, 16)), round(float(x) * (0.75 if cat == "medical" else 0.5), 2),
                                     self.mutuality, "social_security", "health_refund", "REFUND HEALTH CARE")

    def _prefs(self, cat):
        rng, M = self.rng, self.M
        local = []
        if cat in LOCAL_CATS:
            local = list(M.local.get((self.city, cat), []))
        chains = M.chain_ids(cat, self.region)
        ids = local + chains
        if not ids:
            return np.array([], dtype=int), np.array([])
        w = rng.dirichlet(np.full(len(ids), 0.5))
        if local and cat in LOCAL_CATS:
            share = LOCAL_CATS[cat]
            w[:len(local)] = w[:len(local)] / max(w[:len(local)].sum(), 1e-9) * share
            if chains:
                w[len(local):] = w[len(local):] / max(w[len(local):].sum(), 1e-9) * (1 - share)
        online_pref = self.t["online_shopper"]
        for i, mid in enumerate(ids):
            if M.get(mid)["is_online"]:
                w[i] *= 0.3 + 1.5 * online_pref
        return np.array(ids), w / w.sum()

    def _fixed_monthly(self):
        """Rough monthly fixed costs on START, used to calibrate day-to-day spending."""
        c = self.L.c
        days = np.array(c["day"])
        amounts = np.array(c["amount"])
        acct = np.array(c["account"])
        cats = np.array(c["category"], dtype=object)
        mask = (days < 365) & (amounts < 0) & (acct == "current") & np.isin(cats, [
            "rent", "mortgage", "energy", "water", "telecom", "insurance", "streaming", "gym", "bank_fees",
            "health_insurance", "childcare", "school", "car_loan", "charity", "tax", "property_tax", "road_tax",
            "social_contributions", "family_support", "own_transfer"])
        return float(-amounts[mask].sum() / 12) if mask.any() else 0.0

    # ------------------------------------------------------------------ credit card
    def emit_card_settlement(self):
        if "credit_card" not in self.accounts:
            return
        c = self.L.c
        acct = np.array(c["account"])
        days = np.array(c["day"])
        amounts = np.array(c["amount"])
        mask = acct == "credit_card"
        for k in range(1, len(MONTHS)):
            y, m, first, last = MONTHS[k - 1]
            spent = -amounts[mask & (days >= first) & (days <= last)].sum()
            if spent > 0:
                d = business_on_or_after(MONTHS[k][2] + 4)
                if d < NDAYS:
                    self.L.add("current", d, 7200, -round(spent, 2), "card_settlement", "direct_debit", "KBC Bank",
                               "bank", f"CREDIT CARD STATEMENT {m:02d}/{y}", recurring=True)
                    self.L.add("credit_card", d, 7200, round(spent, 2), "card_settlement", "direct_debit",
                               "Own current account", "own_account", "PAYMENT RECEIVED", recurring=True)

    # ------------------------------------------------------------------ balances
    def finalize(self):
        p, t, rng = self.p, self.t, self.rng
        c = self.L.c
        acct = np.array(c["account"], dtype=object)
        day = np.array(c["day"])
        amount = np.array(c["amount"])
        for key in set(acct.tolist()):
            if key not in self.accounts:
                self.open_account(key, 0)
        income_ref = max(self.income_at(0), self.income_at(NDAYS - 1), 800)
        has_sav = "savings" in self.accounts
        sav_open = self.accounts["savings"]["opened_day"] if has_sav else FAR
        cur_day = np.bincount(day[acct == "current"], weights=amount[acct == "current"], minlength=NDAYS)
        sav_day = np.bincount(day[acct == "savings"], weights=amount[acct == "savings"], minlength=NDAYS) if has_sav else np.zeros(NDAYS)
        cur = self.accounts["current"]["opening"]
        sav = self.accounts["savings"]["opening"] if has_sav else 0.0
        demo = bool(self.targets)
        month_last = {m[3] for m in MONTHS}
        buffer = max(700.0, income_ref)
        floor = -1500.0 if t["overdraft_ok"] else -100.0
        for d in range(NDAYS):
            need = self.fund_needs[d]
            if need > 0 and has_sav and d >= sav_open and sav > 0 and not demo:
                x = round(min(need + 200, sav), -1) if sav > need else round(sav, 2)
                if x > 0:
                    self.internal(d, x, "savings", "current", "", sec=6 * 3600)
                    cur += x
                    sav -= x
            cur += cur_day[d]
            sav += sav_day[d]
            if MONTH[d] == 1 and (d == 0 or MONTH[d - 1] == 12) and has_sav and sav > 0 and d >= sav_open:
                interest = round(sav * float(rng.uniform(0.007, 0.013)), 2)
                if interest > 0:
                    self.L.add("savings", d, 3600, interest, "interest", "interest", "KBC Bank", "bank",
                               f"INTEREST AND FIDELITY PREMIUM {YEAR[d] - 1}")
                    sav += interest
            if demo:
                continue
            if d in month_last and has_sav and d >= sav_open:
                if t["sweeper"] and cur > 2.2 * buffer:
                    x = round((cur - 1.2 * buffer) * float(rng.uniform(0.5, 0.9)), -1)
                    if x > 0:
                        self.internal(d, x, "current", "savings", "", sec=20 * 3600)
                        cur -= x
                        sav += x
            if cur < floor and has_sav and d >= sav_open and sav > 50:
                x = round(min(sav, buffer - cur), -1) if sav > buffer - cur else round(sav, 2)
                if x > 0:
                    self.internal(d, x, "savings", "current", "", sec=23 * 3600)
                    cur += x
                    sav -= x
        return self._rows()

    def _rows(self):
        p, rng = self.p, self.rng
        c = self.L.c
        n = len(c["day"])
        acct = np.array(c["account"], dtype=object)
        day = np.array(c["day"], dtype=np.int64)
        sec = np.array(c["sec"], dtype=np.int64)
        amount = np.array(c["amount"])
        order = np.lexsort((sec, day))
        ts = day * 86400 + sec
        balances = np.zeros(n)
        final = {}
        for key, a in self.accounts.items():
            idx = order[acct[order] == key]
            flows = amount[idx]
            opening = a["opening"]
            if self.targets and key in self.targets:
                opening = self.targets[key][0] - flows.sum()
            elif key == "current":
                run = opening + np.cumsum(flows) if len(flows) else np.array([opening])
                floor = -1500.0 if self.t["overdraft_ok"] else -100.0
                if run.min() < floor:
                    opening += floor - run.min() + float(rng.uniform(100, 900))
            elif key in ("savings", "pension_savings", "long_term_savings", "investment_plan", "child_savings",
                         "rental_guarantee"):
                run = opening + np.cumsum(flows) if len(flows) else np.array([opening])
                if run.min() < 0:
                    opening += -run.min() + float(rng.uniform(0, 300))
            a["opening"] = round(float(opening), 2)
            balances[idx] = np.round(opening + np.cumsum(flows), 2)
            final[key] = round(float(opening + flows.sum()), 2)
        return {"order": order, "ts": ts, "balances": balances, "final": final, "acct": acct, "day": day}
