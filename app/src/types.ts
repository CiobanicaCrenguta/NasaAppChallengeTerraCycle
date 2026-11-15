export type Lang = 'en' | 'ro';
export type Health = 'weak_spot' | 'below_usual' | 'good' | 'unknown';
export type Priority = 'water' | 'soil' | 'income';

export type Polygon = { type: 'Polygon'; coordinates: number[][][] };
export type FieldFeature = {
  type: 'Feature';
  properties: {
    id: string; name: string; crop: string; ha: number; health: Health; healthLabel: string;
    /** Centres [lon, lat] of 10 m squares that are often less green than the rest of the field. */
    weakSquares?: [number, number][];
  };
  geometry: Polygon;
};
export type FieldCollection = { type: 'FeatureCollection'; features: FieldFeature[] };
export type FieldSummary = { id: string; history: { year: number; crop: string }[] };
export type Me = { name: string; region: string };

export type Source = { name: string; detail: string };
export type Series = {
  kind: 'line' | 'bar';
  title: string;
  labels: string[];
  values: number[];
  usual?: number[];
  valuesLabel?: string;
  usualLabel?: string;
  highlightIndex?: number;
  source: Source;
};

export type Overview = {
  headline: string;
  attention: { fieldId: string; name: string; label: string }[];
  stats: { id: string; label: string; value: string; note: string; warn: boolean }[];
};
/** One analysis on the Data screen: a plain sentence, then the chart behind it. */
/** Where a number comes from: measured on the field itself, or estimated for the wider area. */
export type Scope = 'field' | 'area';
export type Insight = { id: string; scope: Scope; takeaway: string; series: Series; perField?: boolean };
/** A plain list of what the assistant knows, and how well. */
export type Know = { id: 'field' | 'area' | 'you' | 'blind'; title: string; items: string[]; note?: string };
export type Insights = { area: string; knows: Know[]; cards: Insight[] };

export type Option = { value: string; label: string };
export type Card =
  | { type: 'rotation'; plan: { year: number; crop: string }[]; reasons: string[]; avoid?: string }
  | { type: 'chart'; series: Series }
  | { type: 'limits'; items: string[] };

/** One turn from the assistant. The app shows these strings as received. */
export type AssistantMessage = {
  id: string;
  role: 'assistant';
  text: string; // the one sentence that is also spoken
  detail?: string;
  fieldId?: string;
  fieldName?: string;
  cards?: Card[];
  /** Tap answers: either the assistant needs more information, or offers next steps. */
  replies?: { id: string; prompt?: string; options: Option[] };
  /** Quieter follow-ups, e.g. "How do you know?". Sent as a reply with id "next". */
  links?: Option[];
};
export type UserMessage = { id: string; role: 'user'; text: string };
export type Message = AssistantMessage | UserMessage;

export type ConverseRequest = {
  sessionId: string;
  lang: Lang;
  text?: string;
  fieldId?: string;
  intent?: 'rotation' | 'health';
  reply?: { id: string; value: string };
};

export type Conversation = { id: string; startedAt: number; messages: Message[] };
