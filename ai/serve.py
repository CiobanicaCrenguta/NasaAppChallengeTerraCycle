"""Serves the fine-tuned model to the backend, on this machine only.

    .venv\\Scripts\\python -m uvicorn serve:app --host 127.0.0.1 --port 8001

POST /understand {"fields": [{"id","name","crop","ha"}], "question": "..."}  ->  {"result": {...} | null, "seconds": ...}
POST /answer     {"question": "...", "facts": [{"text","source","status"}]}  ->  {"text": "...", "safe": true|false, "seconds": ...}

Nothing leaves the laptop. The backend falls back to keyword matching and to plain fact sentences when
this service is off, slow, or returns something that fails its checks.
"""
from fastapi import FastAPI

from common import ADAPTER, generate, load, parse_json  # first: it puts ../backend on the import path

import knowledge  # noqa: E402
from llm_prompts import CROP_IDS, INTENTS, PRIORITIES, SYSTEM_ANSWER, SYSTEM_UNDERSTAND, answer_user, understand_user

app = FastAPI(title="Local language model")
tok, model = load(adapter=ADAPTER if ADAPTER.exists() else None)
TUNED = ADAPTER.exists()
generate(tok, model, SYSTEM_UNDERSTAND, "Fields:\n- a: Test, Corn, 1 ha\nQuestion: hello", 8)  # warm-up


@app.get("/health")
def health():
    return {"ok": True, "tuned": TUNED}


@app.post("/understand")
def understand(req: dict):
    fields = req.get("fields") or []
    text, seconds = generate(tok, model, SYSTEM_UNDERSTAND, understand_user(fields, req.get("question", "")), 64)
    got = parse_json(text)
    ids = {f["id"] for f in fields}
    valid = bool(got) and got.get("intent") in INTENTS and got.get("field") in ids | {None} \
        and got.get("crop") in CROP_IDS + [None] and got.get("after") in CROP_IDS + [None] and got.get("priority") in PRIORITIES + [None]
    result = {k: got.get(k) for k in ("intent", "field", "crop", "after", "priority")} if valid else None
    return {"result": result, "seconds": round(seconds, 2)}


@app.post("/answer")
def answer(req: dict):
    facts = req.get("facts") or []
    text, seconds = generate(tok, model, SYSTEM_ANSWER, answer_user(req.get("question", ""), knowledge.facts_block(facts)), 120)
    return {"text": text, "safe": knowledge.safe(text, facts), "seconds": round(seconds, 2)}
