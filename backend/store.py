"""Fields and the crop table. Geometry is real; crops and history are sample values."""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
_raw = json.loads((HERE / "fields.json").read_text(encoding="utf-8"))
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
    f["ha"] = round(area_ha(f["geometry"]), 1)


def field(field_id):
    return next((f for f in FIELDS if f["id"] == field_id), None)


def area_point() -> tuple[float, float]:
    """One point for area-level data: the middle of all fields (they share one ~50 km cell)."""
    cs = [centroid(f["geometry"]) for f in FIELDS]
    return (round(sum(c[0] for c in cs) / len(cs), 3), round(sum(c[1] for c in cs) / len(cs), 3))


# PLACEHOLDER crop table. water / soil / income are 1 (low) to 3 (high); min_gap = years before
# the crop may return to the same field. To be replaced by a sourced agronomy table.
CROPS = [
    {"id": "barley", "name": "Winter barley", "family": "cereal", "water": 1, "soil": 1, "income": 1, "early": True},
    {"id": "wheat", "name": "Winter wheat", "family": "cereal", "water": 2, "soil": 1, "income": 2, "early": True},
    {"id": "rapeseed", "name": "Rapeseed", "family": "brassica", "water": 2, "soil": 2, "income": 3, "early": True, "min_gap": 3},
    {"id": "corn", "name": "Corn", "family": "maize", "water": 3, "soil": 1, "income": 3},
    {"id": "sunflower", "name": "Sunflower", "family": "aster", "water": 2, "soil": 1, "income": 3, "min_gap": 4},
    {"id": "peas", "name": "Peas", "family": "legume", "water": 1, "soil": 3, "income": 1, "nfix": True, "early": True, "min_gap": 4},
    {"id": "soy", "name": "Soybean", "family": "legume", "water": 3, "soil": 3, "income": 2, "nfix": True, "min_gap": 3},
    {"id": "alfalfa", "name": "Alfalfa", "family": "legume", "water": 2, "soil": 3, "income": 1, "nfix": True},
    {"id": "sorghum", "name": "Sorghum", "family": "sorghum", "water": 1, "soil": 1, "income": 1},
]


def crop(crop_id):
    return next(c for c in CROPS if c["id"] == crop_id)
