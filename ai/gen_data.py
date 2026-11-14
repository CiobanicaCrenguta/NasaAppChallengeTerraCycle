"""Builds the training set for the local model: data/train.jsonl and data/val.jsonl.

Two tasks, one model:
  understand  farmer question + list of fields  ->  JSON {intent, field, crop, after, priority}
  answer      question + sourced facts          ->  one or two sentences that use only those facts

The answer examples take their facts from backend/crops.json (the literature in SOURCES.md) and from
made-up facts with random crops, numbers and source ids. The made-up ones are there so the model learns
to copy what the facts say instead of remembering numbers.

    python gen_data.py            # writes data/train.jsonl, data/val.jsonl
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))
import knowledge  # noqa: E402
from llm_prompts import (CROP_IDS, SYSTEM_ANSWER, SYSTEM_UNDERSTAND, answer_user, understand_target,  # noqa: E402
                         understand_user)

rng = random.Random(7)

# ---------- words ----------
CROP_WORDS = {
    "wheat": ["wheat", "winter wheat", "wheat"], "barley": ["barley", "winter barley"], "corn": ["corn", "maize", "corn"],
    "sunflower": ["sunflower", "sunflowers"], "rapeseed": ["rapeseed", "canola", "oilseed rape"], "peas": ["peas", "field peas"],
    "soy": ["soy", "soybean", "soybeans", "soya"],
}
FIELD_CROP_NAME = {"wheat": "Winter wheat", "barley": "Winter barley", "corn": "Corn", "sunflower": "Sunflower",
                   "rapeseed": "Rapeseed", "peas": "Peas", "soy": "Soybean"}
OTHER_CROPS = ["potatoes", "tomatoes", "alfalfa", "sugar beet", "oats", "rye", "lentils", "sorghum", "onions", "vines"]
FIELD_NAMES = [
    "Valea Mare", "Dealul Viei", "Lunca Jiului", "Pădurea Veche", "La Fântână", "Câmpul Lung", "Podul Vechi", "Sub Deal",
    "La Moară", "Grădina Mare", "Hill Field", "Long Acre", "Mill Meadow", "North Plot", "River Bend", "Oak Corner", "Home Field",
    "Stony Rise", "Lower Forty", "Church Field", "Les Grands Champs", "Le Pré Haut", "Campo Alto", "La Vega", "El Olivar",
    "Campo Grande", "Feld am Bach", "Obere Wiese", "Kirchacker", "Shamba Kubwa", "Mto Field", "Khet One", "Nadi Khet",
    "Parcela 3", "Plot 12", "Field A", "Field B", "Lot 7", "The Triangle", "Back Field", "Windmill Plot", "Red Soil Field",
    "Poiana", "Livada Veche", "Bălți Est", "Tarlaua 4", "Sunny Slope", "Marsh Edge", "Quarry Field", "Station Field",
]
PRIO = {
    "water": ["that needs little water", "that saves water", "for a dry year", "because water is short", "that copes with drought",
              "since I cannot irrigate"],
    "soil": ["that improves the soil", "to build up the soil", "that is good for soil health", "to rest the soil",
             "that puts nitrogen back"],
    "income": ["that earns the most", "for the best income", "that pays well", "to make the most money", "with the best profit"],
}

T = {  # templates; {F} field phrase with leading space or empty, {C} crop, {D} second crop, {P} priority phrase
    "rotation": [
        "What should I plant next year{F}?", "what do i sow next{F}", "What do you recommend{F} for next season?",
        "Plan my rotation{F}.", "what to grow{F} next", "Which crop should come next{F}?", "What is a good crop{F} for next year?",
        "Next year{F}: what do I put in?", "Help me choose the next crop{F}.", "what should follow this year's crop{F}",
        "I need a rotation plan{F}.", "What goes in{F} after harvest?", "Suggest a crop{F}.", "what now{F}, what do I plant",
    ],
    "rotation_after": [
        "What should I plant after {C}{F}?", "what comes after {C}{F}", "Which crop should follow {C}{F}?",
        "After {C}, what do I sow{F}?", "I had {C}{F} this year. What next?", "{C} is coming off{F}, what do i plant then",
    ],
    "rotation_prio": [
        "I want a crop {P}{F}. What do you suggest?", "What should I plant{F} {P}?", "Give me a crop{F} {P}.",
        "next year{F} i need something {P}", "Which crop{F} {P}?", "Plan my rotation{F}, something {P}.",
    ],
    "health_field": [
        "How is{F} doing?", "Is{F} healthy?", "How green is{F}?", "Anything wrong with{F}?", "check{F} for me",
        "Which part of{F} is weaker?", "How does{F} look from the satellite?", "is{F} ok", "Any problem on{F} this year?",
        "show me how{F} is growing", "Is{F} behind compared to other years?",
    ],
    "health_crop": [
        "Why did my {C} do badly?", "my {C} looks weak, why", "Is my {C} growing well this year?", "How is the {C} doing?",
        "the {C} is yellow in places, what is going on", "Why is my {C} worse than last year?", "what happened to my {C}",
        "Is the {C} greener than usual?",
    ],
    "health_none": ["How are my fields doing?", "Is everything ok on my land?", "any field in trouble?", "How do my crops look?",
                    "which of my fields is doing worst"],
    "weather": [
        "Has it been dry lately?", "How much rain did we get this month?", "Is the soil wet enough?", "was this year drier than usual",
        "How hot was the summer?", "rain in the last 30 days?", "Is there enough water in the ground?", "Did we get less rain than normal?",
        "is it a drought", "How does this year's rain compare to other years?", "How wet is the ground now?", "was july dry",
        "How many heavy rain days did we have?", "is the weather unusual this year",
    ],
    "sowing": [
        "When should I sow {C}?", "best time to plant {C}", "Is it too late to sow {C}?", "when do i put {C} in the ground",
        "sowing date for {C}?", "What is the right window for sowing {C}?", "When do people here sow {C}?", "can i still sow {C} now",
        "When to drill {C}?", "{C}: when to sow", "Should I sow {C} early or late?", "what month for {C}",
    ],
    "gap_two": [
        "Can I plant {C} after {D}?", "can {C} follow {D}", "Is it ok to grow {C} after {D}?", "{C} after {D}, good idea?",
        "I had {D} this year. Can I sow {C} now?", "is {D} a bad crop to have before {C}", "Should {C} come after {D}?",
        "How long between {D} and {C}?",
    ],
    "gap_one": [
        "How many years between {C} crops?", "how long should I wait before {C} again", "Can I grow {C} two years in a row?",
        "Is it ok to plant {C} after {C}?", "how often can i grow {C} on the same field", "{C} every year, is that a problem",
        "What break does {C} need?", "When can {C} come back on the same field?",
    ],
    "heat": [
        "Is heat a problem for {C} at flowering?", "What temperature hurts {C}?", "how hot is too hot for {C}",
        "will a heatwave damage my {C}", "At what temperature does {C} pollination fail?", "Does {C} suffer above 35 degrees?",
        "hot days and {C}, when should I worry", "Can {C} stand the heat in July?", "what heat is dangerous for {C} flowers",
    ],
    "soil": [
        "What kind of soil do I have{F}?", "Is my soil{F} clay or sand?", "soil type{F}?", "What is the pH{F}?",
        "tell me about the soil{F}", "Is the soil{F} heavy or light?", "how much clay is there{F}", "what is my soil like{F}",
    ],
    "limits": [
        "How do you know that?", "Where does this data come from?", "What can't you see?", "can I trust this", "Which satellites do you use?",
        "how sure are you", "Is this measured on my field or estimated?", "why should i believe you", "How accurate is this?",
        "what are you not able to tell me", "who says so", "Is this from NASA?",
    ],
    "other": [
        "What is the price of {C}?", "Which tractor should I buy?", "hello", "What is this bug on my leaves?", "Can you get me a subsidy?",
        "tell me a joke", "who made you", "How much fertilizer for {C}?", "should I spray fungicide on the {C}", "What is the weather tomorrow?",
        "thanks", "Where can I sell my {C}?", "what herbicide kills thistles", "How do I fix my seeder?", "good morning",
        "Can you call the vet?", "what variety of {C} is best", "how much seed per hectare for {C}", "ok", "When should I harvest {C}?",
        "how deep should I plough", "Is it going to rain next week?", "what is the capital of France",
    ],
}
FILLERS = ["", "", "", "", "hi, ", "hello, ", "please, ", "quick question: ", "one more thing: ", "ok so ", "hey, "]


def noise(q: str) -> str:
    if rng.random() < 0.35:
        q = q.lower()
    if rng.random() < 0.3:
        q = q.rstrip("?.")
    if rng.random() < 0.12:  # one typo: drop or swap a letter inside a longer word
        words = q.split(" ")
        idx = [i for i, w in enumerate(words) if len(w) > 4 and w.isalpha()]
        if idx:
            i = rng.choice(idx)
            w, k = words[i], rng.randrange(1, len(words[i]) - 2)
            words[i] = w[:k] + w[k + 1:] if rng.random() < 0.5 else w[:k] + w[k + 1] + w[k] + w[k + 2:]
            q = " ".join(words)
    filler = rng.choice(FILLERS)
    if filler:
        q = filler + q[0].lower() + q[1:]
    return q


# ---------- farms ----------
def farm():
    n = rng.choice([1, 2, 3, 3, 4, 4, 5, 6])
    names = rng.sample(FIELD_NAMES, n)
    ids = rng.sample(["a", "b", "c", "d", "e", "f1", "f2", "f3", "f4", "f5", "f6", "vm", "dv", "lj", "pv", "n1", "s2", "p7"], n)
    out = []
    for i in range(n):
        ha = rng.choice([round(rng.uniform(0.03, 0.9), 2), round(rng.uniform(1, 15), 1), round(rng.uniform(15, 120), 1)])
        out.append({"id": ids[i], "name": names[i], "crop": FIELD_CROP_NAME[rng.choice(CROP_IDS)], "ha": ha})
    return out


def crop_id_of(field):
    return next(k for k, v in FIELD_CROP_NAME.items() if v == field["crop"])


def field_ref(fields, allow_none=True):
    """Returns (phrase to put after a verb, field id or None, crop id named in the phrase or None)."""
    kinds = ["name", "name", "name", "lower", "crop", "size"] + (["none", "none"] if allow_none else [])
    kind = rng.choice(kinds)
    f = rng.choice(fields)
    if kind == "none":
        return "", None, None
    if kind == "name":
        return " " + rng.choice(["on ", "at ", "for "]) + f["name"], f["id"], None
    if kind == "lower":
        return " on " + f["name"].lower(), f["id"], None
    if kind == "crop":
        cid = rng.choice(CROP_IDS)
        owners = [x for x in fields if crop_id_of(x) == cid]
        phrase = " on " + rng.choice(["my {} field", "the {} field", "the field with {}"]).format(rng.choice(CROP_WORDS[cid]))
        return phrase, (owners[0]["id"] if len(owners) == 1 else None), cid
    sizes = sorted(fields, key=lambda x: x["ha"])
    if len(fields) < 2 or sizes[0]["ha"] == sizes[1]["ha"] or sizes[-1]["ha"] == sizes[-2]["ha"]:
        return " on " + f["name"], f["id"], None
    if rng.random() < 0.5:
        return " on " + rng.choice(["my biggest field", "the largest field", "my big field"]), sizes[-1]["id"], None
    return " on " + rng.choice(["my smallest field", "the small plot", "my smallest plot"]), sizes[0]["id"], None


def bare_field(fields):
    """A field named without a preposition, for 'How is X doing?'."""
    phrase, fid, _ = field_ref(fields, allow_none=False)
    for prep in (" on ", " at ", " for "):
        if phrase.startswith(prep):
            return " " + phrase[len(prep):], fid
    return phrase, fid


def crop_word(cid=None):
    cid = cid or rng.choice(CROP_IDS)
    return cid, rng.choice(CROP_WORDS[cid])


def understand_example():
    fields = farm()
    kind = rng.choices(
        ["rotation", "rotation_after", "rotation_prio", "health_field", "health_crop", "health_none", "weather", "sowing",
         "gap_two", "gap_one", "heat", "soil", "limits", "other"],
        weights=[10, 5, 6, 8, 6, 2, 8, 9, 7, 6, 8, 6, 6, 13])[0]
    tpl = rng.choice(T[kind])
    intent, field, crop, after, priority = kind.split("_")[0], None, None, None, None
    q = tpl
    if kind in ("rotation", "rotation_after", "rotation_prio", "soil"):
        phrase, field, _ = field_ref(fields)
        q = q.replace("{F}", phrase)
    if kind == "rotation_after":
        after, word = crop_word()
        q = q.replace("{C}", word)
    if kind == "rotation_prio":
        priority = rng.choice(list(PRIO))
        q = q.replace("{P}", rng.choice(PRIO[priority]))
    if kind == "health_field":
        phrase, field = bare_field(fields)
        q = q.replace("{F}", phrase)
    if kind == "health_crop":
        crop, word = crop_word(crop_id_of(rng.choice(fields)) if rng.random() < 0.7 else None)
        owners = [x for x in fields if crop_id_of(x) == crop]
        field = owners[0]["id"] if len(owners) == 1 else None
        q = q.replace("{C}", word)
    if kind in ("sowing", "heat", "gap_one"):
        if rng.random() < 0.08:  # a crop outside the table: intent stays, crop is null
            q = q.replace("{C}", rng.choice(OTHER_CROPS))
        else:
            crop, word = crop_word()
            q = q.replace("{C}", word)
    if kind == "gap_two":
        crop, word = crop_word()
        after, word2 = crop_word(rng.choice([c for c in CROP_IDS if c != crop]))
        q = q.replace("{C}", word).replace("{D}", word2)
    if kind == "other":
        q = q.replace("{C}", rng.choice(CROP_WORDS[rng.choice(CROP_IDS)] + OTHER_CROPS))
    return {"task": "understand", "system": SYSTEM_UNDERSTAND, "user": understand_user(fields, noise(q)),
            "assistant": understand_target(intent, field, crop, after, priority)}


# ---------- answer task ----------
def cap(s):
    return s[0].upper() + s[1:]


def unconf(facts, used):
    return " " + knowledge.UNCONFIRMED if any(f["status"] != "verificat" for f in facts if f["source"] in used) else ""


SYN_CROPS = ["winter wheat", "winter barley", "corn", "sunflower", "rapeseed", "peas", "soybean", "oats", "lentil", "chickpea",
             "sorghum", "sugar beet", "potato", "rye", "flax", "millet"]
WINDOWS = ["late August to early September", "10 to 25 October", "first ten days of October", "10 to 15 April",
           "last week of April to first week of May", "second ten days of October", "mid March to early April", "1 to 15 May",
           "late September to late October", "5 to 20 March", "first half of November", "20 April to 5 May", "early June",
           "15 to 30 September", "third ten days of March", "last ten days of April"]


def src():
    return f"S{rng.randint(1, 40)}"


def status():
    return "verificat" if rng.random() < 0.7 else "de_confirmat"


def syn_sowing():
    c = rng.choice(SYN_CROPS)
    facts = []
    if rng.random() < 0.3:
        facts.append({"text": f"{c}, best sowing window: {rng.choice(WINDOWS)}", "source": src(), "status": status()})
    facts.append({"text": f"{c}, sowing window: {rng.choice(WINDOWS)}", "source": src(), "status": status()})
    return "sowing", c, facts


def syn_gap():
    c, d = rng.sample(SYN_CROPS, 2)
    r = rng.random()
    if r < 0.3:
        n = rng.randint(2, 7)
        return "gap_one", c, [{"text": f"years between {c} crops: {n}", "source": src(), "status": status()}]
    if r < 0.5:
        a = rng.randint(2, 5)
        b = a + rng.randint(1, 2)
        u = rng.choice([a, b])
        return "gap_one", c, [{"text": f"years between {c} crops: {a} to {b}; value used: {u}", "source": src(), "status": status()}]
    if r < 0.65:
        return "gap_two", (c, d), [{"text": f"{c} should not follow {d}", "source": src(), "status": status()}]
    if r < 0.8:
        n = rng.randint(2, 6)
        return "gap_two", (c, d), [{"text": f"years between {d} and {c}: at least {n}", "source": src(), "status": status()}]
    if r < 0.9:
        return "gap_one", c, [{"text": f"{c} can follow itself (self-tolerant crop)", "source": src(), "status": status()}]
    return "gap_one", c, [{"text": f"{c} after {c}: at most 1 year, only in extreme cases", "source": src(), "status": status()}]


def syn_heat():
    c = rng.choice(SYN_CROPS)
    facts = []
    a = rng.randint(27, 36)
    if rng.random() < 0.75:
        if rng.random() < 0.3:
            b = a + rng.randint(2, 5)
            facts.append({"text": f"{c}, warning level at flowering: daily maximum above {a} to {b} °C; value used: {a} °C",
                          "source": src(), "status": status()})
        else:
            facts.append({"text": f"{c}, warning level at flowering: daily maximum above {a} °C", "source": src(), "status": status()})
    if not facts or rng.random() < 0.7:
        facts.append({"text": f"{c}, pollination starts to fail: daily maximum above {rng.randint(34, 44)} °C",
                      "source": src(), "status": status()})
    return "heat", c, facts


def syn_soil():
    tex = rng.choice(["clay", "silty clay", "loam", "sandy loam", "silt loam", "clay loam", "sand", "loamy sand", "sandy clay loam"])
    clay, sand = round(rng.uniform(3, 60), 1), round(rng.uniform(3, 85), 1)
    text = f"soil in the top 30 cm: {tex}, {clay}% clay, {sand}% sand"
    if rng.random() < 0.8:
        text += f", pH {round(rng.uniform(4.8, 8.4), 1)}"
    return "soil", None, [{"text": text + " (estimate for the area, 250 m grid)", "source": "SoilGrids", "status": "verificat"}]


def render(facts):
    """A natural answer built from fact texts in the formats that knowledge.py produces."""
    if not facts:
        return knowledge.NO_FACTS
    out = []
    for f in facts:
        t, s = f["text"], f"[{f['source']}]"
        nc = "" if f["status"] == "verificat" else " " + knowledge.UNCONFIRMED
        if ", best sowing window: " in t:
            c, w = t.split(", best sowing window: ")
            out.append(rng.choice([f"The best sowing window for {c} is {w}. {s}", f"{cap(c)} does best when sown in this window: {w}. {s}"]) + nc)
        elif ", sowing window for autumn varieties: " in t:
            c, w = t.split(", sowing window for autumn varieties: ")
            out.append(f"For autumn varieties of {c}, the sowing window is {w}. {s}" + nc)
        elif ", sowing window: " in t:
            c, w = t.split(", sowing window: ")
            first = not out
            out.append((rng.choice([f"The sowing window for {c} is {w}. {s}", f"For {c}, the sowing window is {w}. {s}"])
                        if first else f"The wider window is {w}. {s}") + nc)
        elif ", early sowing tested: " in t:
            c, w = t.split(", early sowing tested: ")
            out.append(f"Sowing as early as {w} has been tested. {s}" + nc)
        elif t.startswith("years between ") and " crops: " in t:
            c, rest = t[len("years between "):].split(" crops: ")
            if "; value used: " in rest:
                span, used = rest.split("; value used: ")
                out.append(f"Leave {span} years between {c} crops; I use {used}. {s}" + nc)
            else:
                out.append(rng.choice([f"Leave {rest} years between {c} crops. {s}",
                                       f"Wait {rest} years before growing {c} on the same field again. {s}"]) + nc)
        elif " should not follow " in t:
            c, d = t.split(" should not follow ")
            out.append(rng.choice([f"Do not plant {c} after {d}. {s}", f"{cap(c)} should not follow {d}. {s}"]) + nc)
        elif t.startswith("years between ") and ": at least " in t:
            pair, n = t[len("years between "):].split(": at least ")
            out.append(f"Leave at least {n} years between {pair}. {s}" + nc)
        elif " can follow itself" in t:
            c = t.split(" can follow itself")[0]
            out.append(f"Yes, {c} can follow itself. {s}" + nc)
        elif ": at most 1 year, only in extreme cases" in t:
            c = t.split(" after ")[0]
            out.append(f"{cap(c)} can follow itself for at most 1 year, and only in extreme cases. {s}" + nc)
        elif ", warning level at flowering: daily maximum above " in t:
            c, rest = t.split(", warning level at flowering: daily maximum above ")
            if "; value used: " in rest:
                span, used = rest.split("; value used: ")
                out.append(f"For {c}, days above {span} at flowering are a warning; I use {used}. {s}" + nc)
            else:
                out.append(f"For {c}, days above {rest} at flowering are a warning. {s}" + nc)
        elif ", pollination starts to fail: daily maximum above " in t:
            c, v = t.split(", pollination starts to fail: daily maximum above ")
            out.append((f"Above {v}, pollination starts to fail. {s}" if out else f"For {c}, pollination starts to fail above {v}. {s}") + nc)
        elif t.startswith("soil in the top 30 cm: "):
            body = t[len("soil in the top 30 cm: "):].replace(" (estimate for the area, 250 m grid)", "")
            out.append(f"Your soil is {body}. This is an estimate for your area, not a measurement on your field. {s}")
        else:
            raise ValueError(t)
    return " ".join(out)


def question_for(kind, crop):
    if kind == "gap_two":
        return rng.choice(T["gap_two"]).replace("{C}", crop[0]).replace("{D}", crop[1])
    if kind == "soil":
        return rng.choice(T["soil"]).replace("{F}", "")
    return rng.choice(T[kind]).replace("{C}", crop or "")


def real_cases():
    """Every question the literature in crops.json can answer, and the ones it cannot."""
    cases = []
    for c in CROP_IDS:
        cases.append(("sowing", knowledge.name(c), knowledge.sowing(c)))
        cases.append(("heat", knowledge.name(c), knowledge.heat(c)))
        cases.append(("gap_one", knowledge.name(c), knowledge.gap(c)))
        for d in CROP_IDS:
            if d != c:
                cases.append(("gap_two", (knowledge.name(c), knowledge.name(d)), knowledge.gap(c, d)))
    for fid in ("vm", "dv", "lj", "pv"):
        cases.append(("soil", None, knowledge.soil(fid)))
    return cases


def answer_example(real):
    if real:
        kind, crop, facts = rng.choice(REAL)
    else:
        kind, crop, facts = rng.choice([syn_sowing, syn_gap, syn_heat, syn_soil])()
        if rng.random() < 0.08:
            facts = []
    target = render(facts)
    assert knowledge.safe(target, facts), (target, facts)
    return {"task": "answer", "system": SYSTEM_ANSWER, "user": answer_user(noise(question_for(kind, crop)), knowledge.facts_block(facts)),
            "assistant": target}


REAL = real_cases()


def main():
    rows = [understand_example() for _ in range(7000)]
    rows += [answer_example(real=True) for _ in range(900)] + [answer_example(real=False) for _ in range(2100)]
    rng.shuffle(rows)
    seen, unique = set(), []
    for r in rows:
        key = (r["user"], r["assistant"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    (HERE / "data").mkdir(exist_ok=True)
    val, train = unique[:400], unique[400:]
    for name, part in (("train", train), ("val", val)):
        with open(HERE / "data" / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in part:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"train {len(train)}, val {len(val)}; understand {sum(r['task'] == 'understand' for r in unique)}, "
          f"answer {sum(r['task'] == 'answer' for r in unique)}")


if __name__ == "__main__":
    main()
