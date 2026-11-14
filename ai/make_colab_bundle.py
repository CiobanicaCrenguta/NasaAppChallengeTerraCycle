"""Packs everything Colab needs into terracycle_colab.zip, and writes the notebook colab.ipynb.

    python gen_data.py && python build_corpus.py && python make_colab_bundle.py

The archive unpacks to terracycle/ai and terracycle/backend, the same layout as the project, so the
scripts run unchanged. It holds no model weights (Colab downloads Qwen itself). It does hold the
literature passages, which are other people's text, so the archive is kept out of git.
"""
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
AI = ["common.py", "train.py", "evaluate.py", "eval_set.py", "gen_data.py", "make_passage_qa.py", "build_corpus.py", "serve.py",
      "README.md", "colab.ipynb", "data/train.jsonl", "data/val.jsonl", "data/corpus.jsonl"]
BACKEND = ["knowledge.py", "llm_prompts.py", "crops.json", "SOURCES.md"]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


NOTEBOOK = [
    md("""
# TerraCycle: fine-tune the local model

Trains a LoRA adapter for Qwen2.5-1.5B-Instruct on three things at once: reading the specialist literature, understanding a farmer's question, and answering from sourced facts.

**Before you start:** Runtime > Change runtime type > **T4 GPU**. Then run the cells from top to bottom.

Progress is saved to your Google Drive every 100 updates. If Colab disconnects, run cells 1 to 3 again and then the training cell: it continues where it stopped.
"""),
    md("## 1. Drive and GPU"),
    code("""
from google.colab import drive
drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/terracycle'
!mkdir -p "$OUT"
!nvidia-smi --query-gpu=name,memory.total --format=csv
"""),
    md("## 2. Upload `terracycle_colab.zip`\n\nSkipped if the folder is already there (after a reconnect in the same session)."),
    code("""
import os
if not os.path.exists('/content/terracycle/ai/train.py'):
    from google.colab import files
    files.upload()   # choose terracycle_colab.zip
    !unzip -q -o terracycle_colab.zip -d /content
%cd /content/terracycle/ai
!ls
"""),
    md("## 3. Libraries"),
    code("""
!pip uninstall -y -q torchao   # an old torchao on Colab breaks peft; we do not use it
!pip install -q -U "transformers>=4.46" peft accelerate
"""),
    md("## 4. Score the untouched model\n\nGives the numbers to compare against. About 5 minutes; downloads Qwen (3 GB) the first time."),
    code("""
!python evaluate.py --name base
!cp runs/eval_base.json "$OUT/"
"""),
    md("""
## 5. Optional: questions and answers written from the literature

A larger model (Qwen2.5-7B, 4-bit) writes one question and answer per passage; rows that state a number missing from the passage are dropped. Adds a fourth skill: answering from a passage with its source.

This step has only been checked on a handful of passages with a small teacher. It can take an hour or more on a T4. Skip it if time is short: training works without it.
"""),
    code("""
RUN_PASSAGE_QA = False   # set to True to run this step
if RUN_PASSAGE_QA:
    !pip install -q -U bitsandbytes
    !python make_passage_qa.py
    !cp data/passage_qa.jsonl "$OUT/"
"""),
    md("""
## 6. Train

Two passes over the data. The line printed every 20 updates shows the time left. The best adapter so far is always in `MyDrive/terracycle/terracycle-lora`.

After a disconnect: run cells 1 to 3, then this cell again.
"""),
    code("""
!python train.py --out "$OUT" --epochs 2 --resume
"""),
    md("## 7. Score the trained model"),
    code("""
!python evaluate.py --name tuned --adapter "$OUT/terracycle-lora"
!cp runs/eval_tuned.json "$OUT/"
"""),
    code("""
import json
base, tuned = (json.load(open(f'runs/eval_{n}.json')) for n in ('base', 'tuned'))
rows = [('Questions understood, every field right', 'understand', 'everything_right', True),
        ('Intent right', 'understand', 'intent_right', True),
        ('Answers that pass the safety check', 'answer', 'safe', True),
        ('Perplexity on held-out literature (lower is better)', 'read', 'perplexity', False),
        ('Seconds per question, median', 'understand', 'seconds_median', False)]
print(f"{'':52} {'before':>8} {'after':>8}")
for label, part, key, pct in rows:
    a, b = base[part][key], tuned[part][key]
    print(f"{label:52} {a:8.1%} {b:8.1%}" if pct else f"{label:52} {a:8.2f} {b:8.2f}")
print()
print('Still wrong after training:')
for w in tuned['understand']['wrong']:
    print(' ', w['question'], '| expected', w['expected'], '| got', w['got'])
"""),
    md("""
## 8. Take the adapter home

Downloads `terracycle-lora.zip` (about 150 MB). On the laptop, unpack it into `TerraCycle/ai/runs/terracycle-lora`; `serve.py` loads it from there. `eval_base.json`, `eval_tuned.json` and `training_log.json` are in `MyDrive/terracycle`.
"""),
    code("""
!cd "$OUT" && zip -q -r /content/terracycle-lora.zip terracycle-lora training_log.json eval_base.json eval_tuned.json
from google.colab import files
files.download('/content/terracycle-lora.zip')
"""),
]


def main():
    notebook = {"cells": NOTEBOOK, "nbformat": 4, "nbformat_minor": 5,
                "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
                             "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}}}
    (HERE / "colab.ipynb").write_text(json.dumps(notebook, indent=1), encoding="utf-8")
    target = HERE / "terracycle_colab.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in AI:
            z.write(HERE / name, f"terracycle/ai/{name}")
        for name in BACKEND:
            z.write(ROOT / "backend" / name, f"terracycle/backend/{name}")
        for profile in sorted((ROOT / "backend" / "data" / "baked").glob("*/profile.json")):
            z.write(profile, f"terracycle/backend/data/baked/{profile.parent.name}/profile.json")
        names = z.namelist()
    print(f"{target.name}: {len(names)} files, {target.stat().st_size / 2**20:.1f} MB")


if __name__ == "__main__":
    main()
