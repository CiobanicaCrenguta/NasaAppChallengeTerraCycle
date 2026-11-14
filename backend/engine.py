"""The conversation: understands a question or a tapped reply and returns one structured answer.

Honesty rules:
- weather facts come from analysis.py (computed from NASA POWER);
- the local language model (llm.py) only reads the question and words answers from facts we give it;
  sowing, crop-gap, heat and soil answers come from knowledge.py and always carry their source;
- crop greenness is not connected yet, so field-health questions say so instead of guessing;
- the rotation pick uses a PLACEHOLDER rule table (store.CROPS) and says what it is based on.
"""
import re
import unicodedata
import uuid

import analysis
import knowledge
import llm
from store import CROPS, FIELDS, HERE, crop, field

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


# ---------- rotation (placeholder rules) ----------
def _score(c, past, priority):
    rev = list(reversed(past))
    since = rev.index(c["id"]) if c["id"] in rev else None  # 0 = last year
    if since is not None and since < c.get("min_gap", 2) - 1:
        return float("-inf")
    last = crop(past[-1])
    if priority == "water":
        s = (4 - c["water"]) * 2 + (1 if c.get("early") else 0)
    elif priority == "soil":
        s = c["soil"] * 2 + (1 if c.get("nfix") else 0)
    else:
        s = c["income"] * 2
    if c["family"] == last["family"]:
        s -= 3
    if not any(crop(p)["family"] == c["family"] for p in past[-2:]):
        s += 1
    return s


def _plan(f, priority):
    past = [h["cropId"] for h in f["history"]]
    year = f["history"][-1]["year"]
    out = []
    for _ in range(3):
        best = max(CROPS, key=lambda c: _score(c, past, priority))  # ties: first in the table
        past.append(best["id"])
        year += 1
        out.append({"year": year, "crop": best["name"], "cropId": best["id"]})
    return out


def _rotation(s):
    f, p = field(s["fieldId"]), s["priority"]
    plan = _plan(f, p)
    pick, last = crop(plan[0]["cropId"]), crop(f["cropId"])
    reasons = []
    if pick["family"] != last["family"]:
        reasons.append(f"Breaks the disease cycle after {last['name'].lower()}")
    if p == "water" and pick["water"] == 1:
        reasons.append("Needs little water")
    if p == "water" and pick.get("early"):
        reasons.append("Harvested before the July heat")
    if p == "soil" and pick.get("nfix"):
        reasons.append("Puts nitrogen back into the soil")
    if p == "income":
        reasons.append("Usually pays better than the other crops that fit")
    gap = last.get("min_gap", 2)
    return _msg(
        f"Plant {pick['name'].lower()} on {f['name']}.", f,
        cards=[{"type": "rotation", "plan": [{"year": x["year"], "crop": x["crop"]} for x in plan], "reasons": reasons[:2],
                "avoid": f"Not {last['name'].lower()} again: leave {gap} years between"}],
        replies={"id": "next", "options": [{"value": "why", "label": "Why?"}, {"value": "priority", "label": "Change priority"}]},
    )


def _why(s, weather):
    f, p = field(s.get("fieldId")), s.get("priority")
    limits = {"id": "next", "options": [{"value": "limits", "label": "What can't you see?"}]}
    if p == "water":
        text, series = analysis.july_card(weather)
        return _msg(text, f,
                    detail="With saving water as your priority, I prefer crops that finish before July or need little water. "
                           "The rain is an estimate for your area, not measured on your field.",
                    cards=[{"type": "chart", "series": series}], replies=limits)
    if p == "soil":
        return _msg("Because the soil comes first for you.", f,
                    detail="I prefer crops that put nitrogen back and leave the soil in better shape, and I keep crops of the same family apart. "
                           "These are general rotation rules, not measurements from your field.", replies=limits)
    if p == "income":
        return _msg("Because income comes first for you.", f,
                    detail="I rank the crops that fit your rotation by a rough income score. That score is not from NASA data. "
                           "Check it against local prices before you decide.", replies=limits)
    # the priority is not known (e.g. the server restarted): ask for it again rather than guess
    s["intent"] = "rotation"
    return _next(s, weather)


def _limits():
    return _msg("From space I can't see everything.", cards=[{"type": "limits", "items": [
        "Packed soil below the surface", "Pests and disease", "Blocked drains"]}])


# ---------- field health: not connected yet ----------
def _health(s):
    f = field(s["fieldId"])
    return _msg(f"I don't have satellite readings for {f['name']} yet.", f,
                detail="How green the crop is, from satellite images, is not connected yet. "
                       "What I do have is the weather for your area, on the Data page.",
                replies={"id": "next", "options": [PLANT]})


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


def _knowledge(s, intent, crop_id, after, question):
    if intent == "soil":
        f = field(s["fieldId"])
        return _sourced(question, knowledge.soil(f["id"]), f)
    if not crop_id:
        s["pending"] = {"intent": intent, "after": after, "question": question}
        return _msg("Which crop do you mean?", replies={"id": "crop", "options": CROP_REPLIES})
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
        return _weather(weather)
    if intent == "limits":
        return _limits()
    if intent == "soil":
        s["intent"], s["pending"] = "soil", {"intent": "soil", "after": None, "question": question}
        return None  # _next asks for the field if it is not known
    if intent in ("sowing", "gap", "heat"):
        return _knowledge(s, intent, read["crop"], read["after"], question)
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
    return _rotation(s)


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
