import { afterEach, describe, expect, it } from "vitest";
import fr from "../i18n/fr.json";
import { currentLanguage, setLanguage, t } from "../i18n";

afterEach(() => setLanguage("en", { reload: false }));

describe("interface languages", () => {
  it("shows the English text by default", () => {
    expect(currentLanguage()).toBe("en");
    expect(t("Save changes")).toBe("Save changes");
  });

  it("translates to French and keeps untranslated strings in English", () => {
    setLanguage("fr", { reload: false });
    expect(t("Save changes")).toBe("Enregistrer les modifications");
    expect(t("Sign out")).toBe("Se déconnecter");
    // technical terms wait for the HSE glossary: they stay in English
    expect(t("Flaring Intensity Trend")).toBe("Flaring Intensity Trend");
    expect(document.documentElement.lang).toBe("fr");
  });

  it("fills placeholders in both languages", () => {
    expect(t("Account menu for {{name}}", { name: "Amina" })).toBe("Account menu for Amina");
    setLanguage("fr", { reload: false });
    expect(t("Account menu for {{name}}", { name: "Amina" })).toBe("Menu du compte de Amina");
  });

  it("remembers the choice in the browser", () => {
    setLanguage("fr", { reload: false });
    expect(window.localStorage.getItem("neocarbon.language")).toBe("fr");
  });

  it("keeps the spacing of fragment strings", () => {
    for (const [en, frText] of Object.entries(fr as Record<string, string>)) {
      // a fragment that follows other text keeps its leading space (French may add one before ":")
      if (en.startsWith(" ")) expect(frText.startsWith(" "), `leading space of ${JSON.stringify(en)}`).toBe(true);
      const placeholders = (s: string) => (s.match(/\{\{\w+\}\}/g) || []).sort().join();
      expect(placeholders(frText), `placeholders of ${JSON.stringify(en)}`).toBe(placeholders(en));
    }
  });
});
