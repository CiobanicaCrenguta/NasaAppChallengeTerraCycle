"""Client for the local language model (ai/serve.py). Every call may return None; callers must cope.

The model does two things only: it reads a question into {intent, field, crop, after, priority}, and it
words an answer from facts we hand it. An answer is used only if knowledge.safe() accepts it.
"""
import json
import os
import time
import urllib.request

import knowledge

URL = os.environ.get("LLM_URL", "http://127.0.0.1:8001")
TIMEOUT_S = 4.0
_down_until = 0.0  # after a failure, skip the model for a while instead of waiting on every question


def _post(path: str, body: dict):
    global _down_until
    if time.time() < _down_until:
        return None
    try:
        req = urllib.request.Request(URL + path, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        _down_until = time.time() + 30
        return None


def understand(fields, question: str):
    """{intent, field, crop, after, priority} or None."""
    got = _post("/understand", {"fields": fields, "question": question})
    return got.get("result") if got else None


def answer(question: str, facts) -> tuple[str, bool]:
    """(text, written_by_model). Falls back to the plain fact sentences."""
    if facts:
        got = _post("/answer", {"question": question, "facts": facts})
        if got and knowledge.safe(got.get("text", ""), facts):
            return got["text"], True
    return knowledge.plain_answer(facts), False
