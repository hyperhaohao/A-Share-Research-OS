import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import i18n from "../i18n";
import {
  applyDocumentLanguage,
  browserLanguage,
  readStoredPreference,
  resolveLanguage,
  storePreference,
} from "../i18n";
import type { Language, LanguagePreference } from "../i18n";

interface LanguageContextValue {
  preference: LanguagePreference;
  language: Language;
  setPreference: (preference: LanguagePreference) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<LanguagePreference>(() =>
    readStoredPreference(),
  );
  // Re-evaluated on render; browserLanguage() reads navigator live so a
  // preference change or OS language change recomputes through the same path.
  const language: Language = resolveLanguage(preference, browserLanguage());

  useEffect(() => {
    void i18n.changeLanguage(language);
    applyDocumentLanguage(language);
  }, [language]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      preference,
      language,
      setPreference: (next) => {
        setPreferenceState(next);
        storePreference(next);
      },
    }),
    [preference, language],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
