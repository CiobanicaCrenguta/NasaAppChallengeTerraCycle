"""The two prompts of the local language model. Training (ai/) and the server use these same strings."""
import json

INTENTS = ["rotation", "health", "weather", "sowing", "gap", "heat", "soil", "limits", "other"]
CROP_IDS = ["wheat", "barley", "corn", "sunflower", "rapeseed", "peas", "soy"]
PRIORITIES = ["water", "soil", "income"]

SYSTEM_UNDERSTAND = (
    "You read a farmer's question and reply with JSON only, with the keys intent, field, crop, after, priority.\n"
    "intent: rotation (what to plant next), health (how a field or crop is doing), weather (rain, heat, water in the soil), "
    "sowing (when to sow a crop), gap (which crop may follow which, years between crops), heat (heat danger for a crop), "
    "soil (what the soil is like), limits (how you know, what you cannot see), other (anything else).\n"
    "field: the id of the field meant, from the list, or null.\n"
    "crop: the crop asked about, one of wheat, barley, corn, sunflower, rapeseed, peas, soy, or null.\n"
    "after: the crop that came before, same ids, or null.\n"
    "priority: water, soil, income or null."
)

SYSTEM_ANSWER = (
    "You answer a farmer in one or two short sentences. Use only the facts given. Never state a number that is not in the facts. "
    "Put the source id in square brackets after what it supports. If a fact is marked not confirmed, say that the value is not "
    "confirmed yet. If there are no facts, reply exactly: I have no sourced value for that yet."
)

NO_PASSAGE_ANSWER = "The passage does not answer that."
SYSTEM_PASSAGE = (
    "You answer a farmer's question from the passage given. Use only what the passage says. Never state a number that is "
    "not in the passage. Answer in one or two short sentences and end with the source id in square brackets. "
    "If the passage does not answer the question, reply exactly: " + NO_PASSAGE_ANSWER
)


def understand_user(fields, question: str) -> str:
    """fields: [{"id", "name", "crop", "ha"}]"""
    lines = "\n".join(f"- {f['id']}: {f['name']}, {f['crop']}, {f['ha']} ha" for f in fields)
    return f"Fields:\n{lines}\nQuestion: {question}"


def understand_target(intent, field=None, crop=None, after=None, priority=None) -> str:
    return json.dumps({"intent": intent, "field": field, "crop": crop, "after": after, "priority": priority})


def answer_user(question: str, facts_block: str) -> str:
    return f"Question: {question}\n{facts_block}"


def passage_user(question: str, source: str, text: str) -> str:
    return f"Question: {question}\nPassage [{source}]: {text}"
