// All interface text lives here. The app is English-only for now; the
// provider is kept so another language can be added without touching screens.
import { createContext, ReactNode, useContext } from 'react';
import type { Lang } from './types';

const en = {
  tabAsk: 'Ask',
  tabLand: 'My land',
  tabData: 'Data',
  dataTitle: 'The data behind the answers',
  dataSub: (area: string) => `NASA data for your land · ${area}`,
  dataLoading: 'Loading the satellite data…',
  dataError: 'I could not load the data.',
  knowTitle: 'What I know about your land',
  scopeField: 'Measured on your field',
  scopeArea: 'Estimate for your area',
  showMore: 'Show the chart',
  showLess: 'Hide',
  knowHint: 'Where it comes from, and what I cannot see',
  askMore: 'Or ask',
  hello: (name: string) => `Hello, ${name}.`,
  prompt: 'What do you want to know about your land?',
  placeholder: 'Type your question',
  micHint: 'Tap the microphone on your keyboard and speak.',
  thinking: 'Looking at your land…',
  errorAnswer: 'I could not answer just now.',
  retry: 'Try again',
  suggestions: ['What should I plant next year?', 'Why did my corn do badly?'],
  history: 'History',
  noHistory: 'Your questions will show up here.',
  newQuestion: 'New question',
  fieldsLoading: 'Loading your fields…',
  fieldsError: 'I could not load your fields. Check your connection.',
  askField: 'Ask about it',
  planField: 'What to plant next',
  askFieldText: (name: string) => `How is ${name} doing?`,
  planFieldText: (name: string) => `What should I plant next on ${name}?`,
  grewHere: 'What grew here',
  talk: 'Talk',
  send: 'Send',
  listen: 'Read aloud',
  back: 'Back',
  speech: 'en-US',
};

const value: { lang: Lang; t: typeof en } = { lang: 'en', t: en };
const Ctx = createContext(value);
export const useLang = () => useContext(Ctx);
export const LangProvider = ({ children }: { children: ReactNode }) => <Ctx.Provider value={value}>{children}</Ctx.Provider>;
