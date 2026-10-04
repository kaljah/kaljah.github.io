import React, { useState, useEffect } from "react";
import { ArrowLeft, ArrowRight, Factory, Globe2, Zap } from "lucide-react";
import { Badge, Button, SegmentedControl } from "../ui";
import { useSearchParams } from "react-router-dom";
import { useBreadcrumbExtra } from "../hooks/useBreadcrumbExtra";
import "./Emissions.css";
import "../pages/Dashboard.css";

// Scope Components
import Scope1Form from "../components/Scope1Form";
import Scope2Form from "../components/Scope2Form";
import Scope3Form from "../components/Scope3Form";

import {
  STAGE_SCOPE_SELECTION,
  STAGE_SCOPE1_SUB_SELECTION,
  STAGE_SCOPE2,
  STAGE_SCOPE3,
} from "../utils/constants";

// Landing cards for the three GHG scopes (the stage constants are defined above in this module)
const SCOPE_CARDS = [
  {
    number: "01",
    title: "Scope 1",
    tag: "Direct Emissions",
    desc: "Combustion, flaring, fugitive & vented emissions from sources owned or controlled by your organisation.",
    chips: ["Stationary Combustion", "Flaring", "Fugitive", "+ more"],
    stage: STAGE_SCOPE1_SUB_SELECTION,
    rule: "border-t-brand-500",
    iconBox: "bg-brand-50 text-brand-700",
    tone: "brand",
    Icon: Factory,
  },
  {
    number: "02",
    title: "Scope 2",
    tag: "Indirect Energy",
    desc: "Indirect emissions from the generation of purchased electricity, steam, heat, or cooling consumed by your organisation.",
    chips: ["Electricity", "Steam / Heat", "CHP"],
    stage: STAGE_SCOPE2,
    rule: "border-t-blue-500",
    iconBox: "bg-info-bg text-info-fg",
    tone: "info",
    Icon: Zap,
  },
  {
    number: "03",
    title: "Scope 3",
    tag: "Value Chain",
    desc: "All other indirect emissions in your value chain — upstream inputs, downstream product use, and logistics.",
    chips: ["Upstream", "Downstream", "Logistics", "+ more"],
    stage: STAGE_SCOPE3,
    rule: "border-t-violet-500",
    iconBox: "bg-ink-100 text-violet-700",
    tone: "neutral",
    Icon: Globe2,
  },
];

const Emissions = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [stage, setStage] = useState(STAGE_SCOPE_SELECTION);

  useBreadcrumbExtra(
    stage === STAGE_SCOPE_SELECTION
      ? null
      : stage === STAGE_SCOPE1_SUB_SELECTION
        ? "Scope 1 (Direct)"
        : stage === STAGE_SCOPE2
          ? "Scope 2 (Indirect)"
          : "Scope 3 (Value Chain)",
  );

  useEffect(() => {
    const scopeParam = searchParams.get("scope") || searchParams.get("stage");
    if (scopeParam) {
      const lower = scopeParam.toLowerCase();
      if (lower === "1" || lower === "scope1" || lower === "s1") {
        // the stage follows the URL (?scope=...), an external source
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setStage(STAGE_SCOPE1_SUB_SELECTION);
      } else if (lower === "2" || lower === "scope2" || lower === "s2") {
        setStage(STAGE_SCOPE2);
      } else if (lower === "3" || lower === "scope3" || lower === "s3") {
        setStage(STAGE_SCOPE3);
      } else if (lower === "select" || lower === "all") {
        setStage(STAGE_SCOPE_SELECTION);
      }
    }
  }, [searchParams]);

  const goToStage = (newStage) => {
    setStage(newStage);
    let sVal = "select";
    if (newStage === STAGE_SCOPE1_SUB_SELECTION) sVal = "scope1";
    else if (newStage === STAGE_SCOPE2) sVal = "scope2";
    else if (newStage === STAGE_SCOPE3) sVal = "scope3";
    setSearchParams(sVal === "select" ? {} : { scope: sVal }, { replace: true });
    window.scrollTo(0, 0);
  };

  const renderSelectionScreen = () => (
    <div className="grid gap-5 md:grid-cols-3">
      {SCOPE_CARDS.map((c) => (
        <button
          key={c.title}
          type="button"
          onClick={() => goToStage(c.stage)}
          className={`group flex cursor-pointer flex-col gap-4 rounded-lg border border-t-4 border-border bg-surface p-6 text-left shadow-card transition-shadow hover:shadow-raised ${c.rule}`}
        >
          <span className="flex items-center justify-between">
            <span className={`inline-flex size-12 items-center justify-center rounded-md ${c.iconBox}`}>
              <c.Icon className="size-6" aria-hidden="true" />
            </span>
            <span className="text-sm font-bold tabular-nums text-text-secondary">{c.number}</span>
          </span>
          <span className="flex flex-col gap-1">
            <Badge tone={c.tone} className="self-start">
              {c.tag}
            </Badge>
            <span className="text-xl font-bold text-text">{c.title}</span>
            <span className="text-base text-text-secondary">{c.desc}</span>
          </span>
          <span className="flex flex-wrap gap-1.5">
            {c.chips.map((chip) => (
              <span key={chip} className="rounded-full border border-border bg-ink-50 px-2 py-0.5 text-xs text-text-secondary">
                {chip}
              </span>
            ))}
          </span>
          <span className="mt-auto inline-flex items-center gap-1 text-base font-semibold text-link">
            Open calculator
            <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </span>
        </button>
      ))}
    </div>
  );

  const SCOPE_TABS = [
    { value: STAGE_SCOPE1_SUB_SELECTION, label: "01 Scope 1" },
    { value: STAGE_SCOPE2, label: "02 Scope 2" },
    { value: STAGE_SCOPE3, label: "03 Scope 3" },
  ];
  const content = "w-full px-3 md:px-10";

  return (
    <div>
      {stage !== STAGE_SCOPE_SELECTION && (
        <div className="flex flex-wrap items-center justify-end gap-2 px-3 pt-4 md:px-6">
          <SegmentedControl label="Scope" value={stage} onChange={goToStage} options={SCOPE_TABS} />
          <Button variant="ghost" size="sm" onClick={() => goToStage(STAGE_SCOPE_SELECTION)} title="Back to Scope Selection">
            <ArrowLeft className="size-4" aria-hidden="true" /> All Scopes
          </Button>
        </div>
      )}

      <div>
        {stage === STAGE_SCOPE_SELECTION && (
          <div className={content}>
            <div className="pb-1 pt-5 md:pt-9">
              <h2 className="m-0 mb-2.5 text-xl font-bold text-text">Emission Calculator</h2>
              <p className="m-0 mb-5 text-base leading-relaxed text-text-secondary md:mb-9 md:text-md">
                Select a GHG scope to begin logging and calculating emissions for your facility.
              </p>
            </div>
            {renderSelectionScreen()}
          </div>
        )}

        {stage === STAGE_SCOPE1_SUB_SELECTION && (
          <div className={content}>
            <Scope1Form />
          </div>
        )}

        {stage === STAGE_SCOPE2 && (
          <div className={content}>
            <Scope2Form />
          </div>
        )}

        {stage === STAGE_SCOPE3 && (
          <div className={content}>
            <Scope3Form />
          </div>
        )}
      </div>
    </div>
  );
};

export default Emissions;
