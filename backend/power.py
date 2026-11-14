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
PARAMS = "T2M_MAX,T2M_MIN,T2MDEW,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR,GWETROOT"
NAMES = {"T2M_MAX": "tmax", "T2M_MIN": "tmin", "T2MDEW": "tdew", "WS2M": "wind",
         "ALLSKY_SFC_SW_DWN": "sun", "PRECTOTCORR": "rain", "GWETROOT": "soil"}
START = "20010101"
FILL = -999.0
MAX_AGE_S = 24 * 3600


def _fetch(lat: float, lon: float, start: str, end: str) -> dict:
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters={PARAMS}&community=AG&longitude={lon}&latitude={lat}"
        f"&start={start}&end={end}&format=JSON"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "field-app-backend"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))["properties"]["parameter"]


def load(lat: float, lon: float, end: str | None = None) -> dict[str, dict[str, float]]:
    """Returns {"YYYYMMDD": {"tmax":..,"tmin":..,"tdew":..,"wind":..,"sun":..,"rain":..,"soil":..}}.

    Missing values are left out. Without `end` the series runs to today and is refreshed daily;
    with `end` (a closed period such as "20201231") it is downloaded once and kept.
    """
    path = CACHE / f"power7_{lat}_{lon}_{end or 'live'}.json"
    raw = None
    if path.exists() and (end or time.time() - path.stat().st_mtime < MAX_AGE_S):
        raw = json.loads(path.read_text())
    else:
        try:
            raw = _fetch(lat, lon, START, end or f"{date.today():%Y%m%d}")
            path.write_text(json.dumps(raw))
        except Exception:
            if not path.exists():
                raise
            raw = json.loads(path.read_text())  # offline: fall back to the last good copy

    names = NAMES
    days: dict[str, dict[str, float]] = {}
    for key, name in names.items():
        for day, value in raw[key].items():
            if value != FILL:
                days.setdefault(day, {})[name] = value
    return dict(sorted(days.items()))
