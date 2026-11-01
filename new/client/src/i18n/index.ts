/**
 * Interface languages (English, French, Arabic).
 *
 * The English text is the translation key: `t("Save changes")` looks the sentence up in fr.json
 * or ar.json and falls back to the English text when no localized entry exists yet.
 *
 * The language is read once, before any module renders, so labels defined at module level are
 * translated too. Changing it saves the choice and reloads the page with correct dir ("ltr" or "rtl").
 */
import i18next from "i18next";
import fr from "./fr.json";
import ar from "./ar.json";

export type Language = "en" | "fr" | "ar";

export const LANGUAGES: { value: Language; label: string; dir: "ltr" | "rtl" }[] = [
  { value: "en", label: "English", dir: "ltr" },
  { value: "fr", label: "Français", dir: "ltr" },
  { value: "ar", label: "العربية", dir: "rtl" },
];

const STORAGE_KEY = "neocarbon.language";

function storedLanguage(): Language {
  try {
    const l = window.localStorage.getItem(STORAGE_KEY);
    return l === "fr" ? "fr" : l === "ar" ? "ar" : "en";
  } catch {
    return "en";
  }
}

void i18next.init({
  lng: typeof window === "undefined" ? "en" : storedLanguage(),
  fallbackLng: "en",
  resources: {
    fr: { translation: fr as Record<string, string> },
    ar: { translation: ar as Record<string, string> },
  },
  initAsync: false,
  // English sentences contain "." and ":": they are whole keys, not paths.
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false },
  returnEmptyString: false,
});

if (typeof document !== "undefined") {
  const current = storedLanguage();
  document.documentElement.lang = current;
  document.documentElement.dir = current === "ar" ? "rtl" : "ltr";
}

/** Translate an English interface string; `vars` fill {{name}} placeholders. */
export function t(text: string, vars?: Record<string, string | number>): string {
  return vars ? i18next.t(text, vars) : i18next.t(text);
}

export function currentLanguage(): Language {
  const lang = i18next.language;
  return lang === "fr" ? "fr" : lang === "ar" ? "ar" : "en";
}

/** Save the choice and reload so every label, including module-level ones, is rebuilt. */
export function setLanguage(language: Language, { reload = true } = {}): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch {
    /* private mode: the choice lasts for this page only */
  }
  if (language === currentLanguage()) return;
  if (reload) {
    window.location.reload();
  } else {
    void i18next.changeLanguage(language);
    document.documentElement.lang = language;
    document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  }
}
