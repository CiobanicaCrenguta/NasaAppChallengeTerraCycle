"""Chooses the next crops for a field from the sourced crop table (crops.json) and NASA POWER rain.

Two steps, both traceable:
  1. Rules. A crop is left out when a source says it should not come now: too few years since the same
     crop, a crop it should not follow, a shared disease host too recently, wheat straight after wheat.
  2. Ranking. Among the crops that remain:
       water   years (2001-2020) in which the yearly rain here reached the crop's optimal range
               (NASA POWER rain against FAO ECOCROP ranges);
       soil    crops that leave nitrogen in the soil first (S6), then the rain ranking;
       income  there is no price data, so the rain ranking is used and the answer says so.
     A crop not grown on the field in the last three years goes ahead of one that was (S1 asks to avoid
     monoculture).

Known weakness, shown to the farmer in "Why?": ECOCROP has one yearly-rain range per species for the whole
world. It does not know when in the year the rain falls, so it is hard on winter crops.
"""
import knowledge

BASE = range(2001, 2021)
CROPS = knowledge.CROPS
ORDER = ["barley", "wheat", "rapeseed", "corn", "sunflower", "peas", "soy"]  # only to make ties repeatable


def _value(node, key="value"):
    return node.get("engine_value", node[key]) if node else None


def excluded(crop_id: str, past: list[str]):
    """None if the crop may come next, else {"text", "source"}. `past` is oldest first, one crop per year."""
    r = CROPS[crop_id]["rotation"]
    name = knowledge.name(crop_id)
    last = past[-1] if past else None

    gap = r.get("min_gap_years")
    if gap:
        years = _value(gap)
        if crop_id in past[-years:]:
            ago = len(past) - 1 - max(i for i, c in enumerate(past) if c == crop_id) + 1
            return {"text": f"{name}: grown here {ago} year{'s' if ago > 1 else ''} ago; leave {years} years between {name} crops",
                    "source": gap["source"], "status": gap["status"]}
    once = r.get("max_years_after_itself")
    if once and last == crop_id:
        return {"text": f"{name}: not straight after {name}, except in extreme cases", "source": once["source"], "status": once["status"]}
    avoid = r.get("avoid_after")
    if avoid and last in avoid["value"]:
        return {"text": f"{name}: should not follow {knowledge.name(last)}", "source": avoid["source"], "status": avoid["status"]}
    for a, b in ((crop_id, None), (None, crop_id)):  # the host rule, read from either crop
        for other_id, other in CROPS.items():
            hosts = other["rotation"].get("min_gap_from_other_hosts")
            if not hosts:
                continue
            years = hosts["value"]
            if a == other_id and any(c in hosts["hosts"] for c in past[-years:]):
                host = next(c for c in reversed(past[-years:]) if c in hosts["hosts"])
                return {"text": f"{name}: leave at least {years} years after {knowledge.name(host)} (shared disease)",
                        "source": hosts["source"], "status": hosts["status"]}
            if b in hosts["hosts"] and other_id in past[-years:]:
                return {"text": f"{name}: leave at least {years} years after {knowledge.name(other_id)} (shared disease)",
                        "source": hosts["source"], "status": hosts["status"]}
    return None


def rain_fit(crop_id: str, rain_by_year: dict[int, float]):
    """How many of the reference years had enough rain for the crop, by its ECOCROP ranges."""
    req = CROPS[crop_id]["requirements"]
    optimal, absolute = req["rain_optimal"]["value"][0], req["rain_absolute"]["value"][0]
    years = [rain_by_year[y] for y in BASE if y in rain_by_year]
    return {"years": len(years), "optimal_mm": optimal, "minimum_mm": absolute,
            "optimal_years": sum(v >= optimal for v in years), "minimum_years": sum(v >= absolute for v in years)}


def rank(past: list[str], priority: str, rain_by_year):
    """(candidates best first, excluded). Each candidate: {"id", "fit", "fresh", "nitrogen"}."""
    allowed, out = [], []
    for cid in ORDER:
        reason = excluded(cid, past)
        if reason:
            out.append({"id": cid, **reason})
            continue
        allowed.append({"id": cid, "fit": rain_fit(cid, rain_by_year), "fresh": cid not in past[-3:],
                        "nitrogen": bool(CROPS[cid]["rotation"].get("leaves_nitrogen"))})

    def key(c):
        return (not c["fresh"], not (priority == "soil" and c["nitrogen"]), -c["fit"]["optimal_years"], -c["fit"]["minimum_years"],
                ORDER.index(c["id"]))
    return sorted(allowed, key=key), out


def plan(history: list[dict], priority: str, rain_by_year, years: int = 3):
    """[{"year", "cropId", "candidates", "excluded"}] for the coming years. history: [{"year", "cropId"}], oldest first."""
    past = [h["cropId"] for h in history]
    year = history[-1]["year"]
    steps = []
    for _ in range(years):
        candidates, out = rank(past, priority, rain_by_year)
        if not candidates:
            break
        year += 1
        steps.append({"year": year, "cropId": candidates[0]["id"], "candidates": candidates, "excluded": out})
        past.append(candidates[0]["id"])
    return steps
