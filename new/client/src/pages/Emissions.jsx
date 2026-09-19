import React, { useState, useEffect } from "react";
import api from "../api";
import { useToast } from "../components/Toast";
import { useAuth } from "../context/AuthContext";
import { useNavigate, useSearchParams } from "react-router-dom";
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

const Emissions = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [stage, setStage] = useState(STAGE_SCOPE_SELECTION);

  useEffect(() => {
    const scopeParam = searchParams.get("scope") || searchParams.get("stage");
    if (scopeParam) {
      const lower = scopeParam.toLowerCase();
      if (lower === "1" || lower === "scope1" || lower === "s1") {
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
    <div className="scope-selection-grid">
      {/* ── SCOPE 1 ── */}
      <div
        className="scope-card scope-1-card"
        onClick={() => goToStage(STAGE_SCOPE1_SUB_SELECTION)}
      >
        <div className="scope-card-left">
          <div className="scope-number-badge s1-badge">01</div>
          <div className="scope-icon-ring s1-ring">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </div>
        </div>
        <div className="scope-card-body">
          <div className="scope-card-header">
            <span className="scope-tag s1-tag">Direct Emissions</span>
            <h3 className="scope-card-title">Scope 1</h3>
            <p className="scope-card-desc">
              Combustion, flaring, fugitive &amp; vented emissions from sources
              owned or controlled by your organisation.
            </p>
          </div>
          <div className="scope-meta-row">
            <span className="scope-meta-chip">Stationary Combustion</span>
            <span className="scope-meta-chip">Flaring</span>
            <span className="scope-meta-chip">Fugitive</span>
            <span className="scope-meta-chip">+&nbsp;more</span>
          </div>
        </div>
        <div className="scope-card-arrow s1-arrow">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </div>
      </div>

      {/* ── SCOPE 2 ── */}
      <div
        className="scope-card scope-2-card"
        onClick={() => goToStage(STAGE_SCOPE2)}
      >
        <div className="scope-card-left">
          <div className="scope-number-badge s2-badge">02</div>
          <div className="scope-icon-ring s2-ring">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="2" y="7" width="20" height="14" rx="2" />
              <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
              <line x1="12" y1="12" x2="12" y2="16" />
            </svg>
          </div>
        </div>
        <div className="scope-card-body">
          <div className="scope-card-header">
            <span className="scope-tag s2-tag">Indirect Energy</span>
            <h3 className="scope-card-title">Scope 2</h3>
            <p className="scope-card-desc">
              Indirect emissions from the generation of purchased electricity,
              steam, heat, or cooling consumed by your organisation.
            </p>
          </div>
          <div className="scope-meta-row">
            <span className="scope-meta-chip">Electricity</span>
            <span className="scope-meta-chip">Steam / Heat</span>
            <span className="scope-meta-chip">CHP</span>
          </div>
        </div>
        <div className="scope-card-arrow s2-arrow">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </div>
      </div>

      {/* ── SCOPE 3 ── */}
      <div
        className="scope-card scope-3-card"
        onClick={() => goToStage(STAGE_SCOPE3)}
      >
        <div className="scope-card-left">
          <div className="scope-number-badge s3-badge">03</div>
          <div className="scope-icon-ring s3-ring">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </div>
        </div>
        <div className="scope-card-body">
          <div className="scope-card-header">
            <span className="scope-tag s3-tag">Value Chain</span>
            <h3 className="scope-card-title">Scope 3</h3>
            <p className="scope-card-desc">
              All other indirect emissions in your value chain — upstream
              inputs, downstream product use, and logistics.
            </p>
          </div>
          <div className="scope-meta-row">
            <span className="scope-meta-chip">Upstream</span>
            <span className="scope-meta-chip">Downstream</span>
            <span className="scope-meta-chip">Logistics</span>
            <span className="scope-meta-chip">+&nbsp;more</span>
          </div>
        </div>
        <div className="scope-card-arrow s3-arrow">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </div>
      </div>
    </div>
  );

  return (
    <div className="emissions-page">
      <header className="top-bar">
        <div className="breadcrumbs">
          <span
            style={{ cursor: "pointer" }}
            onClick={() => navigate("/")}
          >
            Dashboard
          </span>
          <span style={{ color: "var(--text-secondary)", margin: "0 8px" }}>
            /
          </span>
          <span
            style={{ cursor: "pointer" }}
            onClick={() => goToStage(STAGE_SCOPE_SELECTION)}
          >
            Calculations
          </span>
          <span style={{ color: "var(--text-secondary)", margin: "0 8px" }}>
            /
          </span>
          <span>
            {stage === STAGE_SCOPE_SELECTION
              ? "Select Scope"
              : stage === STAGE_SCOPE1_SUB_SELECTION
                ? "Scope 1 (Direct)"
                : stage === STAGE_SCOPE2
                  ? "Scope 2 (Indirect)"
                  : "Scope 3 (Value Chain)"}
          </span>
        </div>

        {stage !== STAGE_SCOPE_SELECTION && (
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
        )}
      </header>

      <div className="content-wrapper">
        {stage === STAGE_SCOPE_SELECTION && (
          <div className="calculator-container">
            <div className="scope-selector-header">
              <h2 className="scope-selector-title">Emission Calculator</h2>
              <p className="scope-selector-subtitle">
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
