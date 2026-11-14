"""Turns daily weather into the few numbers and sentences the app shows.

Every sentence here is computed from the data. "Usual" always means the 2001-2020 average.
"""
from datetime import date, timedelta
from statistics import mean

BASE = range(2001, 2021)  # the "usual" period
BASE_LABEL = "usual = 2001-2020 average"
SOURCE = "NASA POWER (MERRA-2)"
RES = "~50 km"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _d(key: str) -> date:
    return date(int(key[:4]), int(key[4:6]), int(key[6:]))


class Weather:
    def __init__(self, days: dict[str, dict[str, float]]):
        self.days = {_d(k): v for k, v in days.items()}
        self.last = max(self.days)  # last day with data

    # ---- helpers ----
    def _values(self, name, start: date, end: date):
        out, d = [], start
        while d <= end:
            v = self.days.get(d, {}).get(name)
            if v is not None:
                out.append(v)
            d += timedelta(days=1)
        return out

    def _sum(self, name, start, end, min_days):
        v = self._values(name, start, end)
        return sum(v) if len(v) >= min_days else None

    def _mean(self, name, start, end, min_days):
        v = self._values(name, start, end)
        return mean(v) if len(v) >= min_days else None

    def complete_years(self):
        return [y for y in range(2001, self.last.year + 1) if self._sum("rain", date(y, 1, 1), date(y, 12, 31), 360) is not None]

    # ---- yearly rain ----
    def rain_by_year(self) -> dict[int, float]:
        return {y: self._sum("rain", date(y, 1, 1), date(y, 12, 31), 360) for y in self.complete_years()}

    # ---- summer (June-August) mean temperature ----
    def summer_temp_by_year(self) -> dict[int, float]:
        out = {}
        for y in range(2001, self.last.year + 1):
            hi = self._mean("tmax", date(y, 6, 1), date(y, 8, 31), 85)
            lo = self._mean("tmin", date(y, 6, 1), date(y, 8, 31), 85)
            if hi is not None and lo is not None:
                out[y] = (hi + lo) / 2
        return out

    # ---- July rain ----
    def july_rain_by_year(self) -> dict[int, float]:
        out = {}
        for y in range(2001, self.last.year + 1):
            s = self._sum("rain", date(y, 7, 1), date(y, 7, 31), 29)
            if s is not None:
                out[y] = s
        return out

    # ---- soil wetness by month, this year against usual ----
    def soil_by_month(self):
        y = self.last.year
        months = [m for m in range(1, 13) if self._month_complete(y, m)]
        this = [self._month_mean("soil", y, m) for m in months]
        usual = [mean(v for v in (self._month_mean("soil", b, m) for b in BASE) if v is not None) for m in months]
        return months, this, usual

    def _month_end(self, y, m):
        return date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)

    def _month_complete(self, y, m):
        return self._month_end(y, m) <= self.last and self._month_mean("soil", y, m) is not None

    def _month_mean(self, name, y, m):
        return self._mean(name, date(y, m, 1), self._month_end(y, m), 25)

    # ---- the last 30 days against the same 30 days in usual years ----
    def _same_window(self, year, days):
        try:
            end = self.last.replace(year=year)
        except ValueError:  # 29 February
            end = self.last.replace(year=year, day=28)
        return end - timedelta(days=days - 1), end

    def rain_last_30(self):
        now = self._sum("rain", self.last - timedelta(days=29), self.last, 27)
        usual = mean(v for v in (self._sum("rain", *self._same_window(b, 30), 27) for b in BASE) if v is not None)
        return now, usual

    def soil_now(self):
        """Mean of the last 7 days, and where it sits among the same week of usual years (0..1)."""
        now = self._mean("soil", self.last - timedelta(days=6), self.last, 5)
        past = sorted(v for v in (self._mean("soil", *self._same_window(b, 7), 5) for b in BASE) if v is not None)
        rank = sum(1 for v in past if v < now) / len(past)
        return now, rank


def _base_mean(by_year: dict[int, float]) -> float:
    return mean(v for y, v in by_year.items() if y in BASE)


def _yy(years):
    return [f"'{str(y)[2:]}" for y in years]


def insight_cards(w: Weather) -> list[dict]:
    cards = []
    src = {"name": f"{SOURCE} · {RES}", "detail": BASE_LABEL}

    # rain per year
    rain = w.rain_by_year()
    years = sorted(rain)[-10:]
    y = years[-1]
    pct = (rain[y] / _base_mean(rain) - 1) * 100
    if pct <= -10:
        take = f"{y} had {abs(pct):.0f}% less rain than usual here."
    elif pct >= 10:
        take = f"{y} had {pct:.0f}% more rain than usual here."
    else:
        take = f"{y} had about the usual amount of rain here."
    cards.append({"id": "rain", "scope": "area", "takeaway": take, "series": {
        "kind": "bar", "title": "Rain per year, mm", "labels": _yy(years), "values": [round(rain[k]) for k in years],
        "highlightIndex": len(years) - 1, "source": src}})

    # summer temperature
    temp = w.summer_temp_by_year()
    years = sorted(temp)[-10:]
    y = years[-1]
    diff = temp[y] - _base_mean(temp)
    if diff >= 0.5:
        take = f"Summer {y} was {diff:.1f} °C warmer than usual here."
    elif diff <= -0.5:
        take = f"Summer {y} was {abs(diff):.1f} °C cooler than usual here."
    else:
        take = f"Summer {y} was about as warm as usual here."
    cards.append({"id": "temp", "scope": "area", "takeaway": take, "series": {
        "kind": "line", "title": "Average temperature, June to August, °C", "labels": _yy(years),
        "values": [round(temp[k], 1) for k in years], "highlightIndex": len(years) - 1, "source": src}})

    # soil wetness this year
    months, this, usual = w.soil_by_month()
    if months:
        # July to September is when crops run short of water; judge that window once it is complete
        season = [i for i, m in enumerate(months) if 7 <= m <= 9]
        span = "from July to September"
        if len(season) < 3:
            season, span = list(range(len(months))), "so far this year"
        rel = mean(this[i] for i in season) / mean(usual[i] for i in season) - 1
        if rel <= -0.05:
            take = f"The soil in your area was drier than usual {span}."
        elif rel >= 0.05:
            take = f"The soil in your area was wetter than usual {span}."
        else:
            take = f"The soil in your area was about as wet as usual {span}."
        cards.append({"id": "soil", "scope": "area", "takeaway": take, "series": {
            "kind": "line", "title": "Water in the root zone of the soil (0 = dry, 1 = soaked)",
            "labels": [MONTHS[m - 1] for m in months], "values": [round(v, 2) for v in this], "usual": [round(v, 2) for v in usual],
            "valuesLabel": str(w.last.year), "usualLabel": "Usual",
            "source": {"name": f"{SOURCE} · {RES}", "detail": f"model estimate · {BASE_LABEL}"}}})
    return cards


def overview_stats(w: Weather) -> list[dict]:
    now, usual = w.rain_last_30()
    ratio = now / usual if usual else 1
    note = "Less than usual" if ratio < 0.75 else "More than usual" if ratio > 1.25 else "About usual"
    stats = [{"id": "rain", "label": "Rain in your area, 30 days", "value": f"{now:.0f} mm",
              "note": f"{note}: usually {usual:.0f} mm", "warn": ratio < 0.75}]
    _, rank = w.soil_now()
    level = "Low" if rank < 1 / 3 else "High" if rank > 2 / 3 else "Normal"
    stats.append({"id": "soil", "label": "Water in the soil", "value": level, "note": "Estimate for your area", "warn": level == "Low"})
    return stats


def july_card(w: Weather) -> tuple[str, dict]:
    """Sentence + chart used to explain a water-saving rotation."""
    july = w.july_rain_by_year()
    years = sorted(july)[-10:]
    base = _base_mean(july)
    recent = mean(july[y] for y in years[-5:])
    r = recent / base - 1
    if r <= -0.10:
        text = "Julys here have been drier than usual lately."
    elif r >= 0.10:
        text = "Julys here have been wetter than usual lately."
    else:
        text = "July rain here has been close to usual lately."
    series = {"kind": "bar", "title": "July rain in your area, mm", "labels": _yy(years), "values": [round(july[y]) for y in years],
              "highlightIndex": len(years) - 1, "source": {"name": f"{SOURCE} · {RES}", "detail": f"usual July = {base:.0f} mm (2001-2020)"}}
    return text, series
