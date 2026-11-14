"""What the satellites measured on one field, read from data/baked/<field id>/ (made by field_pull.py).

Everything here is a description of what was seen: how green the field is, and where inside the field it
is often less green. Nothing here says why. Thresholds are our own choices and are stored in profile.json.
"""
import json
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from statistics import mean, median

BAKED = Path(__file__).parent / "data" / "baked"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
RECENT_DAYS = 45       # an older reading is not presented as the state of the field
THIN_NDVI = 0.5        # between the bare-soil threshold and this: thin green cover
MIN_SQUARES = 10       # fewer clean squares inside the outline than this: the field is not read
WEAK_MIN_CELLS = 10    # fewer weak 10 m squares than this (0.1 ha) are not reported


@lru_cache(maxsize=None)
def profile(field_id: str):
    path = BAKED / field_id / "profile.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _ok(p, source: str) -> bool:
    return bool(p) and p.get("sources", {}).get(source, {}).get("status") == "ok"


def _week_date(year: int, week: int) -> date:
    return date(year, 1, 1) + timedelta(days=week * 7)  # the first day of the 7-day bin


def _latest(series):
    """(date, value) of the last week with a reading, or None."""
    for year in sorted(series, reverse=True):
        weeks = series[year]
        for week in range(len(weeks) - 1, -1, -1):
            if weeks[week] is not None:
                return _week_date(int(year), week), weeks[week]
    return None


def greenness(field_id: str, today: date | None = None):
    """The latest Sentinel-2 reading of the field, in words. None if there is no usable reading."""
    p = profile(field_id)
    if not _ok(p, "s2"):
        return None
    squares = p["static"]["s2"]["clean_pixels"]
    if squares < MIN_SQUARES:
        return {"too_small": True, "squares": squares, "recent": False}
    latest = _latest(p["weekly"]["ndvi_field_10m"])
    if not latest:
        return None
    when, value = latest
    bare = p["thresholds"]["bare_ndvi"]
    if value < bare:
        words, short = "bare soil or very little green", "Bare soil"
    elif value < THIN_NDVI:
        words, short = "a thin green cover", "Thin green cover"
    else:
        words, short = "a dense green cover", "Green cover"
    out = {"date": when, "ndvi": round(value, 2), "words": words, "short": short,
           "recent": ((today or date.today()) - when).days <= RECENT_DAYS,
           "squares": p["static"]["s2"]["clean_pixels"]}
    if _ok(p, "hls"):  # NASA's own 30 m reading of the same field, if it has one close in time
        nasa = _latest(p["weekly"]["ndvi_field_30m"])
        if nasa and abs((nasa[0] - when).days) <= 7 and p["static"]["hls"]["clean_pixels"] >= MIN_SQUARES:
            out["hls"] = {"date": nasa[0], "ndvi": round(nasa[1], 2), "squares": p["static"]["hls"]["clean_pixels"]}
    return out


@lru_cache(maxsize=None)
def zones(field_id: str):
    """The 10 m squares that were less green than the rest of the field in at least half of the years."""
    path = BAKED / field_id / "zones.geojson"
    if not path.exists() or not _ok(profile(field_id), "s2") or profile(field_id)["static"]["s2"]["clean_pixels"] < MIN_SQUARES:
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    cells = data["features"]
    if not cells:
        return None
    years = max(c["properties"]["years"] for c in cells)
    weak = [c for c in cells if c["properties"]["weak_years"] * 2 >= years]
    return {"years": years, "cells": len(cells), "weak": len(weak), "flag": len(weak) >= WEAK_MIN_CELLS, "cell_m": data["cell_m"],
            "points": [[round(c["geometry"]["coordinates"][0], 6), round(c["geometry"]["coordinates"][1], 6),
                        c["properties"]["weak_years"]] for c in weak]}


def month_series(field_id: str):
    """Monthly greenness this year next to the median of earlier years (whatever grew then)."""
    p = profile(field_id)
    if not _ok(p, "s2") or p["static"]["s2"]["clean_pixels"] < MIN_SQUARES:
        return None
    series = p["weekly"]["ndvi_field_10m"]
    this_year = max(series)

    def monthly(year):
        bins = [[] for _ in range(12)]
        for week, value in enumerate(series[year]):
            if value is not None:
                bins[_week_date(int(year), week).month - 1].append(value)
        return [mean(b) if b else None for b in bins]

    now = monthly(this_year)
    earlier = [monthly(y) for y in series if y != this_year]
    labels, values, usual = [], [], []
    for m in range(12):
        past = [e[m] for e in earlier if e[m] is not None]
        if now[m] is not None and len(past) >= 3:
            labels.append(MONTHS[m])
            values.append(round(now[m], 2))
            usual.append(round(median(past), 2))
    if len(labels) < 3:
        return None
    return {"kind": "line", "title": "How green the field is (NDVI: 0 = bare soil, 1 = dense crop)",
            "labels": labels, "values": values, "usual": usual, "valuesLabel": this_year,
            "usualLabel": f"Middle of {min(y for y in series if y != this_year)}-{max(y for y in series if y != this_year)}",
            "source": {"name": "Sentinel-2 (ESA) · 10 m", "detail": f"measured on your field · {p['static']['s2']['clean_pixels']} squares"}}


def health(field_id: str):
    """(health, label) for the map and the field list."""
    g = greenness(field_id)
    if g and g.get("too_small"):
        return "unknown", "Too small to read from space"
    if not g or not g["recent"]:
        return "unknown", "No clear image lately" if g else "No satellite reading yet"
    z = zones(field_id)
    if z and z["flag"]:
        return "weak_spot", "A part is often less green"
    return "good", g["short"]


def relief(field_id: str):
    p = profile(field_id)
    return p["static"]["relief"] if _ok(p, "relief") else None
