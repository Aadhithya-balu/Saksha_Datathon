import { create } from 'zustand';
import { translations, type Language, type TranslationSet } from './translations';

interface I18nState {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: TranslationSet;
}

const STORAGE_KEY = 'saksha_language';

function getStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'en' || stored === 'kn' || stored === 'kn-en') return stored;
  } catch {}
  return 'en';
}

export const useI18n = create<I18nState>((set) => ({
  language: getStoredLanguage(),
  setLanguage: (lang: Language) => {
    localStorage.setItem(STORAGE_KEY, lang);
    set({ language: lang, t: translations[lang] });
  },
  t: translations[getStoredLanguage()],
}));

export const useTranslation = () => useI18n((s) => s.t);
export const useLanguage = () => useI18n((s) => s.language);
export const useSetLanguage = () => useI18n((s) => s.setLanguage);

export type { Language, TranslationSet };
