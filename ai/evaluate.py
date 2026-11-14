"""Scores a model on the two tasks and writes runs/eval_<name>.json.

    python evaluate.py --name base                           # the untouched Qwen
    python evaluate.py --name tuned --adapter [folder]       # Qwen + our adapter (default runs/terracycle-lora)

understand: the 110 hand-written questions in eval_set.py (wording not seen in training).
answer:     every question the crop table can or cannot answer, plus held-out made-up facts;
            an answer passes if knowledge.safe() accepts it (no number or source outside the facts).
read:       perplexity on the literature passages held out of training (lower = the text is less
            surprising to the model). It shows what the model took from reading the literature.
"""
import argparse
import json
import math
import random
from collections import Counter, defaultdict

import gen_data
import knowledge
import torch

from common import ADAPTER, BASE, HERE, corpus_split, generate, load, parse_json, passage_text
from eval_set import FARMS, ROWS
from llm_prompts import SYSTEM_ANSWER, SYSTEM_UNDERSTAND, answer_user, understand_user

ap = argparse.ArgumentParser()
ap.add_argument("--name", required=True)
ap.add_argument("--adapter", nargs="?", const=str(ADAPTER), default=None, help="adapter folder; none = the base model alone")
ap.add_argument("--base", default=BASE)
args = ap.parse_args()
tok, model = load(args.base, adapter=args.adapter)

# ---------- understand ----------
KEYS = ["intent", "field", "crop", "after", "priority"]
hit, per_intent, wrong, times, valid = Counter(), defaultdict(lambda: [0, 0]), [], [], 0
for farm, question, *gold in ROWS:
    text, seconds = generate(tok, model, SYSTEM_UNDERSTAND, understand_user(FARMS[farm], question), 64)
    times.append(seconds)
    got = parse_json(text)
    valid += got is not None
    got = got or {}
    ok = [got.get(k) == g for k, g in zip(KEYS, gold)]
    for k, o in zip(KEYS, ok):
        hit[k] += o
    hit["all"] += all(ok)
    per_intent[gold[0]][0] += all(ok)
    per_intent[gold[0]][1] += 1
    if not all(ok):
        wrong.append({"question": question, "expected": dict(zip(KEYS, gold)), "got": got or text})
n = len(ROWS)
times.sort()
understand = {
    "questions": n, "valid_json": valid / n, "everything_right": hit["all"] / n,
    **{f"{k}_right": hit[k] / n for k in KEYS},
    "by_intent": {k: f"{a}/{b}" for k, (a, b) in per_intent.items()},
    "seconds_median": round(times[n // 2], 2), "seconds_slowest": round(times[-1], 2), "wrong": wrong,
}

# ---------- answer ----------
gen_data.rng = random.Random(2026)  # held-out made-up facts: a seed the training set never used
cases = [(kind, crop, facts) for kind, crop, facts in gen_data.REAL]
cases += [random.Random(i).choice([gen_data.syn_sowing, gen_data.syn_gap, gen_data.syn_heat, gen_data.syn_soil])() for i in range(80)]
safe_n, exact_refusal, empty_n, unsafe, a_times = 0, 0, 0, [], []
for kind, crop, facts in cases:
    question = gen_data.question_for(kind, crop)
    text, seconds = generate(tok, model, SYSTEM_ANSWER, answer_user(question, knowledge.facts_block(facts)), 120)
    a_times.append(seconds)
    ok = knowledge.safe(text, facts)
    safe_n += ok
    if not facts:
        empty_n += 1
        exact_refusal += text.strip() == knowledge.NO_FACTS
    if not ok:
        unsafe.append({"question": question, "facts": [f["text"] for f in facts], "got": text})
a_times.sort()
answer = {
    "cases": len(cases), "from_crop_table": len(gen_data.REAL), "safe": safe_n / len(cases),
    "no_facts_cases": empty_n, "no_facts_refused": exact_refusal / max(1, empty_n),
    "seconds_median": round(a_times[len(cases) // 2], 2), "seconds_slowest": round(a_times[-1], 2), "unsafe": unsafe,
}

# ---------- read ----------
_, held_out = corpus_split()
total = tokens = 0
with torch.no_grad():
    for row in held_out:
        ids = tok(passage_text(row), return_tensors="pt", truncation=True, max_length=512).to(model.device)
        n = ids["input_ids"].shape[1] - 1
        total += model(**ids, labels=ids["input_ids"]).loss.float().item() * n
        tokens += n
read = {"held_out_passages": len(held_out), "perplexity": round(math.exp(total / tokens), 2) if tokens else None}

out = {"name": args.name, "adapter": args.adapter, "understand": understand, "answer": answer, "read": read}
(HERE / "runs").mkdir(exist_ok=True)
(HERE / "runs" / f"eval_{args.name}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
short = {k: v for k, v in understand.items() if k != "wrong"}
print(json.dumps({"understand": short, "answer": {k: v for k, v in answer.items() if k != "unsafe"}, "read": read}, indent=1))
