"""NASA POWER daily weather for one point, cached on disk.

POWER's meteorology comes from the MERRA-2 / GEOS models on a grid of about 0.5 x 0.625 degrees
(roughly 50 km), so one request covers all the fields of a farm. No account is needed.
"""
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)
PARAMS = "T2M_MAX,T2M_MIN,PRECTOTCORR,GWETROOT"
START = "20010101"
FILL = -999.0
MAX_AGE_S = 24 * 3600


def _fetch(lat: float, lon: float) -> dict:
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={PARAMS}&community=AG&longitude={lon}&latitude={lat}"
        f"&start={START}&end={date.today():%Y%m%d}&format=JSON"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "field-app-backend"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))["properties"]["parameter"]


def load(lat: float, lon: float) -> dict[str, dict[str, float]]:
    """Returns {"YYYYMMDD": {"tmax":..,"tmin":..,"rain":..,"soil":..}}; missing values are left out."""
    path = CACHE / f"power_{lat}_{lon}.json"
    raw = None
    if path.exists() and time.time() - path.stat().st_mtime < MAX_AGE_S:
        raw = json.loads(path.read_text())
    else:
        try:
            raw = _fetch(lat, lon)
            path.write_text(json.dumps(raw))
        except Exception:
            if not path.exists():
                raise
            raw = json.loads(path.read_text())  # offline: fall back to the last good copy

    names = {"T2M_MAX": "tmax", "T2M_MIN": "tmin", "PRECTOTCORR": "rain", "GWETROOT": "soil"}
    days: dict[str, dict[str, float]] = {}
    for key, name in names.items():
        for day, value in raw[key].items():
            if value != FILL:
                days.setdefault(day, {})[name] = value
    return dict(sorted(days.items()))
