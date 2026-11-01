import React, { useState } from "react";
import { Search, BookOpen } from "lucide-react";
import { Dialog, Input, Badge, Button } from "../ui";
import { GLOSSARY_ITEMS, type GlossaryEntry } from "../ui/HelpTip";
import { t } from "../i18n";

export interface GlossaryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const GlossaryModal: React.FC<GlossaryModalProps> = ({ open, onOpenChange }) => {
  const [search, setSearch] = useState("");
  const [selectedCat, setSelectedCat] = useState<string>("All");

  const categories = ["All", "Methodologies", "Frameworks", "Metrics & Units", "Controls"];

  const filtered = GLOSSARY_ITEMS.filter((item: GlossaryEntry) => {
    const matchesCat = selectedCat === "All" || item.category === selectedCat;
    const q = search.toLowerCase().trim();
    const matchesSearch =
      !q ||
      item.term.toLowerCase().includes(q) ||
      item.definition.toLowerCase().includes(q);
    return matchesCat && matchesSearch;
  });

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title={
        <span className="flex items-center gap-2">
          <BookOpen className="size-5 text-brand-600" aria-hidden="true" />
          <span>{t("GHG & MRV Technical Glossary")}</span>
        </span>
      }
      description={t(
        "Standardized technical terminology, methodologies, and framework definitions across NeoCarbon.",
      )}
      footer={<Button onClick={() => onOpenChange(false)}>{t("Close")}</Button>}
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary"
              aria-hidden="true"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("Search terms or definitions...")}
              className="pl-9 h-9"
              aria-label={t("Filter glossary terms")}
            />
          </div>
          <div className="flex flex-wrap gap-1">
            {categories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCat(cat)}
                className={`cursor-pointer rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                  selectedCat === cat
                    ? "bg-brand-500 text-white"
                    : "bg-ink-100 text-text-secondary hover:bg-ink-200 hover:text-text"
                }`}
              >
                {cat === "All" ? t("All") : cat}
              </button>
            ))}
          </div>
        </div>

        <div className="max-h-[55vh] overflow-y-auto space-y-3 pr-1">
          {filtered.length === 0 ? (
            <p className="py-6 text-center text-sm text-text-secondary">
              {t("No glossary terms match your search.")}
            </p>
          ) : (
            filtered.map((item) => (
              <div
                key={item.term}
                className="rounded-lg border border-border bg-ink-50/50 p-3.5 transition-colors hover:bg-ink-50"
              >
                <div className="flex items-center justify-between gap-2 pb-1.5">
                  <h3 className="text-base font-bold text-text">{item.term}</h3>
                  <Badge tone="neutral" className="text-[0.65rem]">
                    {item.category}
                  </Badge>
                </div>
                <p className="text-sm leading-relaxed text-text-secondary m-0">
                  {item.definition}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </Dialog>
  );
};
