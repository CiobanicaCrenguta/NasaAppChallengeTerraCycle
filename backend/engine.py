"""The conversation: understands a question or a tapped reply and returns one structured answer.

Honesty rules:
- weather facts come from analysis.py (computed from NASA POWER); `weather` below is a function that
  returns the weather record for a field's place;
- the local language model (llm.py) only reads the question and words answers from facts we give it;
  sowing, crop-gap, heat and soil answers come from knowledge.py and always carry their source;
- field health comes from fieldstate.py: what Sentinel-2 and HLS measured, never a cause;
- the rotation pick comes from rotation.py: sourced rules from crops.json, then NASA POWER rain against
  FAO ECOCROP ranges; every exclusion shows its source.
"""
import difflib
import re
import unicodedata
import uuid

import analysis
import fieldstate
import knowledge
import llm
import rotation
from store import CROPS, FIELDS, HERE, crop, field, in_romania

SESSIONS: dict[str, dict] = {}

PLANT = {"value": "rotation", "label": "What to plant next"}


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def _msg(text, f=None, **extra):
    m = {"id": uuid.uuid4().hex, "role": "assistant", "text": text}
    if f:
        m["fieldId"], m["fieldName"] = f["id"], f["name"]
    m.update({k: v for k, v in extra.items() if v is not None})
    return m


# ---------- rotation: sourced rules, then the rain record ----------
RAIN_NOTE = ("Rain is NASA POWER's estimate for your area, 2001-2020. The rain each crop needs is FAO ECOCROP's range: one yearly "
             "figure per species for the whole world. It does not know when in the year the rain falls, so it is hard on winter crops.")


def _left_out(item):
    text = f"Left out {item['text']} [{item['source']}]"
    return text + (" (value not confirmed yet)" if item["status"] != "verificat" else "")


def _rotation(s, weather):
    f, p = field(s["fieldId"]), s["priority"]
    steps = rotation.plan(f["history"], p, weather(f["id"]).rain_by_year())
    if not steps:
        return _msg(f"I can't suggest a crop for {f['name']} with the rules I have.", f,
                    detail="Every crop in my table is ruled out by a rotation rule for this field's history.", replies=LIMITS_REPLY)
    first = steps[0]
    pick, out = first["candidates"][0], first["excluded"]
    fit = pick["fit"]
    reasons = []
    if p == "soil" and pick["nitrogen"]:
        reasons.append("Leaves nitrogen in the soil for the next crop [S6]")
    reasons.append(f"Enough rain for it here in {fit['optimal_years']} of {fit['years']} years")
    if pick["fresh"]:
        reasons.append("Not grown on this field in the last 3 years")
    last = f["history"][-1]["cropId"]
    shown = next((x for x in out if x["id"] == last), out[0] if out else None)
    detail = None
    if p == "income":
        detail = ("I have no price data, so I can't rank crops by income. This is the crop that fits your rotation and the rain "
                  "here best. Check it against local prices.")
    return _msg(
        f"Plant {knowledge.name(pick['id'])} on {f['name']}.", f, detail=detail,
        cards=[{"type": "rotation", "plan": [{"year": x["year"], "crop": crop(x["cropId"])["name"]} for x in steps],
                "reasons": reasons[:2], **({"avoid": _left_out(shown)} if shown else {})}],
        replies={"id": "next", "options": [{"value": "why", "label": "Why?"}, {"value": "priority", "label": "Change priority"}]},
    )


def _why(s, weather):
    f, p = field(s.get("fieldId")), s.get("priority")
    if not f or not p:  # not known (e.g. the server restarted): ask again rather than guess
        s["intent"] = "rotation"
        return _next(s, weather)
    steps = rotation.plan(f["history"], p, weather(f["id"]).rain_by_year())
    if not steps:
        return _rotation(s, weather)
    first = steps[0]
    parts = []
    if first["excluded"]:
        parts.append("Rotation rules: " + "; ".join(_left_out(x)[len("Left out "):] for x in first["excluded"]) + ".")
    ranked = ", ".join(f"{knowledge.name(c['id'])} {c['fit']['optimal_years']} of {c['fit']['years']} years"
                       f" (from {c['fit']['optimal_mm']} mm a year)" for c in first["candidates"])
    parts.append(f"Years with enough rain for each crop that remains: {ranked}.")
    if p == "soil":
        parts.append("With soil first, crops that leave nitrogen in the soil go ahead [S6].")
    if p == "income":
        parts.append("I have no price data, so income did not change the order.")
    parts.append("A crop not grown here in the last 3 years goes ahead of one that was [S1].")
    parts.append(RAIN_NOTE)
    rain_chart = analysis.insight_cards(weather(f["id"]))[0]["series"]
    return _msg("It passes the rotation rules and suits the rain here best.", f, detail=" ".join(parts),
                cards=[{"type": "chart", "series": rain_chart}], replies=LIMITS_REPLY)


def _limits():
    return _msg("From space I can't see everything.", cards=[{"type": "limits", "items": [
        "Packed soil below the surface", "Pests and disease", "Blocked drains"]}])


# ---------- field health: what the satellites measured ----------
def _health(s):
    f = field(s["fieldId"])
    g = fieldstate.greenness(f["id"])
    next_steps = {"id": "next", "options": [PLANT, {"value": "limits", "label": "What can't you see?"}]}
    if not g:
        return _msg(f"I don't have satellite readings for {f['name']} yet.", f,
                    detail="No satellite images have been processed for this field.", replies=next_steps)
    if g.get("too_small"):
        return _msg(f"{f['name']} is too small for me to read from space.", f,
                    detail=f"Only {g['squares']} squares of 10 m lie fully inside it, and I need at least {fieldstate.MIN_SQUARES} "
                           "for a reading I can stand behind. I can still use the weather and the soil map for your area, "
                           "and the rotation rules.", replies=next_steps)
    when = f"{g['date']:%d %B}".lstrip("0")
    if not g["recent"]:
        return _msg(f"I have no clear satellite image of {f['name']} lately.", f,
                    detail=f"The last clear one is from the week of {when}. Clouds hide the field from the satellite.", replies=next_steps)
    z = fieldstate.zones(f["id"])
    now = f"{f['name']} has {g['words']} now."
    parts = [f"Sentinel-2 (ESA) measured it in the week of {when}, on {g['squares']} squares of 10 m that lie fully inside the field "
             f"(greenness index {g['ndvi']})."]
    if "hls" in g:
        parts.append(f"NASA's HLS images (30 m, {g['hls']['squares']} squares) show {g['hls']['ndvi']} in the same days.")
    if z and z["flag"]:
        text = f"One part of {f['name']} is often less green than the rest."
        parts.insert(0, now)
        parts.append(f"{z['weak']} of {z['cells']} squares were at least 10% less green than the middle of the field in "
                     f"{(z['years'] + 1) // 2} or more of the last {z['years']} growing seasons. They are marked on the map.")
    else:
        text = now
        if z:
            parts.append(f"No part of the field stands out: in the last {z['years']} growing seasons no area was "
                         "less green than the rest year after year.")
    parts.append("A satellite shows how green a field is, not why.")
    series = fieldstate.month_series(f["id"])
    return _msg(text, f, detail=" ".join(parts), cards=[{"type": "chart", "series": series}] if series else None, replies=next_steps)


# ---------- sourced answers (crop table, soil) ----------
def _source_titles():
    """{"S1": "first line of that entry in SOURCES.md"}"""
    out, current = {"SoilGrids": "ISRIC SoilGrids 2.0, soil maps on a 250 m grid; an estimate for the area"}, None
    for line in (HERE / "SOURCES.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("## S"):
            current = line[3:].strip()
        elif current and line.strip():
            out[current] = line.strip().replace("*", "")
            current = None
    return out


SOURCE_TITLES = _source_titles()
CROP_REPLIES = [{"value": c["id"], "label": c["name"]} for c in CROPS if c["id"] in knowledge.CROPS]
LIMITS_REPLY = {"id": "next", "options": [{"value": "limits", "label": "What can't you see?"}]}


def _sourced(question, facts, f=None):
    text, by_model = llm.answer(question, facts)
    cited = list(dict.fromkeys(fact["source"] for fact in facts))
    detail = " ".join(f"[{c}] {SOURCE_TITLES.get(c, c)}" for c in cited) if cited else \
        "I only give values I can point to a source for. This one is on the list of what is still missing."
    m = _msg(text, f, detail=detail, replies=LIMITS_REPLY)
    m["wordedBy"] = "model" if by_model else "rules"
    return m


# Words that name a crop (English and Romanian, without accents). The model's choice of crop is checked against them:
# a crop the farmer did not mention is never answered about.
CROP_WORDS = {
    "wheat": ["wheat", "grau"], "barley": ["barley", "orz"], "corn": ["corn", "maize", "porumb"],
    "sunflower": ["sunflower", "sunflowers", "floarea", "soarelui"], "rapeseed": ["rapeseed", "canola", "oilseed", "rapita"],
    "peas": ["peas", "pea", "mazare"], "soy": ["soy", "soya", "soybean", "soybeans", "soia"],
}
NOT_CROPS = {"what", "when", "where", "which", "that", "than", "then", "wheel"}


def crops_in(question):
    """Crops named in the question, allowing a typo or two."""
    tokens = [t for t in re.findall(r"[a-z]+", _norm(question)) if len(t) >= 3 and t not in NOT_CROPS]
    def same(token, word):  # short words must match exactly ("prea" is not "pea"); longer ones may have a typo
        return token == word or (len(word) > 4 and len(token) > 4 and difflib.SequenceMatcher(None, token, word).ratio() >= 0.8)
    return [cid for cid, words in CROP_WORDS.items() if any(same(t, w) for t in tokens for w in words)]


def _check_crops(intent, crop_id, after, question):
    named = crops_in(question)
    if crop_id not in named:
        # With a crop that came before ("rice after wheat") the missing crop may simply not be in the table:
        # then ask, never answer about the other one.
        crop_id = named[0] if len(named) == 1 and not (intent == "gap" and after) else None
    return crop_id, (after if after in named else None)


def _knowledge(s, intent, crop_id, after, question):
    if intent == "soil":
        f = field(s["fieldId"])
        return _sourced(question, knowledge.soil(f["id"]), f)
    if intent == "sowing" and not in_romania():
        return _msg("I only have sowing dates for southern Romania, not for your area yet.",
                    detail="Sowing dates depend on the region. The ones in my table come from trials and official guidance in "
                           "southern Romania, so I will not apply them here.", replies=LIMITS_REPLY)
    if not crop_id:
        s["pending"] = {"intent": intent, "after": after, "question": question}
        return _msg("Which crop do you mean? I only have these seven.", replies={"id": "crop", "options": CROP_REPLIES})
    facts = {"sowing": lambda: knowledge.sowing(crop_id), "heat": lambda: knowledge.heat(crop_id),
             "gap": lambda: knowledge.gap(crop_id, after)}[intent]()
    return _sourced(question, facts)


def _weather(weather):
    rain, soil = analysis.overview_stats(weather)
    dry = rain["warn"] or soil["warn"]
    return _msg("It has been dry in your area lately." if dry else "Nothing unusual in your area's weather lately.",
                detail=f"{rain['label']}: {rain['value']} ({rain['note'].lower()}). Water in the soil: {soil['value'].lower()}. "
                       "These are estimates for your area from NASA POWER, not measurements on your field.",
                replies=LIMITS_REPLY)


def _from_model(s, read, question, weather):
    """Acts on what the language model understood. Returns a message, or None to continue with the usual flow."""
    if read["field"] and field(read["field"]):
        s["fieldId"] = read["field"]
    intent = read["intent"]
    if intent in ("rotation", "health"):
        s["intent"] = intent
        if intent == "rotation" and read["priority"]:
            s["priority"] = read["priority"]
        return None
    if intent == "weather":
        return _weather(weather(s.get("fieldId")))
    if intent == "limits":
        return _limits()
    if intent == "soil":
        s["intent"], s["pending"] = "soil", {"intent": "soil", "after": None, "question": question}
        return None  # _next asks for the field if it is not known
    if intent in ("sowing", "gap", "heat"):
        crop_id, after = _check_crops(intent, read["crop"], read["after"], question)
        return _knowledge(s, intent, crop_id, after, question)
    s.pop("intent", None)
    return _msg("That is outside what I can help with. Here is what I can do.", replies={"id": "intent", "options": [
        PLANT, {"value": "health", "label": "How my fields are doing"}]})


# ---------- flow ----------
def _next(s, weather):
    if not s.get("intent"):
        return _msg("I can help with two things.", replies={"id": "intent", "options": [
            PLANT, {"value": "health", "label": "How my fields are doing"}]})
    if not s.get("fieldId"):
        text = "On which field?" if s["intent"] == "rotation" else "Which field?"
        return _msg(text, replies={"id": "field", "options": [{"value": f["id"], "label": f["name"]} for f in FIELDS]})
    f = field(s["fieldId"])
    if s["intent"] == "health":
        return _health(s)
    if s["intent"] == "soil":
        return _knowledge(s, "soil", None, None, (s.get("pending") or {}).get("question", "What is my soil like?"))
    if not s.get("priority"):
        return _msg("What matters most to you?", f, replies={"id": "priority", "options": [
            {"value": "water", "label": "Saving water"}, {"value": "soil", "label": "Healthier soil"}, {"value": "income", "label": "Income"}]})
    return _rotation(s, weather)


def _field_list():
    return [{"id": f["id"], "name": f["name"], "crop": crop(f["cropId"])["name"], "ha": f["ha"]} for f in FIELDS]


ROTATION_WORDS = re.compile(r"plant|sow|rotat|next year|grow")
HEALTH_WORDS = re.compile(r"why|how|bad|weak|health|doing|green")


def converse(req: dict, weather) -> dict:
    s = SESSIONS.setdefault(req["sessionId"], {})
    if req.get("fieldId") and field(req["fieldId"]):
        s["fieldId"] = req["fieldId"]
    if req.get("intent") in ("rotation", "health"):
        s["intent"] = req["intent"]

    reply = req.get("reply")
    if reply:
        rid, value = reply.get("id"), reply.get("value")
        if rid == "field" and field(value):
            s["fieldId"] = value
            s.setdefault("intent", "health")
        elif rid == "priority" and value in ("water", "soil", "income"):
            s["priority"], s["intent"] = value, "rotation"
        elif rid == "intent" and value in ("rotation", "health"):
            s["intent"] = value
        elif rid == "crop" and value in knowledge.CROPS and s.get("pending"):
            pending = s.pop("pending")
            return _knowledge(s, pending["intent"], value, pending["after"], pending["question"])
        elif rid == "next":
            if value == "why":
                return _why(s, weather)
            if value == "limits":
                return _limits()
            if value == "priority":
                s["priority"], s["intent"] = None, "rotation"
            if value == "rotation":
                s["intent"] = "rotation"
    elif req.get("text") and (read := llm.understand(_field_list(), req["text"])):
        message = _from_model(s, read, req["text"], weather)
        if message:
            message["understoodBy"] = "model"
            return message
    elif req.get("text"):  # the language model is off or gave nothing usable: match on words
        t = _norm(req["text"])
        intent = "rotation" if ROTATION_WORDS.search(t) else "health" if HEALTH_WORDS.search(t) else None
        named = next((f for f in FIELDS if _norm(f["name"]) in t), None)
        by_crop = None
        if intent == "health" and not named:
            by_crop = next((f for f in FIELDS if _norm(crop(f["cropId"])["name"]) in t or f["cropId"] in t), None)
        if intent:
            s["intent"] = intent
        if named or by_crop:
            s["fieldId"] = (named or by_crop)["id"]
    return _next(s, weather)
