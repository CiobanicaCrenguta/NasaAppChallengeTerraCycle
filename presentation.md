# TerraCycle — presentation notes

Status on 14 November 2026. Everything marked **Built** runs today and was checked end to end. Everything marked **Next** is designed but not built; say so on stage. Places marked `[team: …]` need a figure or a name from you.

---

## 1. The pitch in one breath

**TerraCycle is a farm assistant you talk to.** A farmer asks "what should I plant next year?" and gets one direct answer for their own field, built from NASA weather records, satellite images of that field, and published agronomy. Every number comes with its source, and the app says "I don't know" when it has none.

Shorter, for the first slide:

> Ask your land a question. Get an answer you can check.

---

## 2. The problem we solve

What farmers told us in interviews `[team: how many farmers, where]`:

- They want to open the app, ask a question, and get a direct answer.
- They do not want dashboards, maps to interpret, or long text.
- They want it to be about *their* land, not about agriculture in general.

What stands in their way today:

| Problem for the farmer | What TerraCycle does about it |
|---|---|
| **"What do I plant next?" has no simple answer.** Rotation rules are scattered across guides and advisors. | Gives a three-year plan for the field, and shows which crops it left out and which published rule left each one out. |
| **Free satellite and weather data exists, but it is built for specialists.** | Turns it into one sentence, with a chart behind it for anyone who wants to look. |
| **Dry years are more frequent and one bad choice costs a season.** `[team: add a figure and its source]` | Checks every candidate crop against 20 years of rain for that place. |
| **Advice comes without proof.** A farmer cannot tell a sound recommendation from a guess. | Every figure carries its source, and "Why?" opens the reasoning. |
| **Small plots are invisible to most satellite products.** | Reads fields at 10 m. The smallest field in the demo is 2 ha and 71 m wide, and it gets 207 clean measurement squares. |
| **Chat assistants answer confidently and invent numbers.** | The language model is not allowed to supply a number. See section 7. |

---

## 3. What the farmer sees

Three screens and a history of past questions. English only for now.

- **Ask** — the home screen. A headline about the area's weather, the fields that need a look, and a box to type or speak a question.
- **My land** — the fields on a satellite map, each with what the satellite sees on it now.
- **Data** — the charts behind the answers, each labelled "Measured on your field" or "Estimate for your area".

Real exchanges from the running app:

> **"what should I plant on valea mare next year, we are short of water"**
> Plant winter barley on Valea Mare.
> *2027 Winter barley → 2028 Corn → 2029 Rapeseed*
> ✓ Enough rain for it here in 18 of 20 years
> ✓ Not grown on this field in the last 3 years
> ✗ Left out winter wheat: not straight after winter wheat, except in extreme cases [S1]

> **"how is valea mare doing"**
> One part of Valea Mare is often less green than the rest.
> *Sentinel-2 measured it in the week of 12 November, on 1093 squares of 10 m … 23 of 1027 squares were at least 10% less green than the middle of the field in 5 or more of the last 10 growing seasons … A satellite shows how green a field is, not why.*

> **"how hot is too hot for corn at flowering"**
> For corn, days above 35 °C at flowering are a warning. [S10] Above 40 °C, pollination starts to fail. [S12]

> **"is heat dangerous for peas"**
> I have no sourced value for that yet.

> **"what is the price of diesel"**
> That is outside what I can help with. Here is what I can do.

The last two matter as much as the first three. Show one of them in the demo.

---

## 4. Demo script (about two minutes)

1. Open the app. Read the headline aloud. Point at the field flagged on the home screen.
2. Type: **"what should I plant on valea mare next year, we are short of water"**. One sentence, a three-year plan, two reasons, one crop left out with its source.
3. Tap **Why?** Show the list of crops left out, each with a source id, and the rain chart from NASA POWER.
4. Tap **My land**, tap Valea Mare, tap **Ask about it**. Show the greenness chart and read the last line: "A satellite shows how green a field is, not why."
5. Type: **"is heat dangerous for peas"**. Let the audience read "I have no sourced value for that yet." Say: *this is the answer we are proudest of.*
6. Open **Data** and point at the two labels: measured on your field, estimated for your area.

Keep a screen recording as backup. `[team: record it]`

---

## 5. NASA data: what we use and how

Be exact on stage about the three levels below. Judges will ask.

### In the answers today

| NASA source | What it gives | Where the farmer meets it |
|---|---|---|
| **NASA POWER** (daily, 2001–today; from MERRA-2 and GEOS; about 50 km grid) | Rain, maximum and minimum temperature, water in the root zone of the soil | The home headline and the two boxes on it; the three area charts on the Data screen; the weather answer; **the rotation ranking** |

How POWER drives the rotation: for each crop that passes the rotation rules, we count in how many of the 20 reference years (2001–2020) the yearly rain at that place reached the crop's optimal range from FAO ECOCROP. That is the "18 of 20 years" in the answer. "Usual" always means the 2001–2020 average.

### As a second check on the field

| NASA source | What it gives | How we use it |
|---|---|---|
| **HLS — Harmonized Landsat Sentinel-2** (NASA, 30 m, 2013–today) | Greenness of the field itself | NASA's own reading of each field. All four demo fields have enough clean 30 m squares (20, 64, 114 and 118). Its seasonal curve matched Sentinel-2's when we compared them. The answer quotes HLS next to Sentinel-2 when both have an image in the same week. |

### Downloaded for every field, not yet shown in the app

| NASA source | What it gives | Planned use |
|---|---|---|
| **MODIS** (MOD13Q1, 250 m, 2001–2020) | Greenness of the surrounding area for 20 years | The long history for plots too small to read directly |
| **SMAP** (L4, about 9 km, 2015–2020) | Soil moisture in the root zone | A second, satellite-based view next to POWER's model estimate |
| **GPM IMERG** (about 10 km, 2001–2020) | Rain every half hour | Days of heavy rain per season |
| **NASADEM** (30 m) | Height and slope | Steep and low parts of a field. The demo fields are flat (mean slope 1–2°), so nothing is flagged. |

The download and weekly aggregation for all of these is built and ran for all four fields (`backend/field_pull.py`, through Google Earth Engine). The honest line for the stage: *"POWER is in every answer. HLS is our NASA check on the field. Four more NASA sources are already downloaded per field and are next to be shown."*

---

## 6. The Sentinel-2 part

**Why a European satellite in a NASA challenge:** the fields are small. One MODIS square is 6.25 ha, and none fits inside any of our fields. NASA's HLS at 30 m works. Sentinel-2 at 10 m gives about ten times more measurement squares per field, enough to see differences *inside* a field. The challenge invites partner data, and HLS itself is built partly from Sentinel-2.

| Field | Size | Clean 10 m squares (Sentinel-2) | Clean 30 m squares (HLS) |
|---|---|---|---|
| Valea Mare | 11.2 ha | 1093 | 114 |
| Dealul Viei | 6.2 ha | 616 | 64 |
| Lunca Jiului | 2.1 ha, 71 m wide | 207 | 20 |
| Pădurea Veche | 11.2 ha | 1097 | 118 |

A square counts as clean only if it lies fully inside the field outline.

What we take from Sentinel-2 (2017–today, clouds removed):

- **How green the field is now**, in words: bare soil, thin green cover, dense green cover.
- **The season curve**: this year next to the middle of earlier years.
- **Weaker zones inside the field**: each growing season, each 10 m square is compared with the middle of the same field in the same year. A square is reported only if it was at least 10% less green in half of the years or more. Valea Mare has 23 such squares out of 1027; the other three fields have none worth reporting.
- **Winter crop or spring crop**: a field that is green in March–April grew a winter crop; green in June–July, a spring crop. The split is clean in our data. **Next:** use it to propose the crop history to the farmer, who confirms with one tap.

What we never do: name a cause. The app says "less green", never "disease" or "drought damage".

---

## 7. The AI

### What it is

- **Model:** Qwen2.5-1.5B-Instruct, open (Apache 2.0), 1.5 billion parameters. Small on purpose.
- **Where it runs:** on our own machine, next to the server. **No question is sent to a cloud AI service.**
- **Fine-tuned: yes.** We trained a LoRA adapter (37 million parameters, 2.3% of the model) in 14 minutes on one GPU.

### What we trained it to do

| Skill | In | Out |
|---|---|---|
| **Understand** | The farmer's question and their list of fields | A structured request: what they want, which field, which crop, what matters to them |
| **Answer** | The question and a few facts, each with its source | One or two sentences that use only those facts |
| **Read** | Passages of specialist literature | (Domain training: the model learns how agronomy is written) |

Training data: 7,000 questions, 2,946 answers, and about 1,020 literature passages.

### Specialist literature: yes, in two ways

**As reading material for the model** — 1,075 passages, 190,000 words:

- FAO Irrigation and Drainage Paper 56, *Crop evapotranspiration* (crop water needs)
- FAO Irrigation and Drainage Paper 66, *Crop yield response to water* (crop by crop: wheat, maize, soybean, sunflower, barley, sugar beet)
- Field trials from the National Agricultural Research and Development Institute Fundulea, southern Romania (wheat, sunflower, maize)
- Two scientific reviews on heat and crops

**As the facts behind every figure** — a crop table (`backend/crops.json`) where each value records its source, the page or table it was read from, and whether we confirmed it by opening the source. 16 sources, listed in `backend/SOURCES.md`, including the Romanian Ministry of Agriculture's good-practice guide, FAO ECOCROP and FAO AquaCrop. What we could not source is empty and listed in `backend/MISSING.md`. An automatic test fails if anyone adds a number without a source.

### The safety rule

**The model never supplies a number.** It receives the sourced facts and words the answer. The server then checks the sentence: if it contains a number or a source that was not in the facts, or hides that a value is unconfirmed, the sentence is thrown away and the plain facts are shown.

### Measured results

| | Before training | After training |
|---|---|---|
| Questions fully understood (110 hand-written test questions) | 2% | **93%** |
| Intent understood | 52% | **97%** |
| Answers that pass the safety check (147 cases) | 30% | **100%** |
| Fit to held-out specialist literature (perplexity, lower is better) | 16.0 | **13.6** |
| Time per question on a laptop GPU | 1.4 s | **1.0 s** |

Say this with the numbers: the test questions were written by the team in wording the training data does not contain. They were not collected from farmers.

**If the model is off, the app still works.** It falls back to keyword matching and plain fact sentences.

---

## 8. Does it work without internet?

Answer precisely; it is a strong point if stated honestly.

| Part | Without internet |
|---|---|
| The AI | **Works.** It runs locally; nothing goes to the cloud. |
| Satellite readings, soil, rotation, sourced answers | **Work.** All field data is downloaded once and stored. |
| Weather | **Works on the last downloaded copy.** New days arrive when a connection returns. |
| The map background | **Needs internet** (satellite image tiles). The field list under the map still shows. |
| Phone ↔ server | The phone must reach the server, over a local network or the internet. |

One line for the stage: *"The intelligence and the data are local. Only the map picture and tomorrow's weather need a connection."*

**Next:** the model on the phone itself. At 1.5 billion parameters it compresses to about 1 GB, which fits current phones. Not built yet; do not claim it.

---

## 9. What makes it trustworthy

Four rules the app follows everywhere:

1. **Say what was seen, not why.** "Less green", never a diagnosis.
2. **Label every number.** "Measured on your field" or "Estimate for your area", with the grid size.
3. **No source, no number.** The app answers "I have no sourced value for that yet."
4. **Show the reasoning.** "Why?" lists every crop left out and the published rule that left it out. "What can't you see?" lists the app's blind spots: packed soil, pests and disease, blocked drains.

---

## 10. How it looks at scale

The pitch: **a public service, run by an agriculture ministry or paying agency, free for every farmer.**

- **Every data source is global and free:** NASA POWER, HLS, MODIS, SMAP, IMERG, NASADEM, Sentinel-2, SoilGrids, FAO ECOCROP, FAO-56. The demo is in Dolj, Romania; the pipeline takes any field outline anywhere.
- **One download per field, then local.** A field's stored data is about 300 KB. A million fields is about 300 GB: one server disk.
- **Field outlines and crop history already exist** in the land-parcel systems that paying agencies keep for subsidies. Plugged in, the farmer would not need to draw or type anything. `[team: name the agency for your audience, e.g. APIA in Romania]`
- **The crop table is the part that must be local.** Sowing dates and rotation rules differ by region. The format is ready: each region adds its own sourced values, and the test refuses unsourced ones.
- **Plots of any size.** Designed in four tiers: read at 30 m (HLS), read at 10 m (Sentinel-2), too small to read (the app uses the surroundings plus what the farmer reports), or a single point (weather and rotation only). Rotation advice and weather are the same for 5 ares and 50 hectares. **Next:** the tiers are designed, not yet in the code.
- **The AI is cheap to run.** A 1.5-billion-parameter model answers in a second on a laptop graphics card.

---

## 11. Built, and not built

**Built and checked** (25 end-to-end checks pass against the running server and model):

- The phone app: three screens, conversation with tap replies, history, read-aloud.
- The server, with real field outlines and real data for four fields near Craiova.
- The data pipeline for eight sources, run for all four fields.
- Field greenness and weak zones from Sentinel-2, with HLS as the NASA check.
- Rotation from sourced rules plus the 20-year rain record.
- Sourced answers on sowing dates, years between crops, heat at flowering, soil.
- The fine-tuned local model, with fallbacks.

**Not built — say so if asked:**

- Field names, crops and crop history in the demo are **sample values**. Only the outlines and the measurements are real. The sample crops were chosen to agree with what the satellite shows for each year.
- The weak zones are computed and served, but not yet drawn on the map.
- MODIS, SMAP, IMERG and NASADEM are downloaded but not yet shown.
- No yield data, so nothing is validated against harvests.
- No price data. With "income" as priority the app says so and ranks by rotation and rain.
- The rain ranking uses one yearly rain range per species for the whole world (FAO ECOCROP). It does not know when in the year rain falls, so it is hard on winter crops. The app says this in "Why?".
- Thresholds we chose ourselves (bare soil, weak zone, heavy rain, steep slope) have not been reviewed by an agronomist.
- English only. No on-phone model. No installable build for the demo phone yet.

---

## 12. Questions you will get

**"Is this just a chatbot on top of a large model?"**
No. A small open model that we fine-tuned, running on our machine. It reads the question and words the answer. The content comes from data and a sourced table, and a check throws away any sentence with a number that was not given to it.

**"How do you know the recommendation is right?"**
We do not claim it is optimal. We claim it is traceable: each rule has a published source, the rain figures are NASA's, and the app shows both. We have no yield data to validate against, and we say so.

**"Why Sentinel-2 and not only NASA?"**
Field size. See section 6. NASA's HLS reads the same fields and we use it as the check.

**"What happens when the model is wrong?"**
On understanding: it asks ("Which field?", "Which crop?") or the farmer taps instead of typing. On wording: the safety check replaces the sentence with the plain facts. With the model off, the app still answers.

**"Does it work for a farmer with half a hectare?"**
Weather, soil and rotation: yes, today. A direct satellite reading: down to roughly a fifth of a hectare at 10 m, depending on the shape. Below that the design falls back to the surroundings and the farmer's own observation; that part is not built.

**"Where does the crop history come from?"**
In the demo it is sample data. The plan: the satellite proposes winter or spring crop per year, the farmer confirms; in a public deployment it comes from subsidy declarations.

**"Can it give wrong agronomy?"**
It can only repeat what is in the table, and the table can contain a mistake or a value that does not fit a region. That is why each value records where it was read and whether we confirmed it, and why four values are marked "not confirmed" and announced as such in the answer.

---

## 13. Numbers worth quoting

- **20 years** of daily NASA weather behind every rotation answer.
- **10 m** squares; **207 to 1,097** clean squares per field.
- **10 growing seasons** compared to find weak zones.
- **16 sources**, every value traceable to a page or table.
- **93%** of test questions fully understood after fine-tuning, from **2%**.
- **100%** of test answers pass the no-invented-numbers check, from **30%**.
- **14 minutes** to fine-tune; **1 second** per question on a laptop.
- **0** questions sent to a cloud AI.

---

## 14. Slide outline

1. **Title.** Ask your land a question. Get an answer you can check.
2. **The problem.** What farmers told us; the table from section 2, three rows at most.
3. **The answer.** One screenshot of the rotation answer.
4. **Live demo.** Section 4.
5. **NASA data.** The three levels from section 5.
6. **Seeing inside small fields.** Sentinel-2 and HLS; the squares table; the weak-zone picture.
7. **The AI.** Small, local, fine-tuned; the before/after table.
8. **No source, no number.** The crop table, the safety check, the pea answer.
9. **Without internet.** The table from section 8.
10. **At scale.** A public service; global free data; 300 KB per field.
11. **What is next.** The four NASA sources on screen, crop history from the satellite, the model on the phone.
12. **Team and thanks.** `[team: names]`
