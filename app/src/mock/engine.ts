// Stand-in for the backend conversation endpoint. PLACEHOLDER LOGIC:
// a tiny rule-based rotation pick over sample data, so the interface can be
// built and demoed. The real reasoning (NASA data + agronomy rules) replaces this.
import type { AssistantMessage, ConverseRequest, FieldCollection, FieldSummary, Health, Insights, Lang, Overview, Priority } from '../types';
import { CROPS, Crop, FIELDS, HEALTH_SERIES, JULY_RAIN, ME, MockField, SOIL_WATER, SUMMER_TEMP, YEAR_RAIN, YEARS } from './data';

type Session = { fieldId?: string; priority?: Priority; intent?: 'rotation' | 'health' };
const sessions = new Map<string, Session>();
let counter = 0;
const mid = () => `a${Date.now()}_${counter++}`;
const tr = (L: Lang, en: string, ro: string) => (L === 'ro' ? ro : en);
const norm = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const crop = (id: string) => CROPS.find((c) => c.id === id)!;
const cropName = (id: string, L: Lang) => crop(id)[L];
const SAMPLE = (L: Lang) => tr(L, 'sample data', 'date de test');

const healthLabel = (h: Health, L: Lang) =>
  h === 'good' ? tr(L, 'As green as usual', 'Verde ca de obicei') : h === 'below_usual' ? tr(L, 'Less green than usual', 'Mai puțin verde ca de obicei') : tr(L, 'One part is less green', 'O parte e mai puțin verde');

export function mockFields(L: Lang): FieldCollection {
  return {
    type: 'FeatureCollection',
    features: FIELDS.map((f) => ({
      type: 'Feature',
      properties: { id: f.id, name: f.name, crop: cropName(f.cropId, L), ha: f.ha, health: f.health, healthLabel: healthLabel(f.health, L) },
      geometry: f.geometry,
    })),
  };
}
export function mockField(id: string, L: Lang): FieldSummary {
  const f = FIELDS.find((x) => x.id === id)!;
  return { id, history: f.history.map((h) => ({ year: h.year, crop: cropName(h.cropId, L) })) };
}

const MONTHS = (L: Lang) => (L === 'ro' ? ['Mar', 'Apr', 'Mai', 'Iun', 'Iul', 'Aug', 'Sep'] : ['Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep']);

/* ---------- overview + data screen ---------- */
export function mockOverview(L: Lang): Overview {
  const bad = FIELDS.filter((f) => f.health !== 'good');
  return {
    headline: bad.length
      ? tr(L, `${bad.length} of your ${FIELDS.length} fields need a look.`, `${bad.length} din cele ${FIELDS.length} parcele au nevoie de atenție.`)
      : tr(L, 'All your fields look as green as usual.', 'Toate parcelele tale merg bine.'),
    attention: bad.map((f) => ({ fieldId: f.id, name: f.name, label: healthLabel(f.health, L) })),
    stats: [
      { id: 'rain', label: tr(L, 'Rain in your area, 30 days', 'Ploaie în zonă, 30 de zile'), value: '14 mm', note: tr(L, 'Less than usual', 'Mai puțin ca de obicei'), warn: true },
      { id: 'soil', label: tr(L, 'Water in the soil', 'Apă în sol'), value: tr(L, 'Low', 'Scăzută'), note: tr(L, 'Estimate for your area', 'Estimare pe zonă'), warn: true },
    ],
  };
}

export function mockInsights(L: Lang, fieldId?: string): Insights {
  const f = FIELDS.find((x) => x.id === fieldId) ?? FIELDS[0];
  const yy = YEARS.map((y) => `'${String(y).slice(2)}`);
  const good = f.health === 'good';
  const patch = f.health === 'weak_spot';
  return {
    area: ME.region,
    knows: [
      { id: 'field', title: tr(L, 'Measured on your field', 'Măsurat pe parcela ta'), items: [
        tr(L, 'How green the crop is, in squares 30 m wide, every few days when the sky is clear', 'Cât de verde e cultura, în pătrate de 30 m, la câteva zile, când e senin'),
        tr(L, 'The shape of the land: high and low spots', 'Forma terenului: locuri înalte și joase'),
      ] },
      { id: 'area', title: tr(L, 'Estimated for your area', 'Estimat pe zona ta'), items: [
        tr(L, 'Rain, in squares about 10 km wide', 'Ploaia, în pătrate de circa 10 km'),
        tr(L, 'Water in the soil, about 9 km', 'Apa din sol, circa 9 km'),
        tr(L, 'Temperature, about 50 km', 'Temperatura, circa 50 km'),
      ], note: tr(L, 'Good for trends. Too coarse to tell one field from the next.', 'Bune pentru tendințe. Prea grosiere ca să deosebească o parcelă de alta.') },
      { id: 'you', title: tr(L, 'What you told me', 'Ce mi-ai spus tu'), items: [
        tr(L, 'The crops you grew each year', 'Ce ai cultivat în fiecare an'),
        tr(L, 'Your answers to my questions', 'Răspunsurile tale la întrebările mele'),
      ] },
      { id: 'blind', title: tr(L, 'What I cannot see', 'Ce nu pot vedea'), items: [
        tr(L, 'Pests and disease', 'Dăunători și boli'),
        tr(L, 'Packed soil and blocked drains', 'Sol tasat și drenuri înfundate'),
        tr(L, 'Why a patch is less green, only that it is', 'De ce un petic e mai puțin verde, doar că este'),
      ] },
    ],
    cards: [
      { id: 'rain', scope: 'area', takeaway: tr(L, 'Rain here has been going down.', 'Aici plouă tot mai puțin.'),
        series: { kind: 'bar', title: tr(L, 'Rain per year, mm', 'Ploaie pe an, mm'), labels: yy, values: YEAR_RAIN, highlightIndex: YEAR_RAIN.length - 1,
          source: { name: 'NASA GPM IMERG · ~10 km', detail: SAMPLE(L) } } },
      { id: 'temp', scope: 'area', takeaway: tr(L, 'Summers are getting hotter.', 'Verile sunt tot mai calde.'),
        series: { kind: 'line', title: tr(L, 'Average summer temperature, °C', 'Temperatura medie vara, °C'), labels: yy, values: SUMMER_TEMP, highlightIndex: SUMMER_TEMP.length - 1,
          source: { name: 'NASA POWER · ~50 km', detail: SAMPLE(L) } } },
      { id: 'soil', scope: 'area', takeaway: tr(L, 'The soil in your area is drier than usual this summer.', 'Solul e mai uscat ca de obicei vara asta.'),
        series: { kind: 'line', title: tr(L, 'Water in the top layer of soil', 'Apa din stratul de sus al solului'), labels: MONTHS(L), values: SOIL_WATER.values, usual: SOIL_WATER.usual, highlightIndex: 4,
          valuesLabel: tr(L, 'This year', 'Anul acesta'), usualLabel: tr(L, 'Usual', 'De obicei'), source: { name: 'NASA SMAP · ~9 km', detail: SAMPLE(L) } } },
      { id: 'green', scope: 'field', perField: true,
        takeaway: good
          ? tr(L, `${f.name} is as green as usual.`, `${f.name} e la fel de verde ca de obicei.`)
          : patch
            ? tr(L, `One part of ${f.name} is less green than the rest.`, `O parte din ${f.name} e mai puțin verde decât restul.`)
            : tr(L, `${f.name} is less green than usual since July.`, `${f.name} e mai puțin verde ca de obicei din iulie.`),
        series: { kind: 'line', title: tr(L, 'How green the crop is', 'Cât de verde e cultura'), labels: MONTHS(L),
          values: good ? HEALTH_SERIES.usual.map((v, i) => +(v * (i % 2 ? 1.02 : 0.98)).toFixed(2)) : HEALTH_SERIES.values,
          usual: HEALTH_SERIES.usual, highlightIndex: good ? undefined : 4,
          valuesLabel: patch ? tr(L, 'That part', 'Partea aceea') : tr(L, 'This year', 'Anul acesta'),
          usualLabel: patch ? tr(L, 'Rest of the field', 'Restul parcelei') : tr(L, 'Usual', 'De obicei'),
          source: { name: 'NASA HLS · 30 m', detail: SAMPLE(L) } } },
    ],
  };
}

/* ---------- rotation pick ---------- */
function score(c: Crop, past: string[], p: Priority): number {
  const yearsSince = [...past].reverse().indexOf(c.id); // 0 = last year
  if (yearsSince !== -1 && yearsSince < (c.minGap ?? 2) - 1) return -Infinity;
  const last = crop(past[past.length - 1]);
  let s = p === 'water' ? (4 - c.water) * 2 + (c.early ? 1 : 0) : p === 'soil' ? c.soil * 2 + (c.nfix ? 1 : 0) : c.income * 2;
  if (c.family === last.family) s -= 3;
  if (!past.slice(-2).some((id) => crop(id).family === c.family)) s += 1;
  return s;
}
function plan(f: MockField, p: Priority) {
  const past = f.history.map((h) => h.cropId);
  let year = f.history[f.history.length - 1].year;
  const out: { year: number; cropId: string }[] = [];
  for (let i = 0; i < 3; i++) {
    const best = [...CROPS].sort((a, b) => score(b, past, p) - score(a, past, p))[0];
    past.push(best.id);
    out.push({ year: ++year, cropId: best.id });
  }
  return out;
}

function rotation(s: Session, L: Lang): AssistantMessage {
  const f = FIELDS.find((x) => x.id === s.fieldId)!;
  const p = s.priority!;
  const pl = plan(f, p);
  const pick = crop(pl[0].cropId);
  const last = crop(f.cropId);
  const reasons: string[] = [];
  if (pick.family !== last.family) reasons.push(tr(L, `Breaks the disease cycle after ${last.en.toLowerCase()}`, `Rupe ciclul de boli după ${last.ro.toLowerCase()}`));
  if (p === 'water' && pick.water === 1) reasons.push(tr(L, 'Needs little water', 'Cere puțină apă'));
  if (p === 'water' && pick.early) reasons.push(tr(L, 'Harvested before the July heat', 'Se recoltează înainte de arșița din iulie'));
  if (p === 'soil' && pick.nfix) reasons.push(tr(L, 'Puts nitrogen back into the soil', 'Pune azot înapoi în sol'));
  if (p === 'income') reasons.push(tr(L, 'Usually pays better than the other crops that fit', 'De obicei aduce mai mult decât celelalte culturi potrivite'));
  const gap = last.minGap ?? 2;
  return {
    id: mid(), role: 'assistant', fieldId: f.id, fieldName: f.name,
    text: tr(L, `Plant ${pick.en.toLowerCase()} on ${f.name}.`, `Pune ${pick.ro.toLowerCase()} pe ${f.name}.`),
    cards: [{
      type: 'rotation',
      plan: pl.map((x) => ({ year: x.year, crop: cropName(x.cropId, L) })),
      reasons: reasons.slice(0, 2),
      avoid: tr(L, `Not ${last.en.toLowerCase()} again: leave ${gap} years between`, `Nu din nou ${last.ro.toLowerCase()}: lasă ${gap} ani între culturi`),
    }],
    replies: { id: 'next', options: [
      { value: 'why', label: tr(L, 'Why?', 'De ce?') },
      { value: 'priority', label: tr(L, 'Change priority', 'Altă prioritate') },
    ] },
  };
}

function why(L: Lang): AssistantMessage {
  return {
    id: mid(), role: 'assistant',
    text: tr(L, 'Summers here are getting drier.', 'Verile de aici devin tot mai uscate.'),
    detail: tr(L, 'So I prefer crops that are done before July, or need little water. This is an estimate for your area, not measured on your field.', 'De aceea aleg culturi care se termină înainte de iulie sau cer puțină apă. E o estimare pe zonă, nu o măsurătoare pe parcelă.'),
    cards: [{ type: 'chart', series: {
      kind: 'bar', title: tr(L, 'July rain in your area, mm', 'Ploaia din iulie în zona ta, mm'),
      labels: JULY_RAIN.years.map((y) => `'${String(y).slice(2)}`), values: JULY_RAIN.mm, highlightIndex: JULY_RAIN.mm.length - 1,
      source: { name: 'NASA POWER', detail: SAMPLE(L) },
    } }],
    replies: { id: 'next', options: [{ value: 'limits', label: tr(L, "What can't you see?", 'Ce nu poți vedea?') }] },
  };
}

function limits(L: Lang): AssistantMessage {
  return {
    id: mid(), role: 'assistant',
    text: tr(L, "From space I can't see everything.", 'Din spațiu nu văd tot.'),
    cards: [{ type: 'limits', items: [
      tr(L, 'Packed soil below the surface', 'Sol tasat sub suprafață'),
      tr(L, 'Pests and disease', 'Dăunători și boli'),
      tr(L, 'Blocked drains', 'Drenuri înfundate'),
    ] }],
  };
}

function health(s: Session, L: Lang): AssistantMessage {
  const f = FIELDS.find((x) => x.id === s.fieldId)!;
  const base = { id: mid(), role: 'assistant' as const, fieldId: f.id, fieldName: f.name };
  const plant = { value: 'rotation', label: tr(L, 'What to plant next', 'Ce pun la anul') };
  const links = [{ value: 'how', label: tr(L, 'How do you know?', 'De unde știi?') }];
  if (f.health === 'good') {
    return { ...base, text: tr(L, `${f.name} looks as green as usual.`, `${f.name} e la fel de verde ca de obicei.`),
      detail: tr(L, 'Nothing unusual in the satellite images this season.', 'Nimic neobișnuit în imaginile din satelit sezonul acesta.'),
      replies: { id: 'next', options: [plant] }, links };
  }
  const chart = { type: 'chart' as const, series: {
    kind: 'line' as const, title: tr(L, 'How green the crop is', 'Cât de verde e cultura'), labels: MONTHS(L),
    values: HEALTH_SERIES.values, usual: HEALTH_SERIES.usual, highlightIndex: 4,
    valuesLabel: tr(L, 'This year', 'Anul acesta'), usualLabel: tr(L, 'Usual', 'De obicei'),
    source: { name: 'NASA HLS · 30 m', detail: SAMPLE(L) },
  } };
  if (f.health === 'below_usual') {
    const c = crop(f.cropId);
    return { ...base,
      text: tr(L, `${f.name} is less green than usual for ${c.en.toLowerCase()} in July.`, `${f.name} e mai puțin verde ca de obicei pentru ${c.ro.toLowerCase()} în iulie.`),
      detail: tr(L, 'The whole field dropped at once, in a month with little rain in your area. Most likely the dry weather, but I cannot be sure from space.', 'Toată parcela a scăzut deodată, într-o lună cu puțină ploaie în zonă. Cel mai probabil seceta, dar din spațiu nu pot fi sigur.'),
      cards: [chart], replies: { id: 'next', options: [plant] }, links };
  }
  return { ...base, text: tr(L, `One part of ${f.name} is less green than the rest.`, `O parte din ${f.name} e mai puțin verde decât restul.`),
    detail: tr(L, 'The same patch shows up in satellite images from several seasons, under different crops. That usually points to the ground, not the seed.', 'Același petic apare în imaginile din satelit din mai multe sezoane, sub culturi diferite. De obicei asta arată spre teren, nu spre sămânță.'),
    cards: [{ type: 'chart', series: { ...chart.series, valuesLabel: tr(L, 'That part', 'Partea aceea'), usualLabel: tr(L, 'Rest of the field', 'Restul parcelei') } }],
    replies: { id: 'water', prompt: tr(L, 'After heavy rain, does water stay there?', 'După ploi mari, rămâne apa acolo?'), options: [
      { value: 'yes', label: tr(L, 'Yes', 'Da') }, { value: 'no', label: tr(L, 'No', 'Nu') }, { value: 'unsure', label: tr(L, "I don't know", 'Nu știu') },
    ] },
    links };
}

/** "How do you know?" — what the satellite measures on this field, and what it cannot tell. */
function how(s: Session, L: Lang): AssistantMessage {
  const f = FIELDS.find((x) => x.id === s.fieldId);
  if (!f) return next(s, L);
  const squares = Math.round(f.ha / 0.09 / 10) * 10; // one 30 m square = 0.09 ha
  return { id: mid(), role: 'assistant', fieldId: f.id, fieldName: f.name,
    text: tr(L, 'From satellite images of your field.', 'Din imaginile din satelit ale parcelei tale.'),
    detail: tr(L,
      `Each image is made of squares 30 m wide, and ${f.name} covers about ${squares} of them. Every few days, when the sky is clear, I measure how green each square is. Then I compare it with the rest of the field and with earlier seasons.`,
      `Fiecare imagine e făcută din pătrate de 30 m, iar ${f.name} acoperă cam ${squares}. La câteva zile, când e senin, măsor cât de verde e fiecare pătrat. Apoi îl compar cu restul parcelei și cu sezoanele trecute.`),
    cards: [{ type: 'limits', items: [
      tr(L, 'It shows where the crop is less green, not why', 'Arată unde cultura e mai puțin verde, nu de ce'),
      tr(L, 'It cannot show pests, disease or packed soil', 'Nu poate arăta dăunători, boli sau sol tasat'),
      tr(L, 'It misses anything smaller than about 30 m', 'Nu vede nimic mai mic de circa 30 m'),
    ] }],
    replies: { id: 'next', options: [{ value: 'rotation', label: tr(L, 'What to plant next', 'Ce pun la anul') }] } };
}

function waterReply(s: Session, v: string, L: Lang): AssistantMessage {
  const f = FIELDS.find((x) => x.id === s.fieldId);
  const base = { id: mid(), role: 'assistant' as const, fieldId: f?.id, fieldName: f?.name };
  const plant = { id: 'next', options: [{ value: 'rotation', label: tr(L, 'What to plant next', 'Ce pun la anul') }] };
  if (v === 'yes') return { ...base, text: tr(L, 'Then standing water is the likely cause.', 'Atunci cauza probabilă e apa care băltește.'),
    detail: tr(L, 'Any crop will struggle there until the water has somewhere to go. Check the drainage first.', 'Orice cultură o să sufere acolo până când apa are pe unde să se scurgă. Verifică întâi drenajul.'), replies: plant };
  if (v === 'no') return { ...base, text: tr(L, 'Then packed soil is one possibility.', 'Atunci o posibilitate e solul tasat.'),
    detail: tr(L, 'Dig one spade deep in that spot. If it is dry and hard, the roots cannot get through.', 'Sapă de o cazma în locul acela. Dacă e uscat și tare, rădăcinile nu pot trece.'), replies: plant };
  return { ...base, text: tr(L, 'Look after the next heavy rain and tell me.', 'Uită-te după următoarea ploaie mare și spune-mi.'), replies: plant };
}

function overview(L: Lang): AssistantMessage {
  const bad = FIELDS.filter((f) => f.health !== 'good');
  if (!bad.length) return { id: mid(), role: 'assistant', text: tr(L, 'All your fields look as green as usual.', 'Toate parcelele tale merg bine.') };
  return { id: mid(), role: 'assistant',
    text: tr(L, `${bad.length} of your ${FIELDS.length} fields need a look.`, `${bad.length} din cele ${FIELDS.length} parcele au nevoie de atenție.`),
    replies: { id: 'field', prompt: tr(L, 'Which one first?', 'Cu care începem?'), options: bad.map((f) => ({ value: f.id, label: f.name })) } };
}

function next(s: Session, L: Lang): AssistantMessage {
  if (!s.intent) return { id: mid(), role: 'assistant',
    text: tr(L, 'I can help with two things.', 'Te pot ajuta cu două lucruri.'),
    replies: { id: 'intent', options: [
      { value: 'rotation', label: tr(L, 'What to plant next', 'Ce pun la anul') },
      { value: 'health', label: tr(L, 'How my fields are doing', 'Cum stau parcelele') },
    ] } };
  if (!s.fieldId) {
    if (s.intent === 'health') return overview(L);
    return { id: mid(), role: 'assistant', text: tr(L, 'On which field?', 'Pe care parcelă?'),
      replies: { id: 'field', options: FIELDS.map((f) => ({ value: f.id, label: f.name })) } };
  }
  if (s.intent === 'health') return health(s, L);
  if (!s.priority) return { id: mid(), role: 'assistant', fieldId: s.fieldId, fieldName: FIELDS.find((f) => f.id === s.fieldId)?.name,
    text: tr(L, 'What matters most to you?', 'Ce contează cel mai mult pentru tine?'),
    replies: { id: 'priority', options: [
      { value: 'water', label: tr(L, 'Saving water', 'Să economisesc apă') },
      { value: 'soil', label: tr(L, 'Healthier soil', 'Sol mai sănătos') },
      { value: 'income', label: tr(L, 'Income', 'Venitul') },
    ] } };
  return rotation(s, L);
}

export function mockConverse(req: ConverseRequest): AssistantMessage {
  const s = sessions.get(req.sessionId) ?? {};
  sessions.set(req.sessionId, s);
  const L = req.lang;
  if (req.fieldId) s.fieldId = req.fieldId;
  if (req.intent) s.intent = req.intent;
  if (req.reply) {
    const { id, value } = req.reply;
    if (id === 'field') { s.fieldId = value; s.intent ??= 'health'; }
    else if (id === 'priority') { s.priority = value as Priority; s.intent = 'rotation'; }
    else if (id === 'intent') s.intent = value as Session['intent'];
    else if (id === 'water') return waterReply(s, value, L);
    else if (id === 'next') {
      if (value === 'why') return { ...why(L), fieldId: s.fieldId, fieldName: FIELDS.find((f) => f.id === s.fieldId)?.name };
      if (value === 'limits') return limits(L);
      if (value === 'how') return how(s, L);
      if (value === 'priority') { s.priority = undefined; s.intent = 'rotation'; }
      if (value === 'rotation') s.intent = 'rotation';
    }
  } else if (req.text) {
    const t = norm(req.text);
    const intent = /plant|sow|rotat|next year|grow|pun|seman|la anul|cultiv/.test(t) ? 'rotation'
      : /why|how|bad|weak|health|doing|de ce|cum|slab|prost|rau|sanat|merg|stau/.test(t) ? 'health' : undefined;
    const named = FIELDS.find((f) => t.includes(norm(f.name)));
    const byCrop = intent === 'health' ? FIELDS.find((f) => t.includes(norm(crop(f.cropId).en)) || t.includes(norm(crop(f.cropId).ro))) : undefined;
    if (intent) s.intent = intent;
    if (named || byCrop) s.fieldId = (named ?? byCrop)!.id;
    else if (intent === 'health' && /fields|parcele|toate|all/.test(t)) return overview(L);
  }
  return next(s, L);
}
