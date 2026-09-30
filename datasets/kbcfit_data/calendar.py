"""Simulation window and day-index helpers. Day 0 is START; every date is an int day index."""
from datetime import date, datetime, timedelta, timezone

import numpy as np

START = date(2024, 10, 1)
END = date(2026, 9, 30)
NDAYS = (END - START).days + 1

EPOCH0 = int(datetime(START.year, START.month, START.day, tzinfo=timezone.utc).timestamp())

_days = np.arange(NDAYS)
_dates = np.datetime64(START.isoformat()) + _days
DOW = (_days + START.weekday()) % 7                    # 0 = Monday
MONTH = _dates.astype("datetime64[M]").astype(int) % 12 + 1
YEAR = _dates.astype("datetime64[Y]").astype(int) + 1970
DOM = (_dates - _dates.astype("datetime64[M]")).astype(int) + 1

# (year, month, first day index, last day index) for every month in the window
MONTHS = []
_d = START
while _d <= END:
    nxt = date(_d.year + (_d.month == 12), _d.month % 12 + 1, 1)
    MONTHS.append((_d.year, _d.month, (_d - START).days, min((nxt - START).days - 1, NDAYS - 1)))
    _d = nxt

# Belgian public holidays inside the window (banks do not book on these days)
_HOLIDAYS = {date(2024, 11, 1), date(2024, 11, 11), date(2024, 12, 25), date(2025, 1, 1), date(2025, 4, 21),
             date(2025, 5, 1), date(2025, 5, 29), date(2025, 6, 9), date(2025, 7, 21), date(2025, 8, 15),
             date(2025, 11, 1), date(2025, 11, 11), date(2025, 12, 25), date(2026, 1, 1), date(2026, 4, 6),
             date(2026, 5, 1), date(2026, 5, 14), date(2026, 5, 25), date(2026, 7, 21), date(2026, 8, 15)}
IS_BUSINESS = np.array([DOW[i] < 5 and (START + timedelta(days=int(i))) not in _HOLIDAYS for i in range(NDAYS)])

# School holidays (approximate, Flemish calendar) used for family trips
SCHOOL_HOLIDAY = np.zeros(NDAYS, dtype=bool)
for a, b in [((2024, 10, 28), (2024, 11, 3)), ((2024, 12, 23), (2025, 1, 5)), ((2025, 3, 3), (2025, 3, 9)),
             ((2025, 4, 7), (2025, 4, 21)), ((2025, 7, 1), (2025, 8, 31)), ((2025, 10, 27), (2025, 11, 2)),
             ((2025, 12, 22), (2026, 1, 4)), ((2026, 2, 16), (2026, 2, 22)), ((2026, 4, 6), (2026, 4, 19)),
             ((2026, 7, 1), (2026, 8, 31))]:
    SCHOOL_HOLIDAY[(date(*a) - START).days:(date(*b) - START).days + 1] = True


def day_of(d: date) -> int:
    return (d - START).days


def to_date(i: int) -> date:
    return START + timedelta(days=int(i))


def iso(i: int) -> str:
    return to_date(i).isoformat()


def business_on_or_after(i: int) -> int:
    while 0 <= i < NDAYS and not IS_BUSINESS[i]:
        i += 1
    return i


def business_on_or_before(i: int) -> int:
    while 0 <= i < NDAYS and not IS_BUSINESS[i]:
        i -= 1
    return i


def month_day(month_idx: int, dom: int) -> int:
    """Day index of day `dom` in month number `month_idx` of MONTHS (clamped to the month)."""
    y, m, first, last = MONTHS[month_idx]
    return min(first + dom - 1, last)


def month_index_of(i: int) -> int:
    for k, (_, _, first, last) in enumerate(MONTHS):
        if first <= i <= last:
            return k
    return -1 if i < 0 else len(MONTHS)


def age_at(birth: date, i: int) -> float:
    return (to_date(i) - birth).days / 365.25
