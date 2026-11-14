// The ONLY file that knows whether data comes from mocks or the real backend.
// Set EXPO_PUBLIC_API_URL (see .env.example) to use the backend; empty = mocks.
import { ME } from './mock/data';
import { mockConverse, mockField, mockFields, mockInsights, mockOverview } from './mock/engine';
import type { AssistantMessage, ConverseRequest, FieldCollection, FieldSummary, Insights, Lang, Me, Overview } from './types';

const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? '';
const USER_ID = process.env.EXPO_PUBLIC_USER_ID ?? 'demo-farmer';
export const USE_MOCK = BASE_URL === '';

async function http<T>(path: string, lang: Lang, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-User-Id': USER_ID, 'Accept-Language': lang },
  });
  if (!res.ok) throw new Error(`${res.status} ${path}`);
  return res.json() as Promise<T>;
}
const wait = <T,>(value: T, ms = 400) => new Promise<T>((r) => setTimeout(() => r(value), ms));

export const api = {
  getMe: (lang: Lang): Promise<Me> => (USE_MOCK ? wait(ME, 100) : http('/me', lang)),
  getFields: (lang: Lang): Promise<FieldCollection> => (USE_MOCK ? wait(mockFields(lang)) : http('/fields', lang)),
  getField: (id: string, lang: Lang): Promise<FieldSummary> => (USE_MOCK ? wait(mockField(id, lang), 200) : http(`/fields/${id}`, lang)),
  getOverview: (lang: Lang): Promise<Overview> => (USE_MOCK ? wait(mockOverview(lang), 300) : http('/overview', lang)),
  getInsights: (lang: Lang, fieldId?: string): Promise<Insights> =>
    USE_MOCK ? wait(mockInsights(lang, fieldId), 300) : http(`/insights${fieldId ? `?field=${fieldId}` : ''}`, lang),
  /** One conversation turn: a typed/spoken question, or a tapped reply. */
  converse: (req: ConverseRequest): Promise<AssistantMessage> =>
    USE_MOCK ? wait(mockConverse(req), 900) : http('/converse', req.lang, { method: 'POST', body: JSON.stringify(req) }),
};
