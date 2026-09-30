"""Customer profiles as they stand on START (day 0), before any life event of the window."""
from datetime import date, timedelta

import numpy as np

from . import reference as R
from .calendar import END, START

ARCHETYPES = {
    "student": (0.07, 18, 23), "starter": (0.12, 22, 29), "couple": (0.10, 25, 38),
    "young_family": (0.16, 27, 42), "family": (0.15, 40, 56), "single": (0.10, 29, 62),
    "empty_nester": (0.12, 52, 66), "retiree": (0.18, 66, 90),
}
EMPLOYMENT = {
    "starter": {"employee": .78, "civil_servant": .10, "self_employed": .04, "unemployed": .08},
    "adult": {"employee": .70, "civil_servant": .15, "self_employed": .10, "unemployed": .05},
    "empty_nester": {"employee": .60, "civil_servant": .15, "self_employed": .12, "unemployed": .05, "retired": .08},
}
HOUSING = {
    "student": {"with_parents": .7, "student_room": .3},
    "starter": {"with_parents": .35, "tenant": .58, "owner_mortgage": .07},
    "couple": {"tenant": .50, "owner_mortgage": .48, "owner": .02},
    "young_family": {"owner_mortgage": .68, "tenant": .30, "owner": .02},
    "family": {"owner_mortgage": .55, "owner": .30, "tenant": .15},
    "single": {"tenant": .50, "owner_mortgage": .33, "owner": .17},
    "empty_nester": {"owner": .60, "owner_mortgage": .28, "tenant": .12},
    "retiree": {"owner": .78, "tenant": .20, "owner_mortgage": .02},
}
OTHER_BANKS = ["Belfius", "BNP Paribas Fortis", "ING", "Argenta", "Crelan"]

_CITIES_BY_REGION = {r: [c for c in R.CITIES if c[3] == r] for r in ("FL", "BR", "WA")}


def pick(rng, options):
    """Pick a key from {option: weight} or an element from a list."""
    if isinstance(options, dict):
        keys = list(options)
        w = np.array(list(options.values()), dtype=float)
        return keys[rng.choice(len(keys), p=w / w.sum())]
    return options[rng.integers(len(options))]


def lognormal(rng, median, sigma):
    return float(median * np.exp(sigma * rng.standard_normal()))


def _generation(birth_year):
    return "young" if birth_year >= 1996 else "mid" if birth_year >= 1971 else "old"


def _income(rng, employment, age):
    if employment == "student":
        return round(lognormal(rng, 320, 0.5), 0)
    if employment == "unemployed":
        return round(float(rng.uniform(1150, 1550)), 0)
    if employment == "retired":
        return round(max(1150.0, lognormal(rng, 1750, 0.28)), 0)
    median = 2000 if age < 26 else 2300 if age < 31 else 2600 if age < 41 else 2900 if age < 56 else 3000
    sigma = {"employee": .25, "civil_servant": .17, "self_employed": .50}[employment]
    return round(max(1450.0, lognormal(rng, median, sigma)), 0)


def _employer(rng, employment, region):
    if employment == "civil_servant":
        return pick(rng, R.PUBLIC_EMPLOYERS[region]), "public"
    if employment == "student":
        return pick(rng, R.TEMP_AGENCIES), "temp_work"
    if employment in ("employee", "self_employed"):
        prefix = pick(rng, R.EMPLOYER_PREFIX)
        name, sector = R.EMPLOYER_SECTOR[rng.integers(len(R.EMPLOYER_SECTOR))]
        return f"{prefix} {name} {pick(rng, R.EMPLOYER_FORMS)}", sector
    return None, None


def new_employer(rng, region):
    return _employer(rng, "employee", region)


def generate_customer(idx: int, rng: np.random.Generator) -> dict:
    arche = pick(rng, {k: v[0] for k, v in ARCHETYPES.items()})
    _, lo, hi = ARCHETYPES[arche]
    age = float(rng.triangular(lo, lo, hi + 1)) if arche == "retiree" else float(rng.uniform(lo, hi + 1))
    birth = START - timedelta(days=int(age * 365.25))

    region = pick(rng, R.REGION_WEIGHTS)
    cities = _CITIES_BY_REGION[region]
    city = cities[rng.choice(len(cities), p=np.array([c[4] for c in cities]) / sum(c[4] for c in cities))]
    language = pick(rng, R.REGION_LANGUAGES[region])

    gender = "X" if rng.random() < 0.003 else ("F" if rng.random() < 0.51 else "M")
    gen = _generation(birth.year)
    first = pick(rng, R.FIRST_NAMES[(gen, gender if gender != "X" else pick(rng, ["M", "F"]))])
    other_p = {"BR": .30, "FL": .09, "WA": .12}[region]
    last_pool = "other" if rng.random() < other_p else ("nl" if region == "FL" or (region == "BR" and language == "nl") else "fr")
    last = pick(rng, R.LAST_NAMES[last_pool])

    if arche == "student":
        employment = "student"
    elif arche == "retiree":
        employment = "retired"
    elif arche in ("starter", "empty_nester"):
        employment = pick(rng, EMPLOYMENT[arche])
    else:
        employment = pick(rng, EMPLOYMENT["adult"])
    employer, sector = _employer(rng, employment, region)
    income = _income(rng, employment, age)

    partner_p = {"student": .05, "starter": .25, "couple": 1.0, "young_family": .88, "family": .80, "single": 0.0,
                 "empty_nester": .78, "retiree": .70 if age < 75 else .45}[arche]
    partner = bool(rng.random() < partner_p)
    if partner:
        marital = "married" if rng.random() < (0.35 if age < 32 else 0.6 if age < 50 else 0.8) else "cohabiting"
    else:
        marital = ("widowed" if age > 70 and rng.random() < 0.55 else
                   "divorced" if age > 35 and rng.random() < 0.35 else "single")

    # children living in the household
    children = []
    if arche == "young_family":
        n = pick(rng, {1: .42, 2: .43, 3: .15})
        youngest = float(rng.uniform(0.3, 6))
    elif arche == "family":
        n = pick(rng, {1: .30, 2: .50, 3: .20})
        youngest = float(rng.uniform(5, 16))
    elif arche == "single" and rng.random() < 0.25:
        n, youngest = pick(rng, {1: .6, 2: .4}), float(rng.uniform(3, 15))
    else:
        n, youngest = 0, 0.0
    for k in range(n):
        child_age = youngest + k * float(rng.uniform(1.5, 4))
        if child_age < 23:
            children.append(START - timedelta(days=int(child_age * 365.25)))
    adult_children = int(rng.integers(1, 4)) if arche in ("empty_nester", "retiree") and rng.random() < 0.85 else 0

    housing = pick(rng, HOUSING[arche])
    if housing == "with_parents" and partner:
        housing = "tenant"
    rent_base = {"FL": 1.0, "BR": 1.18, "WA": 0.88}[region]
    hh_size = 1 + int(partner) + len(children)
    rent = 0.0
    if housing == "tenant":
        rent = round(rent_base * (720 + 110 * (hh_size - 1)) * float(rng.uniform(0.85, 1.3)), 0)
    elif housing == "student_room":
        rent = round(float(rng.uniform(380, 560)), 0)
    elif housing == "with_parents":
        rent = float(pick(rng, [0, 0, 100, 150, 200]))
    mortgage = None
    if housing == "owner_mortgage":
        mortgage = {"monthly": round(float(rng.uniform(620, 1450)) * (1.1 if partner else 0.85), 0),
                    "lender": "KBC" if rng.random() < 0.8 else pick(rng, OTHER_BANKS),
                    "remaining_years": int(rng.integers(5, 25))}

    car_p = {"student": .12, "retiree": .65 if age < 80 else .3}.get(arche, .80) * (0.6 if region == "BR" else 1.0)
    has_car = bool(rng.random() < car_p)
    n_cars = 2 if has_car and partner and rng.random() < 0.35 else int(has_car)

    young = age < 35
    digital = float(np.clip(rng.beta(6, 2) if age < 30 else rng.beta(5, 2.5) if age < 50 else
                            rng.beta(3, 3) if age < 66 else rng.beta(2, 4), 0, 1))
    if age > 74 and rng.random() < 0.5 or age > 66 and rng.random() < 0.2:
        digital = 0.0                                   # banks at the branch, no app
    idle_p = {"retiree": .40, "empty_nester": .15}.get(arche, .04)
    well_covered = bool(30 <= age <= 60 and income > 2700 and rng.random() < 0.12)

    traits = {
        "eats_out": lognormal(rng, 1.3 if young else 0.9, 0.45),
        "online_shopper": float(np.clip(rng.beta(4, 2) if young else rng.beta(2, 3) if age < 60 else rng.beta(1.2, 5), 0, 1)),
        "cash_user": float(np.clip(rng.beta(1.2, 6) if young else rng.beta(2, 4) if age < 66 else rng.beta(4, 3), 0, 1)),
        "sporty": bool(rng.random() < (0.35 if young else 0.2)),
        "traveler": float(np.clip(rng.beta(2, 2.5) * (income / 2500) ** 0.5, 0, 1.5)),
        "frugal": float(rng.uniform(0.75, 1.25)),
        "has_pet": bool(rng.random() < (0.40 if children else 0.28)),
        "saver": bool(rng.random() < (0.35 if arche == "student" else 0.62)),
        "savings_rate": float(rng.uniform(0.03, 0.18)),
        "sweeper": bool(rng.random() < 0.55),
        "idle_cash": bool(rng.random() < idle_p),
        "digital_affinity": round(digital, 3),
        "smokes": bool(rng.random() < 0.14),
        "gambler": bool(rng.random() < 0.08),
        "charity_donor": bool(rng.random() < 0.18),
        "overdraft_ok": bool(rng.random() < 0.3),
        "partner_banks_elsewhere": bool(partner and rng.random() < 0.35),
        "well_covered": well_covered,
    }
    if traits["idle_cash"]:
        traits["sweeper"] = False

    months_saved = lognormal(rng, 1.2 if age < 25 else 3.5 if age < 35 else 6 if age < 50 else 11 if age < 66 else 16, 0.9)
    savings = round(min(months_saved * income, 400_000), 0) if rng.random() < 0.9 else 0.0
    current = round(float(rng.uniform(0.3, 1.6)) * income, 0)
    if traits["idle_cash"]:
        current = round(float(rng.uniform(8, 30)) * income, 0)
        savings = round(savings * 0.4, 0)

    since_years = float(rng.uniform(0.5, max(1.0, min(age - 16, 45))))
    customer_since = START - timedelta(days=int(since_years * 365.25))

    prof = {
        "idx": idx, "customer_id": f"C{idx:07d}", "demo_persona": None,
        "first_name": first, "last_name": last, "gender": gender, "birth_date": birth, "age_start": age,
        "city": city[0], "postcode": city[1], "province": city[2], "region": region, "language": language,
        "archetype": arche, "employment": employment, "employer": employer, "sector": sector, "income": income,
        "partner": partner, "marital_status": marital, "children": children, "adult_children": adult_children,
        "housing": housing, "rent": rent, "mortgage": mortgage, "has_car": has_car, "n_cars": n_cars,
        "traits": traits, "savings_start": savings, "current_start": current, "customer_since": customer_since,
        "risk_profile": pick(rng, {"defensive": .35, "neutral": .35, "dynamic": .15, "not_assessed": .15}),
        "consent_personalisation": bool(rng.random() < 0.82),
        "consent_analytics": bool(rng.random() < 0.78),
        "consent_marketing": bool(rng.random() < 0.52),
        "landlord": _landlord(rng, language),
        "card_last4": f"{rng.integers(0, 10000):04d}",
    }
    prof["products"] = initial_products(prof, rng)
    return prof


def _landlord(rng, language):
    if rng.random() < 0.35:
        return pick(rng, ["Immo Vastgoedbeheer BV", "Home Invest Belgium", "Immobilière du Parc SRL", "Woonhaven",
                          "Residentie Beheer NV", "Sociale Huisvesting"])
    pool = R.LAST_NAMES["nl" if language == "nl" else "fr"]
    return f"{pick(rng, ['J.', 'M.', 'A.', 'P.', 'L.', 'S.'])} {pick(rng, pool)}"


def initial_products(p: dict, rng) -> dict:
    """Products held on START. KBC products become accounts or contracts; external ones only show as payments."""
    age, inc, t = p["age_start"], p["income"], p["traits"]
    wc = t["well_covered"]
    prods = {"current": "KBC"}
    if wc or rng.random() < (0.60 if p["archetype"] == "student" else 0.88):
        prods["savings"] = "KBC"
    if 18 <= age < 64:
        pp = 0.08 if age < 25 else 0.35 if age < 35 else 0.50 if age < 55 else 0.55
        if wc or rng.random() < pp * min(1.3, inc / 2500):
            prods["pension_savings"] = "KBC"
    if age >= 28 and (wc or rng.random() < 0.10 * min(2, inc / 2500)):
        prods["long_term_savings"] = "KBC"
    if age >= 25 and (wc or rng.random() < 0.08 * min(2.5, inc / 2500) + (0.2 if t["idle_cash"] else 0)):
        prods["investment_plan"] = "KBC"
    if age >= 21 and (wc or rng.random() < 0.45):
        prods["credit_card"] = "KBC"
    if p["mortgage"]:
        prods["home_loan"] = "KBC" if p["mortgage"]["lender"] == "KBC" else "external"
    if p["has_car"] and rng.random() < 0.18:
        prods["car_loan"] = "KBC" if rng.random() < 0.6 else "external"

    def ins(name, p_have, p_kbc):
        if wc:
            prods[name] = "KBC"
        elif rng.random() < p_have:
            prods[name] = "KBC" if rng.random() < p_kbc else "external"

    owner = p["housing"] in ("owner", "owner_mortgage")
    if p["housing"] != "with_parents":
        ins("home_insurance", 0.93 if owner else 0.55, 0.60)
    if p["has_car"]:
        ins("car_insurance", 1.0, 0.45)
    ins("family_liability", 0.62 if p["housing"] != "with_parents" else 0.2, 0.55)
    ins("hospitalisation", 0.35, 0.50)       # many more are covered through their employer, invisible to the bank
    if p["mortgage"]:
        ins("outstanding_balance_insurance", 0.92, 0.75 if prods.get("home_loan") == "KBC" else 0.1)
    if age >= 30 and rng.random() < 0.08:
        ins("life_insurance", 1.0, 0.6)
    return prods


# ---------------------------------------------------------------------------
# The four demo personas of the KBC Fit site, built so the demo numbers hold at END
# ---------------------------------------------------------------------------
DEMO_PERSONAS = ["lucas", "thomas", "monique", "claire"]


def demo_customer(idx: int, persona: str, rng) -> dict:
    p = generate_customer(idx, rng)
    t = p["traits"]
    t.update({"idle_cash": False, "sweeper": False, "saver": False, "well_covered": False, "overdraft_ok": False,
              "partner_banks_elsewhere": False, "gambler": False})
    base = {"region": "FL", "language": "nl", "consent_personalisation": True, "consent_analytics": True,
            "consent_marketing": True, "demo_persona": persona}
    if persona == "lucas":
        # student room in Gent, first job on 2026-03-01 (7 months with the same employer on END)
        base.update(first_name="Lucas", last_name="Peeters", gender="M", birth_date=date(2002, 5, 14),
                    city="Gent", postcode="9000", province="Oost-Vlaanderen", archetype="student",
                    employment="student", employer="Randstad Belgium", sector="temp_work", income=420.0,
                    partner=False, marital_status="single", children=[], housing="student_room", rent=460.0,
                    mortgage=None, has_car=False, n_cars=0)
        t.update(digital_affinity=0.92, online_shopper=0.8, eats_out=1.3, traveler=0.35, cash_user=0.05, has_pet=False)
    elif persona == "thomas":
        # homeowner in Leuven, saves every month, his first child was born on 2026-08-24 (declared in the app)
        base.update(first_name="Thomas", last_name="Wouters", gender="M", birth_date=date(1995, 3, 2),
                    city="Leuven", postcode="3000", province="Vlaams-Brabant", archetype="couple",
                    employment="employee", income=2550.0, partner=True, marital_status="cohabiting", children=[],
                    housing="owner_mortgage", rent=0.0, mortgage={"monthly": 690.0, "lender": "KBC", "remaining_years": 22},
                    has_car=True, n_cars=1)
        t.update(digital_affinity=0.85, traveler=0.5, has_pet=False, smokes=False, saver=True, savings_rate=0.06)
    elif persona == "monique":
        # retired before the window: two stable years of pension income and ~2,400 EUR spending a month
        base.update(first_name="Monique", last_name="Janssens", gender="F", birth_date=date(1960, 6, 20),
                    city="Hasselt", postcode="3500", province="Limburg", archetype="retiree",
                    employment="retired", employer=None, sector=None, income=2380.0, partner=False,
                    marital_status="widowed", children=[], adult_children=2, housing="owner", rent=0.0, mortgage=None,
                    has_car=True, n_cars=1, spend_target_total=3100.0)
        t.update(digital_affinity=0.30, cash_user=0.7, eats_out=0.5, traveler=0.2, online_shopper=0.05,
                 has_pet=False, smokes=False, charity_donor=False, activity=0.35)
    elif persona == "claire":
        base.update(first_name="Claire", last_name="Mertens", gender="F", birth_date=date(1988, 1, 12),
                    city="Mechelen", postcode="2800", province="Antwerpen", archetype="young_family",
                    employment="self_employed", employer="Mertens Architecture", sector="services", income=3900.0,
                    partner=True, marital_status="married", children=[date(2016, 4, 3), date(2019, 9, 21)],
                    housing="owner_mortgage", rent=0.0, mortgage={"monthly": 1180.0, "lender": "KBC", "remaining_years": 17},
                    has_car=True, n_cars=1)
        t.update(digital_affinity=0.75, well_covered=True, saver=True, savings_rate=0.07)
    p.update(base)
    p["customer_id"] = f"C{idx:07d}"
    p["age_start"] = (START - p["birth_date"]).days / 365.25
    if persona == "thomas":
        p["employer"], p["sector"] = "Brightwave Software BV", "ict"
    prods = {
        "lucas": {"current": "KBC", "savings": "KBC"},
        "thomas": {"current": "KBC", "savings": "KBC", "credit_card": "KBC", "home_loan": "KBC", "home_insurance": "KBC",
                  "outstanding_balance_insurance": "KBC", "car_insurance": "external", "family_liability": "KBC"},
        "monique": {"current": "KBC", "savings": "KBC", "home_insurance": "KBC", "car_insurance": "KBC",
                 "family_liability": "KBC"},
        "claire": {k: "KBC" for k in ("current", "savings", "pension_savings", "long_term_savings", "investment_plan",
                                      "credit_card", "home_insurance", "car_insurance", "family_liability",
                                      "hospitalisation", "outstanding_balance_insurance", "home_loan",
                                      "income_protection_insurance")},
    }[persona]
    # balances on END and last digits taken from src/lib/data/personas.ts (the app's seed data)
    p["demo_targets"] = {
        "lucas": {"current": (2340, "4821"), "savings": (1800, "7730")},
        "thomas": {"current": (3120, "1954"), "savings": (2400, "6602")},
        "monique": {"current": (54400, "3307"), "savings": (3200, "9115")},
        "claire": {"current": (4870, "5540"), "savings": (18500, "2268"), "investment_plan": (32900, "8841"),
                   "pension_savings": (21300, "0417")},
    }[persona]
    p["products"] = prods
    return p


def age_on(p: dict, d: date) -> float:
    return (d - p["birth_date"]).days / 365.25


END_DATE = END
