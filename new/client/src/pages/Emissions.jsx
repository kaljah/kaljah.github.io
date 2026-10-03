import React, { useState, useEffect } from "react";
import { ArrowRight, Factory, Globe2, Zap } from "lucide-react";
import { Badge } from "../ui";
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

  return (
    <div className="emissions-page">
        {stage !== STAGE_SCOPE_SELECTION && (
          <div className="[display:flex] [justify-content:flex-end] [padding:16px_24px_0]">
          <div className="scope-switcher-tabs">
            <button
              className={`scope-tab-btn ${stage === STAGE_SCOPE1_SUB_SELECTION ? "active s1" : ""}`}
              onClick={() => goToStage(STAGE_SCOPE1_SUB_SELECTION)}
            >
              <span className="tab-pill">01</span> Scope 1
            </button>
            <button
              className={`scope-tab-btn ${stage === STAGE_SCOPE2 ? "active s2" : ""}`}
              onClick={() => goToStage(STAGE_SCOPE2)}
            >
              <span className="tab-pill">02</span> Scope 2
            </button>
            <button
              className={`scope-tab-btn ${stage === STAGE_SCOPE3 ? "active s3" : ""}`}
              onClick={() => goToStage(STAGE_SCOPE3)}
            >
              <span className="tab-pill">03</span> Scope 3
            </button>
            <button
              className="scope-tab-btn back-btn"
              onClick={() => goToStage(STAGE_SCOPE_SELECTION)}
              title="Back to Scope Selection"
            >
              ← All Scopes
            </button>
          </div>
          </div>
        )}

      <div className="content-wrapper">
        {stage === STAGE_SCOPE_SELECTION && (
          <div className="calculator-container">
            <div className="[padding:36px_0_4px]! [@media(max-width:768px)]:[padding:20px_0_10px]!">
              <h2 className="[font-size:var(--text-xl)]! [font-weight:700]! [color:var(--text-primary)] [margin:0_0_10px] [letter-spacing:-0.4px] [@media(max-width:768px)]:[font-size:var(--text-xl)]!">Emission Calculator</h2>
              <p className="[font-size:var(--text-md)]! [color:var(--text-secondary)] [margin:0_0_36px]! [line-height:1.65] [@media(max-width:768px)]:[margin-bottom:20px]! [@media(max-width:768px)]:[font-size:var(--text-base)]!">
                Select a GHG scope to begin logging and calculating emissions
                for your facility.
              </p>
            </div>
            {renderSelectionScreen()}
          </div>
        )}

        {stage === STAGE_SCOPE1_SUB_SELECTION && (
          <div className="calculator-container">
            <Scope1Form />
          </div>
        )}

        {stage === STAGE_SCOPE2 && (
          <div className="calculator-container">
            <Scope2Form />
          </div>
        )}

        {stage === STAGE_SCOPE3 && (
          <div className="calculator-container">
            <Scope3Form />
          </div>
        )}
      </div>
    </div>
  );
};

export default Emissions;
