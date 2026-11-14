import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Speech from 'expo-speech';
import { api } from './api';
import { useLang } from './i18n';
import type { AssistantMessage, Conversation, ConverseRequest, Message, Option } from './types';

const KEY = 'tc.conversations.v3';
const newId = () => `c${Date.now()}_${Math.round(Math.random() * 1e6)}`;
const fresh = (): Conversation => ({ id: newId(), startedAt: Date.now(), messages: [] });

type Extra = Pick<ConverseRequest, 'fieldId' | 'intent'>;
type Ctx = {
  current: Conversation;
  history: Conversation[]; // past conversations, newest first
  pending: boolean;
  failed: boolean;
  send: (text: string, extra?: Extra) => void;
  reply: (replyId: string, option: Option, fieldId?: string) => void;
  retry: () => void;
  startNew: () => void;
  /** Start a fresh conversation with this question. */
  ask: (text: string, extra?: Extra) => void;
  open: (id: string) => void;
  speak: (m: AssistantMessage) => void;
};
const C = createContext<Ctx | null>(null);
export const useConversation = () => useContext(C)!;

export function ConversationProvider({ children }: { children: ReactNode }) {
  const { lang, t } = useLang();
  const [all, setAll] = useState<Conversation[]>([]);
  const [current, setCurrent] = useState<Conversation>(fresh);
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const lastReq = useRef<ConverseRequest | null>(null);
  const loaded = useRef(false);

  useEffect(() => {
    AsyncStorage.getItem(KEY)
      .then((v) => { if (v) setAll(JSON.parse(v)); })
      .catch(() => {})
      .finally(() => { loaded.current = true; });
  }, []);

  // keep the stored list in sync with the current conversation
  useEffect(() => {
    if (!loaded.current || current.messages.length === 0) return;
    setAll((prev) => {
      const next = [current, ...prev.filter((c) => c.id !== current.id)].slice(0, 30);
      AsyncStorage.setItem(KEY, JSON.stringify(next)).catch(() => {});
      return next;
    });
  }, [current]);

  const speak = useCallback((m: AssistantMessage) => {
    Speech.stop();
    Speech.speak([m.text, m.replies?.prompt].filter(Boolean).join(' '), { language: t.speech });
  }, [t.speech]);

  const run = useCallback(async (req: ConverseRequest) => {
    lastReq.current = req;
    setPending(true);
    setFailed(false);
    try {
      const answer = await api.converse(req);
      setCurrent((c) => (c.id === req.sessionId ? { ...c, messages: [...c.messages, answer] } : c));
      speak(answer);
    } catch {
      setFailed(true);
    } finally {
      setPending(false);
    }
  }, [speak]);

  const push = (m: Message) => setCurrent((c) => ({ ...c, messages: [...c.messages, m] }));

  const value = useMemo<Ctx>(() => ({
    current,
    history: all.filter((c) => c.id !== current.id),
    pending,
    failed,
    send: (text, extra) => {
      if (pending) return;
      push({ id: newId(), role: 'user', text });
      run({ sessionId: current.id, lang, text, ...extra });
    },
    reply: (replyId, option, fieldId) => {
      if (pending) return;
      push({ id: newId(), role: 'user', text: option.label });
      run({ sessionId: current.id, lang, fieldId, reply: { id: replyId, value: option.value } });
    },
    retry: () => { if (lastReq.current) run(lastReq.current); },
    startNew: () => { Speech.stop(); setFailed(false); setCurrent(fresh()); },
    ask: (text, extra) => {
      if (pending) return;
      const c = fresh();
      c.messages.push({ id: newId(), role: 'user', text });
      setCurrent(c);
      run({ sessionId: c.id, lang, text, ...extra });
    },
    open: (id) => { const c = all.find((x) => x.id === id); if (c) { Speech.stop(); setFailed(false); setCurrent(c); } },
    speak,
  }), [current, all, pending, failed, lang, run, speak]);

  return <C.Provider value={value}>{children}</C.Provider>;
}
