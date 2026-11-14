# The local language model

TerraCycle runs a small language model next to the server: no question leaves the machine. The model is Qwen2.5-1.5B-Instruct (Apache 2.0) with a LoRA adapter that we train.

## What the model learns

One training run teaches the model four things.

| Skill | Input | Output | Training rows |
|---|---|---|---|
| **Read** | a passage of specialist literature | the passage itself (loss on every token) | about 1,020 passages, each seen twice per pass |
| **Understand** | a farmer's question and the list of their fields | JSON: `intent`, `field`, `crop`, `after`, `priority` | 7,000 |
| **Answer** | a question and a few facts with their sources | one or two sentences that use only those facts | 2,946 |
| **Passage** (optional) | a question and one literature passage | a short answer with the source id, or a refusal | made on Colab by `make_passage_qa.py` |

"Read" is the domain training: the model reads the literature and gets used to how agronomy is written. The other skills are what the app calls.

## The literature

`build_corpus.py` downloads and cuts into passages (about 1,075 passages, 190,000 words):

- FAO Irrigation and Drainage Paper 56, chapters 1 and 5 to 11 (S13): crop water use, crop coefficients, water stress.
- FAO Irrigation and Drainage Paper 66, *Crop yield response to water* (S16): crop by crop, including wheat, maize, soybean, sunflower, barley and sugar beet.
- Field trials at Fundulea, southern Romania, on wheat, sunflower and maize (S2, S3, S4).
- Two reviews on heat and crops (S10, S11).

Full references are in `backend/SOURCES.md`. Only English sources are in the corpus. The Romanian ones (S1, S5, S6) reach the model as facts from `backend/crops.json`.

## What keeps the answers honest

Reading literature makes a model fluent, and a fluent model also invents figures. So the app never lets the model supply a number:

- Sowing dates, years between crops and heat thresholds come from `backend/crops.json`, where every value points to a source.
- The model gets those facts in the prompt and words the answer.
- The server checks each sentence (`knowledge.safe`). If it states a number or cites a source that is not in the facts, or hides that a value is unconfirmed, the sentence is dropped and the plain facts are shown.
- About 70% of the "answer" rows use made-up facts (random crops, dates, thresholds, source ids), so the model learns to copy the facts in front of it and not the real numbers by heart.

## Train on Colab

1. On the laptop: `python gen_data.py`, `python build_corpus.py`, `python make_colab_bundle.py`. This writes `terracycle_colab.zip` (about 1 MB, no model weights) and `colab.ipynb`.
2. Open `colab.ipynb` in Google Colab, choose a T4 GPU, run the cells from the top. It asks for the zip.
3. Training saves to Google Drive every 100 updates and continues after a disconnect.
4. The last cell downloads `terracycle-lora.zip`. Unpack it into `ai/runs/terracycle-lora`.

## Files

| File | What it is |
|---|---|
| `gen_data.py` | Builds `data/train.jsonl` and `data/val.jsonl` (understand and answer rows) |
| `build_corpus.py` | Builds `data/corpus.jsonl` from the literature |
| `make_passage_qa.py` | Optional: a larger model writes question-and-answer rows from the passages |
| `train.py` | LoRA fine-tuning; adapts to the GPU, saves and resumes |
| `evaluate.py` | Scores a model, writes `runs/eval_<name>.json` |
| `eval_set.py` | 110 questions written by hand, in wording the training templates do not use |
| `make_colab_bundle.py`, `colab.ipynb` | The Colab archive and notebook |
| `serve.py` | Serves the model to the backend on `127.0.0.1:8001` |
| `common.py` | Loading and generation |
| `../backend/llm_prompts.py` | The prompts, shared by training and the server |
| `../backend/knowledge.py` | Fact lookup and the safety check |
| `../backend/llm.py` | The backend's client, with fallbacks |

## How a model is scored

- **Understand:** share of the 110 hand-written questions where every field is right.
- **Answer:** share of answers that pass the safety check, on every question the crop table can or cannot answer plus held-out made-up facts.
- **Read:** perplexity on the 54 literature passages held out of training (lower is better).

The untouched Qwen2.5-1.5B scores 2% (understand, every field right; intent alone 52%), 30% (answer) and a perplexity of 16.0. These are in `runs/eval_base.json` after `python evaluate.py --name base`.

## Training set-up

- Base weights frozen, in half precision (float16 on a T4, bfloat16 on newer cards).
- LoRA rank 32 on the attention and feed-forward projections: 37 million trainable parameters, 2.3% of the model.
- 16 rows per update, learning rate 2e-4 with warm-up and cosine decay, 2 passes over the data.
- Gradient checkpointing, and the output layer applied only to the tokens that count, so one step fits in a few GB.
- The adapter kept is the one with the lowest validation loss on the task rows.

## Run it on the laptop

```
python -m venv .venv --system-site-packages     # reuses an installed PyTorch with CUDA
.venv\Scripts\pip install peft accelerate fastapi uvicorn
.venv\Scripts\python -m uvicorn serve:app --host 127.0.0.1 --port 8001
```

The backend works without the model: with `serve.py` off it matches questions on keywords and shows the plain facts.

## Limits

- The test questions were written by the team, not collected from farmers.
- English only.
- The "understand" skill knows seven crops; any other crop comes back as `null`.
- The corpus is small and is mostly about water, heat and yield. It has little on pests, fertiliser or machinery, and the app refuses those questions.
- The optional "passage" rows are written by a model and checked only by the number rule, not by a person.
- The app does not yet search the literature for a passage to answer from; the "passage" skill is trained but not wired into the server.
- The model runs on a laptop GPU, not on the phone.
