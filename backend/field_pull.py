"""Download every data source for every field once, and bake it to disk.

    python field_pull.py                      # all sources, all fields
    python field_pull.py --only power,soil    # just the sources that need no account
    python field_pull.py --field <id>         # one field

Output, per field, in data/baked/<field id>/:
    profile.json     weekly series per year for each source, plus soil and relief numbers
    zones.geojson    Sentinel-2 10 m cells: how green each cell is next to the rest of the field
    relief.geojson   NASADEM 30 m cells: slope and height, with steep and low cells flagged

Weeks are 7-day bins counted from 1 January (52 per year; the last bin takes the extra days).
Raw answers are kept in cache/, so a second run only asks for what is missing.
A source that fails is written into profile.json as "pending" with the reason; the app must then
say "no reading yet" for it rather than guess.

POWER and SoilGrids need no account. Everything else goes through Earth Engine:
    .venv\\Scripts\\earthengine authenticate --auth_mode=localhost
"""
import argparse
import json
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from statistics import mean, median

import power
import store

PROJECT = "terracycle-514620"
Y0, Y1 = 2001, 2020  # reference period for the 20-year calendar and the replay
HERE = Path(__file__).parent
BAKED = HERE / "data" / "baked"
CACHE = HERE / "cache" / "pull"
CACHE.mkdir(parents=True, exist_ok=True)

# Thresholds below are our own choices, listed in STATUS.md under "to verify with an agronomist".
HEAVY_RAIN_MM = 20.0   # a day with at least this much rain counts as a heavy-rain day
BARE_NDVI = 0.25       # field NDVI below this is read as bare soil
STEEP_DEG = 5.0        # 30 m cells at least this steep are flagged for erosion risk
LOW_MIN_RANGE_M = 5.0  # low spots are flagged only if the field's height range beats NASADEM noise
WEAK_REL = -0.10       # a 10 m cell this far below the field median counts as weaker that year

SOURCES = {
    "power": {"name": "NASA POWER", "version": "Daily API v2 (MERRA-2 / GEOS, CERES)", "scope": "area", "grid": "about 50 km",
              "period": f"{Y0}-{Y1}"},
    "soil": {"name": "ISRIC SoilGrids", "version": "2.0", "scope": "area", "grid": "250 m", "period": "static"},
    "modis": {"name": "MODIS Terra vegetation indices", "version": "MODIS/061/MOD13Q1", "scope": "area", "grid": "250 m",
              "period": f"{Y0}-{Y1}"},
    "smap": {"name": "SMAP L4 soil moisture", "version": "NASA/SMAP/SPL4SMGP/008", "scope": "area", "grid": "about 9 km",
             "period": f"2015-{Y1}"},
    "imerg": {"name": "GPM IMERG precipitation", "version": "NASA/GPM_L3/IMERG_V07", "scope": "area", "grid": "about 10 km",
              "period": f"{Y0}-{Y1}"},
    "relief": {"name": "NASADEM (SRTM reprocessed)", "version": "NASA/NASADEM_HGT/001", "scope": "field", "grid": "30 m",
               "period": "February 2000"},
    "hls": {"name": "Harmonized Landsat Sentinel-2", "version": "NASA/HLS/HLSL30/v002 + NASA/HLS/HLSS30/v002", "scope": "field",
            "grid": "30 m", "period": "2013-today"},
    "s2": {"name": "Copernicus Sentinel-2 surface reflectance", "version": "COPERNICUS/S2_SR_HARMONIZED", "scope": "field",
           "grid": "10 m", "period": "2017-today"},
}
NEEDS_EE = ("modis", "smap", "imerg", "relief", "hls", "s2")


# ---------- helpers ----------

def week_of(d: date) -> int:
    return min((d.timetuple().tm_yday - 1) // 7, 51)


def weekly(samples, how) -> dict[str, list]:
    """samples: iterable of (date, value). Returns {"2001": [52 values or None], ...}."""
    bins: dict[int, list[list[float]]] = {}
    for d, v in samples:
        if v is not None:
            bins.setdefault(d.year, [[] for _ in range(52)])[week_of(d)].append(v)
    return {str(y): [round(how(w), 4) if w else None for w in weeks] for y, weeks in sorted(bins.items())}


def cached(name: str, make):
    path = CACHE / f"{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    value = make()
    path.write_text(json.dumps(value))
    return value


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "field-app-backend"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def ymd(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def ms_date(ms: float) -> date:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).date()


# ---------- sources without an account ----------

def pull_power(f, lat, lon):
    days = power.load(round(lat, 3), round(lon, 3), end=f"{Y1}1231")
    rows = [(ymd(k), v) for k, v in days.items()]

    def col(name, how):
        return weekly(((d, v.get(name)) for d, v in rows), how)

    return {"weekly": {
        "tmax": col("tmax", mean), "tmax_peak": col("tmax", max),
        "tmin": col("tmin", mean), "tmin_low": col("tmin", min),
        "tdew": col("tdew", mean), "wind": col("wind", mean), "sun": col("sun", mean),
        "rain": col("rain", sum), "soil_wetness": col("soil", mean),
    }}


def texture_class(sand: float, silt: float, clay: float) -> str:
    """USDA texture triangle, from percentages."""
    if silt + 1.5 * clay < 15:
        return "sand"
    if silt + 2 * clay < 30:
        return "loamy sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "sandy loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "loam"
    if (silt >= 50 and 12 <= clay < 27) or (50 <= silt < 80 and clay < 12):
        return "silt loam"
    if silt >= 80 and clay < 12:
        return "silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "sandy clay loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "clay loam"
    if 27 <= clay < 40 and sand <= 20:
        return "silty clay loam"
    if clay >= 35 and sand > 45:
        return "sandy clay"
    if clay >= 40 and silt >= 40:
        return "silty clay"
    return "clay"


def pull_soil(f, lat, lon):
    """Top 30 cm from SoilGrids. No value for the place -> the app asks the farmer instead."""
    props = "&".join(f"property={p}" for p in ("clay", "sand", "silt", "phh2o", "soc"))
    depths = "&".join(f"depth={d}" for d in ("0-5cm", "5-15cm", "15-30cm"))
    url = f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={lon:.4f}&lat={lat:.4f}&{props}&{depths}&value=mean"
    raw = cached(f"soil_{f['id']}", lambda: http_json(url))
    thick = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}
    out = {}
    for layer in raw["properties"]["layers"]:
        vals = [(d["values"]["mean"], thick[d["label"]]) for d in layer["depths"] if d["values"]["mean"] is not None]
        if vals:
            out[layer["name"]] = sum(v * t for v, t in vals) / sum(t for _, t in vals) / layer["unit_measure"]["d_factor"]
    if not all(k in out for k in ("clay", "sand", "silt")):
        raise ValueError("SoilGrids has no soil values at this point")
    soil = {"origin": "SoilGrids", "depth": "0-30 cm",
            "sand_pct": round(out["sand"], 1), "silt_pct": round(out["silt"], 1), "clay_pct": round(out["clay"], 1),
            "texture": texture_class(out["sand"], out["silt"], out["clay"])}
    if "phh2o" in out:
        soil["ph"] = round(out["phh2o"], 1)
    if "soc" in out:
        soil["organic_carbon_g_per_kg"] = round(out["soc"], 1)
    return {"static": {"soil": soil}}


# ---------- Earth Engine ----------

_ee = None


def ee():
    global _ee
    if _ee is None:
        import ee as module
        module.Initialize(project=PROJECT)
        _ee = module
    return _ee


def region_rows(collection, geometry, scale):
    """getRegion as a list of dicts; the first row of the answer is the header."""
    rows = collection.getRegion(geometry, scale).getInfo()
    return [dict(zip(rows[0], r)) for r in rows[1:]]


def pull_modis(f, lat, lon):
    """NDVI of the 250 m squares that touch the field. They also cover the neighbours: area scope."""
    e = ee()
    geom = e.Geometry(f["geometry"])
    samples = []
    for y in range(Y0, Y1 + 1):
        def make(y=y):
            col = e.ImageCollection("MODIS/061/MOD13Q1").filterDate(f"{y}-01-01", f"{y + 1}-01-01").select(["NDVI", "SummaryQA"])
            return region_rows(col, geom, 250)
        by_day: dict[float, list[float]] = {}
        for r in cached(f"modis_{f['id']}_{y}", make):
            if r["NDVI"] is not None and r["SummaryQA"] in (0, 1):  # 0 good, 1 marginal; snow and cloud dropped
                by_day.setdefault(r["time"], []).append(r["NDVI"] * 0.0001)
        samples += [(ms_date(t), mean(v)) for t, v in by_day.items()]
    return {"weekly": {"ndvi_area": weekly(samples, mean)}}


def month_starts(y0, m0, y1):
    return [(y, m) for y in range(y0, y1 + 1) for m in range(1, 13) if (y, m) >= (y0, m0)]


def next_month(y, m):
    return (y + 1, 1) if m == 12 else (y, m + 1)


def pull_smap(f, lat, lon):
    e = ee()
    pt = e.Geometry.Point([lon, lat])
    samples = []
    for y, m in month_starts(2015, 4, Y1):
        ny, nm = next_month(y, m)

        def make(y=y, m=m, ny=ny, nm=nm):
            col = e.ImageCollection("NASA/SMAP/SPL4SMGP/008").filterDate(f"{y}-{m:02d}-01", f"{ny}-{nm:02d}-01").select(["sm_rootzone"])
            return [[r["time"], r["sm_rootzone"]] for r in region_rows(col, pt, 9000)]
        samples += [(ms_date(t), v) for t, v in cached(f"smap_{f['id']}_{y}{m:02d}", make)]
    return {"weekly": {"soil_moisture_rootzone": weekly(samples, mean)}}


def pull_imerg(f, lat, lon):
    """Half-hourly rain rate (mm/h) summed to days, then heavy-rain days per week."""
    e = ee()
    pt = e.Geometry.Point([lon, lat])
    daily: dict[date, float] = {}
    for y, m in month_starts(Y0, 1, Y1):
        ny, nm = next_month(y, m)

        def make(y=y, m=m, ny=ny, nm=nm):
            col = e.ImageCollection("NASA/GPM_L3/IMERG_V07").filterDate(f"{y}-{m:02d}-01", f"{ny}-{nm:02d}-01").select(["precipitation"])
            days: dict[str, float] = {}
            for r in region_rows(col, pt, 11132):
                if r["precipitation"] is not None:
                    key = ms_date(r["time"]).isoformat()
                    days[key] = days.get(key, 0.0) + r["precipitation"] * 0.5
            return days
        for key, mm in cached(f"imerg_{f['id']}_{y}{m:02d}", make).items():
            daily[date.fromisoformat(key)] = mm
    return {"weekly": {
        "rain_day_max": weekly(daily.items(), max),
        "heavy_rain_days": weekly(((d, 1.0 if mm >= HEAVY_RAIN_MM else 0.0) for d, mm in daily.items()), sum),
    }}


def pull_relief(f, lat, lon):
    e = ee()
    geom = e.Geometry(f["geometry"])

    def make():
        dem = e.Image("NASA/NASADEM_HGT/001").select("elevation")
        img = dem.addBands(e.Terrain.slope(dem))
        return img.sample(region=geom, scale=30, geometries=True).getInfo()["features"]
    cells = cached(f"relief_{f['id']}", make)
    if not cells:
        raise ValueError("no 30 m cell centre falls inside the field")
    heights = [c["properties"]["elevation"] for c in cells]
    slopes = [c["properties"]["slope"] for c in cells]
    lo, hi = min(heights), max(heights)
    low_line = lo + 0.1 * (hi - lo) if hi - lo >= LOW_MIN_RANGE_M else None
    feats = []
    for c in cells:
        p = c["properties"]
        feats.append({"type": "Feature", "geometry": c["geometry"], "properties": {
            "slope_deg": round(p["slope"], 1), "elevation_m": p["elevation"],
            "steep": p["slope"] >= STEEP_DEG, "low": low_line is not None and p["elevation"] <= low_line}})
    return {
        "static": {"relief": {"cells": len(cells), "elevation_min_m": lo, "elevation_max_m": hi,
                              "slope_mean_deg": round(mean(slopes), 1), "slope_max_deg": round(max(slopes), 1),
                              "steep_cells": sum(x["properties"]["steep"] for x in feats),
                              "low_cells": sum(x["properties"]["low"] for x in feats)}},
        "files": {"relief.geojson": {"type": "FeatureCollection", "cell_m": 30, "features": feats}},
    }


def field_series(collection, to_ndvi, geometry, scale, reducer_name):
    """One number per image: NDVI over the geometry, and how many pixels were clear."""
    e = ee()
    reducer = getattr(e.Reducer, reducer_name)().combine(e.Reducer.count(), sharedInputs=True)

    def per_image(img):
        stats = to_ndvi(img).reduceRegion(reducer, geometry, scale)
        return e.Feature(None, {"t": img.date().millis(), "v": stats.get(f"ndvi_{reducer_name}"), "n": stats.get("ndvi_count")})
    feats = e.FeatureCollection(collection.map(per_image)).filter(e.Filter.notNull(["v"]))
    return feats.reduceColumns(e.Reducer.toList(3), ["t", "v", "n"]).get("list").getInfo()


def clear_dates(rows):
    """Keep dates where at least 70% of the field's pixels were clear; one value per day."""
    if not rows:
        return [], 0
    full = max(n for _, _, n in rows)
    by_day: dict[date, list[float]] = {}
    for t, v, n in rows:
        if n >= 0.7 * full:
            by_day.setdefault(ms_date(t), []).append(v)
    return [(d, mean(v)) for d, v in sorted(by_day.items())], full


def pull_hls(f, lat, lon):
    """NASA's own 30 m reading of the field, on the outline pulled 21 m inwards (whole pixels only)."""
    e = ee()
    inner = e.Geometry(f["geometry"]).buffer(-21)

    def ndvi(nir):
        def fn(img):
            clear = img.select("Fmask").bitwiseAnd(0b11110).eq(0)  # bits 1-4: cloud, adjacent, shadow, snow
            return img.normalizedDifference([nir, "B4"]).rename("ndvi").updateMask(clear)
        return fn
    rows = []
    for y in range(2013, date.today().year + 1):
        def make(y=y):
            span = (f"{y}-01-01", f"{y + 1}-01-01")
            landsat = e.ImageCollection("NASA/HLS/HLSL30/v002").filterBounds(inner).filterDate(*span)
            sentinel = e.ImageCollection("NASA/HLS/HLSS30/v002").filterBounds(inner).filterDate(*span)
            return field_series(landsat, ndvi("B5"), inner, 30, "mean") + field_series(sentinel, ndvi("B8A"), inner, 30, "mean")
        rows += cached(f"hls_{f['id']}_{y}", make)
    samples, pixels = clear_dates(rows)
    return {"weekly": {"ndvi_field_30m": weekly(samples, max)}, "static": {"hls": {"clean_pixels": pixels, "dates": len(samples)}}}


def pull_s2(f, lat, lon):
    """10 m: the field's NDVI through time (bare-soil weeks) and a map of persistently weaker cells."""
    e = ee()
    inner = e.Geometry(f["geometry"]).buffer(-7)

    def ndvi(img):
        scl = img.select("SCL")
        clear = scl.eq(4).Or(scl.eq(5))  # vegetation or bare soil; cloud, shadow, water, snow dropped
        return img.normalizedDifference(["B8", "B4"]).rename("ndvi").updateMask(clear)
    col = e.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(inner)
    years = list(range(2017, date.today().year + 1))
    rows = []
    for y in years:
        rows += cached(f"s2_{f['id']}_{y}",
                       lambda y=y: field_series(col.filterDate(f"{y}-01-01", f"{y + 1}-01-01"), ndvi, inner, 10, "median"))
    samples, pixels = clear_dates(rows)
    series = weekly(samples, median)
    bare = {y: sum(1 for v in w if v is not None and v < BARE_NDVI) for y, w in series.items()}

    def make_zones():
        # Each growing season: every cell's peak NDVI next to the field's median peak. The crop changes
        # from year to year, so only the difference inside the field is kept, never the level.
        rels = []
        for y in years:
            peak = col.filterDate(f"{y}-04-01", f"{y}-10-01").map(ndvi).reduce(e.Reducer.percentile([90])).rename("peak")
            field_median = e.Number(peak.reduceRegion(e.Reducer.median(), inner, 10).get("peak"))
            rels.append(peak.divide(e.Image.constant(field_median)).subtract(1).rename("rel"))
        stack = e.ImageCollection(rels)
        img = stack.mean().rename("rel").addBands(stack.map(lambda i: i.lt(WEAK_REL)).sum().rename("weak_years")) \
            .addBands(stack.count().rename("years"))
        return img.sample(region=inner, scale=10, geometries=True).getInfo()["features"]
    cells = cached(f"s2zones_{f['id']}", make_zones)
    feats = [{"type": "Feature", "geometry": c["geometry"], "properties": {
        "rel": round(c["properties"]["rel"], 3), "weak_years": c["properties"]["weak_years"], "years": c["properties"]["years"]}}
        for c in cells]
    return {
        "weekly": {"ndvi_field_10m": series},
        "static": {"s2": {"clean_pixels": pixels, "dates": len(samples), "bare_weeks_by_year": bare, "zone_cells": len(feats)}},
        "files": {"zones.geojson": {"type": "FeatureCollection", "cell_m": 10, "weak_rel": WEAK_REL, "features": feats}},
    }


PULLERS = {"power": pull_power, "soil": pull_soil, "modis": pull_modis, "smap": pull_smap, "imerg": pull_imerg,
           "relief": pull_relief, "hls": pull_hls, "s2": pull_s2}


# ---------- bake ----------

def bake(f, only):
    lat, lon = store.centroid(f["geometry"])
    out_dir = BAKED / f["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "profile.json"
    profile = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    profile.update({"field": f["id"], "name": f["name"], "point": [round(lat, 5), round(lon, 5)], "weeks_per_year": 52,
                    "thresholds": {"heavy_rain_mm": HEAVY_RAIN_MM, "bare_ndvi": BARE_NDVI, "steep_deg": STEEP_DEG,
                                   "low_min_range_m": LOW_MIN_RANGE_M, "weak_rel": WEAK_REL}})
    for key in ("sources", "weekly", "static"):
        profile.setdefault(key, {})
    for key in only:
        info = dict(SOURCES[key])
        try:
            got = PULLERS[key](f, lat, lon)
            profile["weekly"].update(got.get("weekly", {}))
            profile["static"].update(got.get("static", {}))
            for name, content in got.get("files", {}).items():
                (out_dir / name).write_text(json.dumps(content), encoding="utf-8")
            info.update(status="ok", pulled=date.today().isoformat())
        except Exception as err:  # one failed source must not lose the others
            info.update(status="pending", reason=f"{type(err).__name__}: {err}".splitlines()[0][:200])
        profile["sources"][key] = info
        print(f"  {key:7} {info['status']}" + (f"  ({info['reason']})" if info["status"] != "ok" else ""))
    for key in SOURCES:  # sources never tried still appear, so the app knows what is missing
        profile["sources"].setdefault(key, {**SOURCES[key], "status": "pending", "reason": "not pulled yet"})
    path.write_text(json.dumps(profile), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=",".join(PULLERS), help="comma-separated: " + ", ".join(PULLERS))
    ap.add_argument("--field", help="one field id; default is every field")
    args = ap.parse_args()
    only = [k for k in args.only.split(",") if k]
    unknown = [k for k in only if k not in PULLERS]
    if unknown:
        sys.exit(f"unknown source: {', '.join(unknown)}")
    for f in store.FIELDS:
        if args.field in (None, f["id"]):
            print(f"{f['name']} ({f['id']})")
            bake(f, only)


if __name__ == "__main__":
    main()
