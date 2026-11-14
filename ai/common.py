"""Loading and running the model; shared by train.py, evaluate.py and serve.py."""
import json
import os
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))
HUB_ID = "Qwen/Qwen2.5-1.5B-Instruct"
LOCAL = HERE / "models" / "Qwen2.5-1.5B-Instruct"
BASE = os.environ.get("TERRACYCLE_BASE") or (str(LOCAL) if LOCAL.exists() else HUB_ID)  # a folder, or a Hugging Face id
ADAPTER = HERE / "runs" / "terracycle-lora"


def half_dtype():
    """bfloat16 on GPUs that have it natively (RTX 30 series and newer); float16 on older ones such as the T4."""
    if os.environ.get("TERRACYCLE_FP16"):  # to try the T4 path on a newer card
        return torch.float16
    return torch.bfloat16 if torch.cuda.get_device_capability()[0] >= 8 else torch.float16


def load(base=BASE, adapter=None, dtype=None):
    tok = AutoTokenizer.from_pretrained(base)
    try:
        model = AutoModelForCausalLM.from_pretrained(base, dtype=dtype or half_dtype())
    except TypeError:  # older transformers name this argument torch_dtype
        model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=dtype or half_dtype())
    model = model.to("cuda")
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter).merge_and_unload()
    model.eval()
    return tok, model


def chat_text(tok, system, user, assistant=None):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return prompt if assistant is None else (prompt, assistant + "<|im_end|>")


@torch.no_grad()
def generate(tok, model, system, user, max_new_tokens=96):
    """Greedy decoding. Returns (text, seconds)."""
    ids = tok(chat_text(tok, system, user), return_tensors="pt").to(model.device)
    start = time.perf_counter()
    out = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.eos_token_id)
    text = tok.decode(out[0, ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return text, time.perf_counter() - start


def parse_json(text):
    """The first JSON object in the text, or None."""
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a:
        return None
    try:
        obj = json.loads(text[a:b + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def passage_text(row) -> str:
    """How a literature passage is shown to the model when it reads the corpus."""
    return f"[{row['source']}, {row['locator']}] {row['text']}"


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def corpus_split():
    """(train passages, held-out passages). Every 20th passage is held out to measure what reading taught."""
    path = HERE / "data" / "corpus.jsonl"
    rows = read_jsonl(path) if path.exists() else []
    return [r for i, r in enumerate(rows) if i % 20 != 0], [r for i, r in enumerate(rows) if i % 20 == 0]
