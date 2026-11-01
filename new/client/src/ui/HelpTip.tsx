import React, { useState } from "react";
import { HelpCircle, Info, X } from "lucide-react";
import * as RadixDialog from "@radix-ui/react-dialog";
import { Tooltip } from "./Tooltip";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { cn } from "./cn";
import { t } from "../i18n";

export interface HelpTipProps {
  content: React.ReactNode;
  term?: string;
  icon?: "help" | "info";
  className?: string;
  side?: "top" | "right" | "bottom" | "left";
}

/**
 * HelpTip component:
 * - Tooltip on hover/focus on pointer devices
 * - Bottom sheet / modal dialog on touch devices
 * Fully keyboard accessible (tab focusable, Enter / Space triggers touch dialog).
 */
export const HelpTip: React.FC<HelpTipProps> = ({
  content,
  term,
  icon = "help",
  className,
  side = "top",
}) => {
  const isTouch = useMediaQuery("(pointer: coarse), (max-width: 768px)");
  const [sheetOpen, setSheetOpen] = useState(false);

  const IconComp = icon === "info" ? Info : HelpCircle;
  const label = term ? t("Help on {{term}}", { term }) : t("Help info");

  if (!isTouch) {
    return (
      <Tooltip content={content} side={side}>
        <button
          type="button"
          aria-label={label}
          className={cn(
            "inline-flex cursor-help items-center justify-center p-0.5 text-text-secondary transition-colors hover:text-text focus-visible:outline-2 focus-visible:outline-brand-600 rounded-full",
            className,
          )}
        >
          <IconComp className="size-3.5" aria-hidden="true" />
        </button>
      </Tooltip>
    );
  }

  return (
    <>
      <button
        type="button"
        aria-label={label}
        onClick={() => setSheetOpen(true)}
        className={cn(
          "inline-flex cursor-pointer items-center justify-center p-1 text-text-secondary transition-colors hover:text-text rounded-full focus-visible:outline-2 focus-visible:outline-brand-600",
          className,
        )}
      >
        <IconComp className="size-4" aria-hidden="true" />
      </button>

      <RadixDialog.Root open={sheetOpen} onOpenChange={setSheetOpen}>
        <RadixDialog.Portal>
          <RadixDialog.Overlay className="fixed inset-0 z-(--z-overlay) bg-ink-900/50 backdrop-blur-xs animate-fadeIn" />
          <RadixDialog.Content
            aria-describedby={undefined}
            className="fixed inset-x-0 bottom-0 z-(--z-modal) flex max-h-[85vh] flex-col rounded-t-xl border-t border-border bg-surface p-5 shadow-overlay animate-slideUp md:inset-auto md:left-1/2 md:top-1/2 md:w-full md:max-w-md md:-translate-x-1/2 md:-translate-y-1/2 md:rounded-xl md:border"
          >
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <RadixDialog.Title className="text-base font-semibold text-text flex items-center gap-2">
                <IconComp className="size-4 text-brand-600" aria-hidden="true" />
                {term || t("Information")}
              </RadixDialog.Title>
              <RadixDialog.Close
                aria-label={t("Close")}
                className="inline-flex size-8 items-center justify-center rounded-full bg-ink-100 text-text-secondary hover:bg-ink-200 hover:text-text"
              >
                <X className="size-4" aria-hidden="true" />
              </RadixDialog.Close>
            </div>
            <div className="pt-4 text-sm leading-relaxed text-text overflow-y-auto">
              {content}
            </div>
          </RadixDialog.Content>
        </RadixDialog.Portal>
      </RadixDialog.Root>
    </>
  );
};

export interface GlossaryEntry {
  term: string;
  category: "Frameworks" | "Methodologies" | "Metrics & Units" | "Controls";
  definition: string;
}

export const GLOSSARY_ITEMS: GlossaryEntry[] = [
  {
    term: "BOE",
    category: "Metrics & Units",
    definition: t(
      "Barrel of Oil Equivalent. A unit of energy based on the approximate energy released by burning one barrel of crude oil, standardized in upstream O&G at 6.0 mscf (or 169.904 Sm3) of natural gas per BOE.",
    ),
  },
  {
    term: "HHV",
    category: "Methodologies",
    definition: t(
      "Higher Heating Value (Gross Calorific Value). Total heat released by complete combustion of a fuel including the latent heat of water vaporization, required by the API Compendium for natural gas energy conversion.",
    ),
  },
  {
    term: "GWP (Global Warming Potential)",
    category: "Metrics & Units",
    definition: t(
      "Metric comparing the heat-trapping capacity of greenhouse gases relative to CO2 over a given time horizon (typically 100-year or 20-year). Under IPCC AR5 without feedbacks, CH4=28 and N2O=265.",
    ),
  },
  {
    term: "AR4 / AR5 / AR6",
    category: "Frameworks",
    definition: t(
      "IPCC Assessment Reports providing standardized GWP factors. AR4 (2007: CH4=25), AR5 (2014 default: CH4=28, N2O=265), and AR6 (2021: CH4=29.8, N2O=273).",
    ),
  },
  {
    term: "Flaring Intensity",
    category: "Metrics & Units",
    definition: t(
      "Volume of flared associated or process gas per barrel of oil equivalent produced (m3/BOE). Central metric for World Bank Zero Routine Flaring by 2030 (ZRF) initiative.",
    ),
  },
  {
    term: "Monte Carlo Uncertainty",
    category: "Methodologies",
    definition: t(
      "IPCC Tier 2 numerical simulation technique using Latin Hypercube stochastic sampling (5,000 iterations) to determine exact non-normal probability distributions and 95% confidence intervals (k=2).",
    ),
  },
  {
    term: "Tier 1/2/3",
    category: "Methodologies",
    definition: t(
      "IPCC calculation methodology tiers. Tier 1 uses global average default factors; Tier 2 uses national or basin-specific factors; Tier 3 uses direct equipment-level measurements and rigorous engineering models.",
    ),
  },
  {
    term: "SRSS",
    category: "Methodologies",
    definition: t(
      "Square Root of the Sum of Squares. Standard ISO 14064-1 statistical method used to propagate independent uncertainties when combining emission sources.",
    ),
  },
  {
    term: "k=2 / 95% CI",
    category: "Metrics & Units",
    definition: t(
      "Coverage factor k=2 corresponds to an approximate 95% confidence interval for a normal distribution, the international benchmark for greenhouse gas assertions.",
    ),
  },
  {
    term: "OGMP 2.0 L1-L5",
    category: "Frameworks",
    definition: t(
      "Oil and Gas Methane Partnership reporting framework. Progresses from L1 (venture-level) to L4 (source-level direct measurements) and L5 (site-level measurement reconciliation).",
    ),
  },
  {
    term: "Gold Standard pathway",
    category: "Frameworks",
    definition: t(
      "UNEP/IMEO status awarded to operators with credible, time-bound plans to report majority operated assets at OGMP 2.0 Level 4/5 within 3-5 years.",
    ),
  },
  {
    term: "SEE_dir/SEE_indir",
    category: "Frameworks",
    definition: t(
      "Specific Embedded Emissions under EU CBAM. SEE_dir represents direct emissions from production processes; SEE_indir accounts for consumed electricity and heat.",
    ),
  },
  {
    term: "CCS",
    category: "Methodologies",
    definition: t(
      "Carbon Capture and Storage. The capture of carbon dioxide emissions from industrial processes followed by transport and permanent deep geological sequestration.",
    ),
  },
  {
    term: "LDAR",
    category: "Controls",
    definition: t(
      "Leak Detection and Repair. Work practice standard to inspect components, identify fugitive emissions, and execute timely repairs.",
    ),
  },
  {
    term: "Method 21/OGI",
    category: "Controls",
    definition: t(
      "Regulatory leak screening protocols. EPA Method 21 uses portable sniffers for concentration (ppm); Optical Gas Imaging (OGI) uses infrared cameras to visualize hydrocarbon plumes.",
    ),
  },
  {
    term: "GWP-100/20",
    category: "Metrics & Units",
    definition: t(
      "Global Warming Potential comparing the warming impact of greenhouse gases relative to CO2 over a 100-year vs 20-year horizon. GWP-20 highlights short-lived climate pollutants like methane.",
    ),
  },
  {
    term: "Market vs Location-based",
    category: "Methodologies",
    definition: t(
      "Scope 2 accounting methods. Location-based reflects the average emissions intensity of regional grids; Market-based accounts for contractual clean energy purchases and RECs.",
    ),
  },
  {
    term: "Maker-Checker",
    category: "Controls",
    definition: t(
      "Segregation of duties control where the person who inputs operational data (maker) cannot verify or approve it (checker).",
    ),
  },
];

export const GlossaryHelpTip: React.FC<{
  term: string;
  className?: string;
  side?: "top" | "right" | "bottom" | "left";
}> = ({ term, className, side }) => {
  const item = GLOSSARY_ITEMS.find((g) => g.term.toLowerCase() === term.toLowerCase());
  const content = item ? (
    <div className="flex flex-col gap-1 max-w-xs text-xs p-0.5">
      <span className="font-bold text-text">{item.term}</span>
      <span className="text-text-secondary leading-normal">{item.definition}</span>
    </div>
  ) : (
    term
  );
  return <HelpTip content={content} term={term} className={className} side={side} />;
};
