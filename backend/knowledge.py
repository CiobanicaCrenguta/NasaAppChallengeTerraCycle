"""Looks up sourced facts in crops.json and the baked field profiles.

A fact is {"text": ..., "source": "S1", "status": "verificat" | "de_confirmat"}. The language model
only ever sees these facts; `plain_answer` builds the same answer without a model, and `safe` checks
that a model's sentence states no number and no source that is not in the facts.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
CROPS = {c["id"]: c for c in json.loads((HERE / "crops.json").read_text(encoding="utf-8"))["crops"]}
NO_FACTS = "I have no sourced value for that yet."
UNCONFIRMED = "This value is not confirmed yet."


def _fact(text, node):
    return {"text": text, "source": node["source"], "status": node["status"]}


def _span(value, unit=""):
    if isinstance(value, list):
        return f"{value[0]} to {value[1]}{unit}"
    return f"{value}{unit}"


def name(crop_id):
    return CROPS[crop_id]["name"].lower() if crop_id in CROPS else crop_id


def sowing(crop_id):
    out = []
    s = CROPS.get(crop_id, {}).get("sowing", {})
    for key, label in (("best_window", "best sowing window"), ("window", "sowing window"),
                       ("autumn_type_window", "sowing window for autumn varieties"), ("early_sowing_tested", "early sowing tested")):
        node = s.get(key)
        if node:
            out.append(_fact(f"{name(crop_id)}, {label}: {node['value']}", node))
    return out


def gap(crop_id, after=None):
    out = []
    r = CROPS.get(crop_id, {}).get("rotation", {})
    avoid = r.get("avoid_after")
    if after and avoid and after in avoid["value"]:
        out.append(_fact(f"{name(crop_id)} should not follow {name(after)}", avoid))
    hosts = r.get("min_gap_from_other_hosts")
    if after and hosts and after in hosts.get("hosts", []):
        out.append(_fact(f"years between {name(crop_id)} and {name(after)}: at least {hosts['value']}", hosts))
    # the same rule seen from the other crop
    other = CROPS.get(after, {}).get("rotation", {}) if after else {}
    hosts = other.get("min_gap_from_other_hosts")
    if hosts and crop_id in hosts.get("hosts", []):
        out.append(_fact(f"years between {name(after)} and {name(crop_id)}: at least {hosts['value']}", hosts))
    if not after or after == crop_id:
        node = r.get("min_gap_years")
        if node:
            text = f"years between {name(crop_id)} crops: {_span(node['value'])}"
            if isinstance(node["value"], list):
                text += f"; value used: {node['engine_value']}"
            out.append(_fact(text, node))
        node = r.get("max_years_after_itself")
        if node:
            out.append(_fact(f"{name(crop_id)} after {name(crop_id)}: at most {node['value']} year, only in extreme cases", node))
        node = r.get("self_tolerant")
        if node:
            out.append(_fact(f"{name(crop_id)} can follow itself (self-tolerant crop)", node))
    return out


def heat(crop_id):
    out = []
    h = CROPS.get(crop_id, {}).get("heat_at_flowering", {})
    node = h.get("attention")
    if node:
        text = f"{name(crop_id)}, warning level at flowering: daily maximum above {_span(node['value'])} °C"
        if isinstance(node["value"], list):
            text += f"; value used: {node['engine_value']} °C"
        out.append(_fact(text, node))
    node = h.get("loss")
    if node:
        out.append(_fact(f"{name(crop_id)}, pollination starts to fail: daily maximum above {node['value']} °C", node))
    return out


def soil(field_id):
    path = HERE / "data" / "baked" / field_id / "profile.json"
    if not path.exists():
        return []
    profile = json.loads(path.read_text(encoding="utf-8"))
    s = profile.get("static", {}).get("soil")
    if not s or profile.get("sources", {}).get("soil", {}).get("status") != "ok":
        return []
    text = f"soil in the top 30 cm: {s['texture']}, {s['clay_pct']}% clay, {s['sand_pct']}% sand"
    if "ph" in s:
        text += f", pH {s['ph']}"
    return [{"text": text + " (estimate for the area, 250 m grid)", "source": "SoilGrids", "status": "verificat"}]


def facts_block(facts):
    if not facts:
        return "Facts: none"
    return "Facts:\n" + "\n".join(f"- {f['text']} [{f['source']}, {'confirmed' if f['status'] == 'verificat' else 'not confirmed'}]"
                                  for f in facts)


def plain_answer(facts):
    """The answer without a language model: the facts, one per sentence, each with its source."""
    if not facts:
        return NO_FACTS
    parts = []
    for f in facts:
        sentence = f["text"][0].upper() + f["text"][1:] + f". [{f['source']}]"
        if f["status"] != "verificat":
            sentence += " " + UNCONFIRMED
        parts.append(sentence)
    return " ".join(parts)


_NUM = re.compile(r"\d+(?:\.\d+)?")
_SRC = re.compile(r"\[([^\]]+)\]")


def safe(answer: str, facts) -> bool:
    """True if the sentence states no number and cites no source beyond the facts, and cites at least one."""
    if not facts:
        return answer.strip() == NO_FACTS
    block = " ".join(f["text"] for f in facts)
    allowed_numbers = set(_NUM.findall(block))
    sources = {f["source"] for f in facts}
    cited = set(_SRC.findall(answer))
    text = _SRC.sub(" ", answer)
    if not cited or not cited <= sources:
        return False
    if not set(_NUM.findall(text)) <= allowed_numbers:
        return False
    if any(f["status"] != "verificat" for f in facts if f["source"] in cited) and "not confirmed" not in answer:
        return False
    return True
