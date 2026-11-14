"""Fields and the crop table. Geometry is real; crops and history are sample values."""
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).parent
# TERRACYCLE_FIELDS picks another farm, e.g. fields_world.json; the default is the demo farm.
FIELDS_FILE = HERE / os.environ.get("TERRACYCLE_FIELDS", "fields.json")
_raw = json.loads(FIELDS_FILE.read_text(encoding="utf-8"))
USER = _raw["user"]


def _ring(geometry):
    return geometry["coordinates"][0]


def area_ha(geometry) -> float:
    """Polygon area in hectares (shoelace on a local flat projection; fine for fields)."""
    ring = _ring(geometry)
    lat0 = math.radians(sum(p[1] for p in ring) / len(ring))
    kx = 111_320.0 * math.cos(lat0)  # metres per degree of longitude
    ky = 110_574.0  # metres per degree of latitude
    pts = [(p[0] * kx, p[1] * ky) for p in ring]
    s = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        s += x1 * y2 - x2 * y1
    return abs(s) / 2 / 10_000


def centroid(geometry) -> tuple[float, float]:
    ring = _ring(geometry)[:-1]
    return (sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring))  # lat, lon


FIELDS = _raw["fields"]
for f in FIELDS:
    f["ha"] = round(area_ha(f["geometry"]), 1 if area_ha(f["geometry"]) >= 1 else 2)  # small plots keep two decimals


def field(field_id):
    return next((f for f in FIELDS if f["id"] == field_id), None)


def area_point() -> tuple[float, float]:
    """One point for area-level data: the middle of all fields (they share one ~50 km cell)."""
    cs = [centroid(f["geometry"]) for f in FIELDS]
    return (round(sum(c[0] for c in cs) / len(cs), 3), round(sum(c[1] for c in cs) / len(cs), 3))


# Names of the crops the app knows. Everything else about a crop is in crops.json, with its source.
CROPS = [
    {"id": "barley", "name": "Winter barley"},
    {"id": "wheat", "name": "Winter wheat"},
    {"id": "rapeseed", "name": "Rapeseed"},
    {"id": "corn", "name": "Corn"},
    {"id": "sunflower", "name": "Sunflower"},
    {"id": "peas", "name": "Peas"},
    {"id": "soy", "name": "Soybean"},
]


def weather_point(field_id=None) -> tuple[float, float]:
    """Where to read area weather for a field. Fields close together share one point (and one download);
    a field far from the others gets its own."""
    middle = area_point()
    centres = {f["id"]: centroid(f["geometry"]) for f in FIELDS}
    if all(abs(c[0] - middle[0]) < 0.25 and abs(c[1] - middle[1]) < 0.25 for c in centres.values()):
        return middle
    c = centres.get(field_id) or centres[FIELDS[0]["id"]]
    return (round(c[0], 2), round(c[1], 2))


def in_romania() -> bool:
    """Rough box around Romania. The sowing dates in crops.json are from southern Romania only."""
    lat, lon = area_point()
    return 43.6 <= lat <= 48.3 and 20.2 <= lon <= 29.8


def crop(crop_id):
    return next(c for c in CROPS if c["id"] == crop_id)
