"""Merchant registry shared by all customers (built once, deterministic)."""
import numpy as np

from . import reference as R

_REGISTRY = None

# Chains that only operate in some regions
REGION_ONLY = {"Albert Heijn": {"FL", "BR"}, "Jumbo": {"FL", "BR"}, "Intermarché": {"WA", "BR"},
               "De Lijn": {"FL"}, "STIB-MIVB": {"BR"}, "TEC": {"WA"}, "DATS 24": {"FL", "BR"},
               "Okay": {"FL", "BR"}, "Bio-Planet": {"FL", "BR"}}


class Registry:
    def __init__(self):
        rng = np.random.default_rng(20260930)
        self.rows = []                      # merchant_id, name, category, mcc, is_online, city, country
        self.chains = {}                    # category -> [merchant ids]
        self.local = {}                     # (city, category) -> [merchant ids]
        self.foreign = {}                   # (country, category) -> [merchant ids]
        self.by_name = {}
        for name, cat, online in R.CHAINS:
            mid = self._add(name, cat, online, None, "BE")
            self.chains.setdefault(cat, []).append(mid)
            self.by_name[name] = mid
        for city, postcode, prov, region, _ in R.CITIES:
            lang = "nl" if region == "FL" else "fr"
            pool = R.LAST_NAMES[lang] + R.LAST_NAMES["other"][:6]
            for cat, templates in R.LOCAL_TEMPLATES.items():
                for tpl in templates[lang]:
                    name = tpl.format(s=pool[rng.integers(len(pool))], c=city)
                    mid = self._add(name, cat, False, city, "BE")
                    self.local.setdefault((city, cat), []).append(mid)
            for hosp in R.HOSPITALS[region]:
                key = (hosp, "hospital")
                if key not in self.by_name:
                    self.by_name[key] = self._add(hosp, "hospital", False, None, "BE")
            for uni in R.UNIVERSITIES[region]:
                if (uni, "education") not in self.by_name:
                    self.by_name[(uni, "education")] = self._add(uni, "education", False, None, "BE")
        for country in R.COUNTRIES_ABROAD:
            for cat, names in R.FOREIGN_MERCHANTS.items():
                for name in rng.choice(names, size=min(3, len(names)), replace=False):
                    mid = self._add(str(name), cat, False, None, country)
                    self.foreign.setdefault((country, cat), []).append(mid)

    def _add(self, name, cat, online, city, country):
        mid = len(self.rows) + 1
        self.rows.append({"merchant_id": mid, "name": name, "category": cat, "mcc": R.CATEGORY_MCC.get(cat, 5999),
                          "is_online": bool(online), "city": city, "country": country})
        return mid

    def get(self, mid):
        return self.rows[mid - 1]

    def chain_ids(self, cat, region=None, online=None):
        out = []
        for mid in self.chains.get(cat, []):
            r = self.rows[mid - 1]
            if region and r["name"] in REGION_ONLY and region not in REGION_ONLY[r["name"]]:
                continue
            if online is not None and r["is_online"] != online:
                continue
            out.append(mid)
        return out

    def hospital(self, region, rng):
        names = R.HOSPITALS[region]
        return self.by_name[(names[rng.integers(len(names))], "hospital")]

    def university(self, region, rng):
        names = R.UNIVERSITIES[region]
        return self.by_name[(names[rng.integers(len(names))], "education")]


def registry() -> Registry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = Registry()
    return _REGISTRY
