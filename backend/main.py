"""Backend for the field app. Serves exactly the shapes the phone app expects (see app/src/types.ts).

Run:  python -m uvicorn main:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException

import analysis
import engine
import power
from store import FIELDS, USER, area_point, crop, field

app = FastAPI(title="Field app backend")

_weather = None


def weather() -> analysis.Weather:
    global _weather
    if _weather is None:
        lat, lon = area_point()
        _weather = analysis.Weather(power.load(lat, lon))
    return _weather


# Crop greenness is not connected yet, so no field has a health reading.
HEALTH, HEALTH_LABEL = "unknown", "No satellite reading yet"


@app.get("/me")
def me():
    return USER


@app.get("/fields")
def fields():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": f["geometry"], "properties": {
            "id": f["id"], "name": f["name"], "crop": crop(f["cropId"])["name"], "ha": f["ha"],
            "health": HEALTH, "healthLabel": HEALTH_LABEL}}
        for f in FIELDS]}


@app.get("/fields/{field_id}")
def field_summary(field_id: str):
    f = field(field_id)
    if not f:
        raise HTTPException(404, "No such field")
    return {"id": f["id"], "history": [{"year": h["year"], "crop": crop(h["cropId"])["name"]} for h in f["history"]]}


@app.get("/overview")
def overview():
    w = weather()
    stats = analysis.overview_stats(w)
    dry = any(s["warn"] for s in stats)
    headline = "It has been dry in your area lately." if dry else "Nothing unusual in your area's weather lately."
    return {"headline": headline, "attention": [], "stats": stats, "asOf": w.last.isoformat()}


@app.get("/insights")
def insights(field: str | None = None):
    w = weather()
    return {
        "area": USER["region"],
        "knows": [
            {"id": "field", "title": "Known about your fields", "items": [
                "Their outlines and sizes, from the map you drew"],
             "note": "How green the crop is, from satellite images, is not connected yet."},
            {"id": "area", "title": "Estimated for your area", "items": [
                "Rain, every day since 2001",
                "Temperature, every day since 2001",
                "Water in the root zone of the soil, a model estimate"],
             "note": f"One value for a square about 50 km wide. Good for trends, too coarse to tell one field from the next. "
                     f"Latest data: {w.last:%d %B %Y}."},
            {"id": "you", "title": "What you told me", "items": [
                "The crops you grew each year", "Your answers to my questions"]},
            {"id": "blind", "title": "What I cannot see", "items": [
                "Pests and disease", "Packed soil and blocked drains", "What happens on one field and not on its neighbour"]},
        ],
        "cards": analysis.insight_cards(w),
    }


@app.post("/converse")
def converse(req: dict):
    if not req.get("sessionId"):
        raise HTTPException(400, "sessionId is required")
    return engine.converse(req, weather())
