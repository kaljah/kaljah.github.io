/**
 * Interface languages (English, French).
 *
 * The English text is the translation key: `t("Save changes")` looks the sentence up in fr.json
 * and falls back to the English text when no French entry exists yet. Strings with technical terms
 * stay in English until the HSE glossary (docs/sonatrach/glossary-fr.csv) validates them.
 *
 * The language is read once, before any module renders, so labels defined at module level are
 * translated too. Changing it saves the choice and reloads the page.
 */
import i18next from "i18next";
import fr from "./fr.json";

export type Language = "en" | "fr";

export const LANGUAGES: { value: Language; label: string }[] = [
  { value: "en", label: "English" },
  { value: "fr", label: "Français" },
];

const STORAGE_KEY = "neocarbon.language";

function storedLanguage(): Language {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "fr" ? "fr" : "en";
  } catch {
    return "en";
  }
}

void i18next.init({
  lng: typeof window === "undefined" ? "en" : storedLanguage(),
  fallbackLng: "en",
  resources: { fr: { translation: fr as Record<string, string> } },
  initAsync: false,
  // English sentences contain "." and ":": they are whole keys, not paths.
  keySeparator: false,
  nsSeparator: false,
  interpolation: { escapeValue: false },
  returnEmptyString: false,
});

if (typeof document !== "undefined") {
  document.documentElement.lang = i18next.language;
}

/** Translate an English interface string; `vars` fill {{name}} placeholders. */
export function t(text: string, vars?: Record<string, string | number>): string {
  return vars ? i18next.t(text, vars) : i18next.t(text);
}

export function currentLanguage(): Language {
  return i18next.language === "fr" ? "fr" : "en";
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
  }
}
