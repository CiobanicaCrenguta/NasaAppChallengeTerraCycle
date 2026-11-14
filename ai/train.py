"""Fine-tunes Qwen2.5-1.5B-Instruct for TerraCycle with a LoRA adapter.

    python train.py --out /content/drive/MyDrive/terracycle     # Colab; add --resume after a disconnect
    python train.py --limit 300 --epochs 1                       # quick check that everything runs

One model learns these things in the same run:
  read        the specialist literature itself (data/corpus.jsonl): plain passages, loss on every token.
              This is the domain training: crops, water, heat and soil, as the sources write about them.
  understand  a farmer's question -> JSON (data/train.jsonl)
  answer      question + sourced facts -> a short answer that uses only those facts (data/train.jsonl)
  passage     optional (data/passage_qa.jsonl, made by make_passage_qa.py): question + passage -> answer

For understand, answer and passage the loss is counted only on the assistant's reply.

The base weights stay frozen. Settings adapt to the GPU: float16 with gradient scaling on a T4, bfloat16
on newer cards; batch size from the memory available. Progress is saved every --save-every updates, so a
Colab disconnect loses a few minutes at most. The adapter with the lowest validation loss is kept in
<out>/terracycle-lora.
"""
import argparse
import json
import math
import random
import shutil
import time
from pathlib import Path

import torch
from peft import LoraConfig, PeftModel, get_peft_model
from torch.utils.checkpoint import checkpoint

from common import BASE, HERE, chat_text, corpus_split, half_dtype, load, passage_text, read_jsonl

ap = argparse.ArgumentParser()
ap.add_argument("--base", default=BASE, help="folder or Hugging Face id of the base model")
ap.add_argument("--out", default=str(HERE / "runs"), help="where checkpoints and the adapter go (a Drive folder on Colab)")
ap.add_argument("--epochs", type=float, default=3)
ap.add_argument("--batch", type=int, default=0, help="rows per step; 0 picks it from the GPU memory")
ap.add_argument("--accum", type=int, default=0, help="steps added up before an update; 0 = whatever makes 16 rows per update")
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--rank", type=int, default=32)
ap.add_argument("--read-repeat", type=int, default=2, help="how many times each literature passage appears per epoch")
ap.add_argument("--max-tokens", type=int, default=512)
ap.add_argument("--save-every", type=int, default=100)
ap.add_argument("--eval-every", type=int, default=200)
ap.add_argument("--limit", type=int, default=0, help="use only this many rows of each kind (for a quick check)")
ap.add_argument("--resume", action="store_true")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

OUT = Path(args.out)
CKPT, BEST = OUT / "checkpoint", OUT / "terracycle-lora"
OUT.mkdir(parents=True, exist_ok=True)
gpu_gb = torch.cuda.get_device_properties(0).total_memory / 2**30
BATCH = args.batch or (16 if gpu_gb >= 14 else 8 if gpu_gb >= 7.5 else 4)
ACCUM = args.accum or max(1, 16 // BATCH)
DTYPE = half_dtype()
SCALE = DTYPE == torch.float16  # float16 needs gradient scaling; bfloat16 does not
print(f"GPU {torch.cuda.get_device_name(0)}, {gpu_gb:.0f} GB: {str(DTYPE).split('.')[-1]}, batch {BATCH} x {ACCUM}", flush=True)

torch.manual_seed(args.seed)
tok, model = load(args.base, dtype=DTYPE)
model.gradient_checkpointing_enable()  # keeps one step within a few GB; costs about a third in speed
LORA = LoraConfig(r=args.rank, lora_alpha=2 * args.rank, lora_dropout=0.05, task_type="CAUSAL_LM",
                  target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"])
resuming = args.resume and (CKPT / "state.pt").exists()
model = PeftModel.from_pretrained(model, CKPT, is_trainable=True) if resuming else get_peft_model(model, LORA)
for p in model.parameters():
    if p.requires_grad:
        p.data = p.data.float()  # the adapter trains in full precision
model.train()
model.print_trainable_parameters()
qwen = model.base_model.model  # the Qwen model with the adapter layers inside
TRAINABLE = [p for p in model.parameters() if p.requires_grad]


# ---------- data ----------
def encode(row):
    """Token ids and labels; -100 marks tokens that do not count in the loss."""
    if row["task"] == "read":
        ids = tok(row["text"], add_special_tokens=False)["input_ids"][:args.max_tokens - 1] + [tok.eos_token_id]
        return ids, list(ids)
    prompt, reply = chat_text(tok, row["system"], row["user"], row["assistant"])
    p = tok(prompt, add_special_tokens=False)["input_ids"]
    r = tok(reply, add_special_tokens=False)["input_ids"]
    p = p[:max(1, args.max_tokens - len(r))]
    return p + r, [-100] * len(p) + r


def cut(rows):
    return rows[:args.limit] if args.limit else rows


chat_train = cut(read_jsonl(HERE / "data" / "train.jsonl"))
chat_val = cut(read_jsonl(HERE / "data" / "val.jsonl"))
qa_path = HERE / "data" / "passage_qa.jsonl"
qa = cut(read_jsonl(qa_path)) if qa_path.exists() else []
qa_val, qa_train = qa[:len(qa) // 20], qa[len(qa) // 20:]
read_train, read_val = corpus_split()
read_train = [{"task": "read", "text": passage_text(r)} for r in cut(read_train)]
read_val = [{"task": "read", "text": passage_text(r)} for r in cut(read_val)]
TRAIN = chat_train + qa_train + read_train * args.read_repeat
VAL = {"understand": [r for r in chat_val if r["task"] == "understand"], "answer": [r for r in chat_val if r["task"] == "answer"],
       "passage": qa_val, "read": read_val}
print("rows per epoch:", {"understand+answer": len(chat_train), "passage": len(qa_train),
                          "read": f"{len(read_train)} x {args.read_repeat}"}, flush=True)
ENC = [encode(r) for r in TRAIN]


def collate(items):
    width = max(len(x) for x, _ in items)
    ids = torch.full((len(items), width), tok.pad_token_id)
    labels = torch.full((len(items), width), -100)
    mask = torch.zeros((len(items), width), dtype=torch.long)
    for row, (x, y) in enumerate(items):
        ids[row, :len(x)] = torch.tensor(x)
        labels[row, :len(y)] = torch.tensor(y)
        mask[row, :len(x)] = 1
    return ids.cuda(), mask.cuda(), labels.cuda()


def plan():
    """Every batch of the whole run, as lists of row numbers. The same seed gives the same plan, so a
    resumed run continues exactly where the saved one stopped."""
    rng, out = random.Random(args.seed), []
    whole, part = int(args.epochs), args.epochs - int(args.epochs)
    for epoch in range(whole + (1 if part else 0)):
        order = list(range(len(ENC)))
        rng.shuffle(order)
        # sort inside large chunks so a batch holds rows of similar length (less padding)
        chunks = [sorted(order[i:i + BATCH * 50], key=lambda k: len(ENC[k][0])) for i in range(0, len(order), BATCH * 50)]
        groups = [c[i:i + BATCH] for c in chunks for i in range(0, len(c), BATCH)]
        rng.shuffle(groups)
        out += groups if epoch < whole else groups[:int(len(groups) * part)]
    return out


def slice_loss(hidden, target):
    return torch.nn.functional.cross_entropy(qwen.lm_head(hidden).float(), target, reduction="sum")


def loss_of(batch):
    """Cross-entropy on the counted tokens. The output layer is 151k words wide, so it is applied only to
    those positions, 512 at a time, and each slice is recomputed in the backward pass instead of being
    kept (checkpoint). Otherwise a batch of literature passages does not fit in memory."""
    ids, mask, labels = batch
    with torch.autocast("cuda", dtype=DTYPE):
        embedded = qwen.model.get_input_embeddings()(ids)
        if model.training:
            embedded.requires_grad_(True)  # checkpointing needs an input that carries gradients
        hidden = qwen.model(inputs_embeds=embedded, attention_mask=mask, use_cache=False).last_hidden_state[:, :-1]
        target = labels[:, 1:]
        keep = target != -100
        hidden, target = hidden[keep], target[keep]
        total = torch.zeros((), device=hidden.device, dtype=torch.float32)
        for i in range(0, len(target), 512):
            h, t = hidden[i:i + 512], target[i:i + 512]
            total = total + (checkpoint(slice_loss, h, t, use_reentrant=False) if model.training else slice_loss(h, t))
    return total / max(1, len(target)), len(target)


@torch.no_grad()
def validate():
    """Mean loss per token for each kind of row; "mean" is the average over the task rows (not "read")."""
    model.eval()
    out = {}
    for name, rows in VAL.items():
        if rows:
            items = sorted((encode(r) for r in rows), key=lambda e: len(e[0]))
            total = tokens = 0
            for i in range(0, len(items), BATCH):
                loss, n = loss_of(collate(items[i:i + BATCH]))
                total, tokens = total + loss.item() * n, tokens + n
            out[name] = total / tokens
    model.train()
    tasks = [v for k, v in out.items() if k != "read"]
    out["mean"] = sum(tasks) / len(tasks)  # the adapter is chosen on the tasks; "read" is reported next to it
    return out


# ---------- optimiser, resume ----------
BATCHES = plan()
total_steps = len(BATCHES) // ACCUM
warmup = max(1, total_steps // 20)
opt = torch.optim.AdamW(TRAINABLE, lr=args.lr, weight_decay=0.0)
sched = torch.optim.lr_scheduler.LambdaLR(
    opt, lambda s: (s + 1) / warmup if s < warmup else max(0.0, 0.5 * (1 + math.cos(math.pi * (s - warmup) / max(1, total_steps - warmup)))))
scaler = torch.amp.GradScaler("cuda", enabled=SCALE)
step, best, log, spent = 0, float("inf"), [], 0.0
if resuming:
    state = torch.load(CKPT / "state.pt", weights_only=False)
    opt.load_state_dict(state["opt"])
    sched.load_state_dict(state["sched"])
    scaler.load_state_dict(state["scaler"])
    step, best, log, spent = state["step"], state["best"], state["log"], state["spent"]
    print(f"resumed at update {step}/{total_steps}", flush=True)
first_step = step
start = time.time()


def minutes():
    return (spent + time.time() - start) / 60


def save_checkpoint():
    tmp = OUT / "checkpoint.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    model.save_pretrained(tmp)
    torch.save({"opt": opt.state_dict(), "sched": sched.state_dict(), "scaler": scaler.state_dict(), "step": step, "best": best,
                "log": log, "spent": minutes() * 60}, tmp / "state.pt")
    shutil.rmtree(CKPT, ignore_errors=True)
    tmp.rename(CKPT)


def evaluate_and_keep():
    global best
    v = validate()
    log.append({"step": step, **{k: round(x, 4) for k, x in v.items()}})
    kept = v["mean"] < best
    if kept:
        best = v["mean"]
        model.save_pretrained(BEST)
    print(f"== update {step}: validation {json.dumps(log[-1])}{'  (best so far, saved)' if kept else ''}", flush=True)


def write_log():
    (OUT / "training_log.json").write_text(json.dumps({
        "base": str(args.base), "gpu": torch.cuda.get_device_name(0), "rows_per_epoch": len(TRAIN), "epochs": args.epochs,
        "updates_done": step, "updates_total": total_steps, "rows_per_update": BATCH * ACCUM, "lr": args.lr, "lora_rank": args.rank,
        "read_repeat": args.read_repeat, "minutes": round(minutes(), 1), "best_validation": best, "validation": log}, indent=1))


# ---------- training ----------
print(f"{len(TRAIN)} rows per epoch, {total_steps} updates in all", flush=True)
if step == 0:
    evaluate_and_keep()
opt.zero_grad(set_to_none=True)
for index in range(step * ACCUM, total_steps * ACCUM):
    loss, _ = loss_of(collate([ENC[k] for k in BATCHES[index]]))
    scaler.scale(loss / ACCUM).backward()
    if (index + 1) % ACCUM:
        continue
    scaler.unscale_(opt)
    torch.nn.utils.clip_grad_norm_(TRAINABLE, 1.0)
    scaler.step(opt)
    scaler.update()
    sched.step()
    opt.zero_grad(set_to_none=True)
    step += 1
    if step % 20 == 0:
        left = (time.time() - start) / (step - first_step) * (total_steps - step) / 60
        print(f"update {step}/{total_steps}  loss {loss.item():.4f}  {minutes():.1f} min so far, about {left:.0f} min left  "
              f"gpu {torch.cuda.max_memory_allocated() / 2**30:.1f} GB", flush=True)
    if step % args.eval_every == 0 or step == total_steps:
        evaluate_and_keep()
    if step % args.save_every == 0 or step == total_steps:
        save_checkpoint()
        write_log()

write_log()
print(f"done. Best adapter: {BEST}  (validation {best:.4f})", flush=True)
