"""Backend for the field app. Serves exactly the shapes the phone app expects (see app/src/types.ts).

Run:  python -m uvicorn main:app --host 0.0.0.0 --port 8000
"""
from fastapi import FastAPI, HTTPException

import analysis
import engine
import fieldstate
import power
from store import FIELDS, USER, crop, field, weather_point

app = FastAPI(title="Field app backend")

_weather: dict = {}


def weather(field_id: str | None = None) -> analysis.Weather:
    """Area weather for a field. Fields close together share one point; see store.weather_point."""
    point = weather_point(field_id)
    if point not in _weather:
        _weather[point] = analysis.Weather(power.load(*point), south=point[0] < 0)
    return _weather[point]



@app.get("/me")
def me():
    return USER


@app.get("/fields")
def fields():
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": f["geometry"], "properties": {
            "id": f["id"], "name": f["name"], "crop": crop(f["cropId"])["name"], "ha": f["ha"],
            "health": fieldstate.health(f["id"])[0], "healthLabel": fieldstate.health(f["id"])[1],
            "weakSquares": _weak_squares(f["id"])}}
        for f in FIELDS]}


def _weak_squares(field_id):
    """Centres [lon, lat] of the 10 m squares that are often less green; empty unless the field is flagged."""
    z = fieldstate.zones(field_id)
    return [[x, y] for x, y, _ in z["points"]] if z and z["flag"] else []


@app.get("/fields/{field_id}/zones")
def field_zones(field_id: str):
    """The 10 m squares that were often less green than the rest of the field: [[lon, lat, years], ...]."""
    if not field(field_id):
        raise HTTPException(404, "No such field")
    z = fieldstate.zones(field_id)
    if not z:
        return {"cellM": 10, "years": 0, "cells": 0, "points": []}
    return {"cellM": z["cell_m"], "years": z["years"], "cells": z["cells"], "points": z["points"] if z["flag"] else []}


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
    attention = [{"fieldId": f["id"], "name": f["name"], "label": fieldstate.health(f["id"])[1]}
                 for f in FIELDS if fieldstate.health(f["id"])[0] == "weak_spot"]
    return {"headline": headline, "attention": attention, "stats": stats, "asOf": w.last.isoformat()}


@app.get("/insights")
def insights(field: str | None = None):
    w = weather(field)
    return {
        "area": USER["region"],
        "knows": [
            {"id": "field", "title": "Measured on your fields", "items": [
                "Their outlines and sizes, from the map you drew",
                "How green each field is, every few days since 2017",
                "Which parts of a field are often less green than the rest"],
             "note": "From Sentinel-2 images (ESA), on squares of 10 m. NASA's HLS images (30 m) read the same fields as a second check."},
            {"id": "area", "title": "Estimated for your area", "items": [
                "Rain, every day since 2001",
                "Temperature, every day since 2001",
                "Water in the root zone of the soil, a model estimate",
                "Soil type, from a world soil map"],
             "note": f"Weather is one value for a square about 50 km wide (NASA POWER); soil is from SoilGrids, 250 m. Good for trends, "
                     f"too coarse to tell one field from the next. Latest weather data: {w.last:%d %B %Y}."},
            {"id": "you", "title": "What you told me", "items": [
                "The crops you grew each year", "Your answers to my questions"]},
            {"id": "blind", "title": "What I cannot see", "items": [
                "Pests and disease", "Packed soil and blocked drains", "What happens on one field and not on its neighbour"]},
        ],
        "cards": _green_card(field) + analysis.insight_cards(w),
    }


def _green_card(field_id):
    """The greenness chart of one field (the chosen one, or the first), ahead of the area charts."""
    f = next((x for x in FIELDS if x["id"] == field_id), FIELDS[0])
    series, g = fieldstate.month_series(f["id"]), fieldstate.greenness(f["id"])
    if not series or not g:
        return []
    return [{"id": "green", "scope": "field", "perField": True, "series": series,
             "takeaway": f"{f['name']} has {g['words']} now."}]


@app.post("/converse")
def converse(req: dict):
    if not req.get("sessionId"):
        raise HTTPException(400, "sessionId is required")
    return engine.converse(req, weather)
