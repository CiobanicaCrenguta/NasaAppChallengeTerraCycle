import { useQuery } from '@tanstack/react-query';
import { api } from './api';
import { useLang } from './i18n';

export function useMe() {
  const { lang } = useLang();
  return useQuery({ queryKey: ['me', lang], queryFn: () => api.getMe(lang) });
}
export function useFields() {
  const { lang } = useLang();
  return useQuery({ queryKey: ['fields', lang], queryFn: () => api.getFields(lang) });
}
export function useField(id: string | undefined) {
  const { lang } = useLang();
  return useQuery({ queryKey: ['field', id, lang], queryFn: () => api.getField(id!, lang), enabled: !!id });
}
export function useOverview() {
  const { lang } = useLang();
  return useQuery({ queryKey: ['overview', lang], queryFn: () => api.getOverview(lang) });
}
export function useInsights(fieldId?: string) {
  const { lang } = useLang();
  return useQuery({ queryKey: ['insights', fieldId ?? '', lang], queryFn: () => api.getInsights(lang, fieldId), placeholderData: (prev) => prev });
}
