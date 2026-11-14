"""Optional: turns literature passages into question-and-answer training rows, with a larger "teacher" model.

    python make_passage_qa.py                       # Colab: Qwen2.5-7B-Instruct in 4-bit as teacher
    python make_passage_qa.py --limit 6 --teacher models/Qwen2.5-1.5B-Instruct --no-4bit    # quick check

For each passage of data/corpus.jsonl the teacher writes one question a farmer or agronomist could ask and
a short answer taken from that passage. A row is kept only if the answer states no number that is missing
from the passage. One row in six is turned into a refusal: the same question with a passage from another
source, answered with "The passage does not answer that."

Writes data/passage_qa.jsonl; train.py picks it up by itself. The teacher's answers are not checked by a
person, only by the number rule, so read a sample before trusting them.
"""
import argparse
import json
import os
import random
import re

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from common import HERE, corpus_split
from llm_prompts import NO_PASSAGE_ANSWER, SYSTEM_PASSAGE, passage_user

ap = argparse.ArgumentParser()
ap.add_argument("--teacher", default="Qwen/Qwen2.5-7B-Instruct")
ap.add_argument("--no-4bit", action="store_true", help="load the teacher in half precision instead of 4-bit")
ap.add_argument("--limit", type=int, default=0)
ap.add_argument("--batch", type=int, default=8)
args = ap.parse_args()

TEACHER_SYSTEM = (
    "You write training material for a farm assistant. You get one passage from an agronomy publication. "
    "Write one question that a farmer or an agronomist could ask and that the passage answers, and the answer in one or two "
    "short plain sentences. Use only what the passage says. Do not use any number that is not in the passage. "
    "Do not mention 'the passage', tables, figures or equations. "
    "Reply in exactly two lines and nothing else:\nQ: <the question>\nA: <the answer>"
)


def split_pair(raw: str):
    """The question and the answer from the teacher's reply. Accepts 'Q: .. / A: ..' and also a question on
    the first line followed by the answer, with or without labels."""
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    if len(lines) == 1 and "?" in lines[0]:  # both on one line: cut after the first question mark
        head, tail = lines[0].split("?", 1)
        lines = [head + "?", tail.strip()]
    if len(lines) < 2 or not lines[1]:
        return None, None
    label = re.compile(r"^(?:Q|A|Question|Answer)\s*[:.]\s*", re.I)
    return label.sub("", lines[0]), label.sub("", " ".join(lines[1:]))


NUM = re.compile(r"\d+(?:\.\d+)?")

tok = AutoTokenizer.from_pretrained(args.teacher)
tok.padding_side = "left"
if args.no_4bit:
    model = AutoModelForCausalLM.from_pretrained(args.teacher, dtype=torch.float16).to("cuda")
else:
    from transformers import BitsAndBytesConfig
    model = AutoModelForCausalLM.from_pretrained(
        args.teacher, device_map={"": 0},
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4"))
model.eval()

passages, _ = corpus_split()  # the held-out passages stay unseen
if args.limit:
    passages = passages[:args.limit]
rng = random.Random(11)
rows, dropped = [], 0
for start in range(0, len(passages), args.batch):
    group = passages[start:start + args.batch]
    prompts = [tok.apply_chat_template([{"role": "system", "content": TEACHER_SYSTEM}, {"role": "user", "content": p["text"]}],
                                       tokenize=False, add_generation_prompt=True) for p in group]
    ids = tok(prompts, return_tensors="pt", padding=True).to("cuda")
    with torch.no_grad():
        out = model.generate(**ids, max_new_tokens=160, do_sample=False, pad_token_id=tok.eos_token_id)
    for p, sequence in zip(group, out):
        raw = tok.decode(sequence[ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        question, answer = split_pair(raw)
        if os.environ.get("QA_DEBUG"):
            print(repr(raw[:300]), "->", (question, answer))
        ok = isinstance(question, str) and isinstance(answer, str) and 15 <= len(question) <= 200 and 20 <= len(answer) <= 400 \
            and set(NUM.findall(answer)) <= set(NUM.findall(p["text"])) and "passage" not in (question + answer).lower()
        if not ok:
            dropped += 1
            continue
        if rng.random() < 1 / 6:
            other = rng.choice([x for x in passages if x["source"] != p["source"]] or passages)
            rows.append({"task": "passage", "system": SYSTEM_PASSAGE, "user": passage_user(question, other["source"], other["text"]),
                         "assistant": NO_PASSAGE_ANSWER, "from": p["id"]})
        else:
            rows.append({"task": "passage", "system": SYSTEM_PASSAGE, "user": passage_user(question, p["source"], p["text"]),
                         "assistant": f"{answer.strip()} [{p['source']}]", "from": p["id"]})
    print(f"{min(start + args.batch, len(passages))}/{len(passages)} passages, {len(rows)} rows kept, {dropped} dropped", flush=True)

rng.shuffle(rows)
with open(HERE / "data" / "passage_qa.jsonl", "w", encoding="utf-8") as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
print("wrote", len(rows), "rows to data/passage_qa.jsonl")
