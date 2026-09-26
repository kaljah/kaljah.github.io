import React, { useEffect } from "react";
import CustomDropdown from "../CustomDropdown";

const DrillingForm = ({ data, onChange, sourceType }) => {
  const currentTier = String(
    data.drilling_tier || data.tier || sourceType || "default"
  ).toLowerCase();
  const isCustom = currentTier === "custom";
  const isTier2Plus =
    currentTier === "tier2_plus" ||
    currentTier === "tier2+" ||
    currentTier === "tier_2_plus";
  const isTier1 = !isCustom && !isTier2Plus;

  const selectedFuel = String(data.fuel || "");
  const isDefaultDays =
    isTier1 &&
    (selectedFuel.includes("Water") ||
      selectedFuel.includes("Oil") ||
      selectedFuel.includes("Mud") ||
      data.unit === "days");

  useEffect(() => {
    if (isTier1) {
      if (isDefaultDays) {
        if (data.unit !== "days") onChange("unit", "days");
      } else {
        if (data.unit !== "well") onChange("unit", "well");
      }
    } else {
      if (data.unit !== "days") onChange("unit", "days");
    }
  }, [isTier1, isDefaultDays]);

  return (
    <div className="drilling-form" style={{ marginTop: "15px" }}>
      <h4
        style={{
          color: "var(--accent-color)",
          marginBottom: "15px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span>Drilling Parameters</span>
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            padding: "3px 8px",
            borderRadius: "4px",
            background: isTier1
              ? "rgba(59, 130, 246, 0.1)"
              : isTier2Plus
              ? "rgba(16, 185, 129, 0.1)"
              : "rgba(245, 158, 11, 0.1)",
            color: isTier1
              ? "#2563eb"
              : isTier2Plus
              ? "#059669"
              : "#d97706",
            border: `1px solid ${
              isTier1
                ? "rgba(59, 130, 246, 0.3)"
                : isTier2Plus
                ? "rgba(16, 185, 129, 0.3)"
                : "rgba(245, 158, 11, 0.3)"
            }`,
          }}
        >
          {isTier1
            ? "Tier 1: API Standard Default"
            : isTier2Plus
            ? "Tier 2+: Onshore EF + Gas Composition"
            : "Tier 2: Saved Custom Factor (Database)"}
        </span>
      </h4>

      <div className="form-grid-2">
        <div className="input-group">
          <label>
            {isTier1 && !isDefaultDays ? "Wells Drilled" : "Drilling Days"}
            <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
          </label>
          <input
            type="number"
            min="0"
            step="1"
            className="mole-input"
            value={data.amount || data.quantity || ""}
            onChange={(e) => {
              onChange("amount", e.target.value);
              onChange("quantity", e.target.value);
            }}
            placeholder={
              isTier1 && !isDefaultDays ? "Number of wells" : "Total drilling days"
            }
          />
        </div>

        <div className="input-group">
          <label>Activity Unit</label>
          <input
            type="text"
            className="mole-input"
            value={isTier1 && !isDefaultDays ? "well" : "days"}
            readOnly
            disabled
            style={{
              background: "#f3f4f6",
              cursor: "not-allowed",
              color: "#374151",
              fontWeight: 600,
            }}
          />
        </div>
      </div>

      {isCustom && (
        <div
          style={{
            marginTop: "12px",
            padding: "12px 14px",
            background: "#fffbeb",
            border: "1px solid #fde68a",
            borderRadius: "6px",
            fontSize: "0.82rem",
            color: "#92400e",
            lineHeight: "1.5",
          }}
        >
          <strong>Tier 2 Custom Factor (Database):</strong>
          <p style={{ margin: "4px 0 0 0" }}>
            Using custom emission factor populated from your database (selected in Calculation Methodology above). Activity represents total drilling days.
          </p>
        </div>
      )}

      {isTier1 && !isDefaultDays && (
        <div
          style={{
            marginTop: "12px",
            padding: "12px 14px",
            background: "#f0f9ff",
            border: "1px solid #bae6fd",
            borderRadius: "6px",
            fontSize: "0.82rem",
            color: "#0369a1",
            lineHeight: "1.5",
          }}
        >
          <strong>API Table 6-3 Simplified Default:</strong>
          <p style={{ margin: "4px 0 0 0" }}>
            Methane emissions are estimated using the standard API factor of{" "}
            <strong>0.0524 t CH₄ per drilled well</strong>.
          </p>
        </div>
      )}

      {isTier2Plus && (
        <>
          <div className="input-group" style={{ marginTop: "12px" }}>
            <label>Mud Type (API Compendium Onshore Defaults)</label>
            <CustomDropdown
              options={[
                {
                  value: "water_based",
                  label: "Water-Based Mud (0.0458 t CH₄/day)",
                },
                {
                  value: "oil_based",
                  label: "Oil-Based / Synthetic Mud (0.0103 t CH₄/day)",
                },
              ]}
              value={data.mud_type || "water_based"}
              onChange={(val) => onChange("mud_type", val)}
            />
            <small
              style={{
                color: "#6b7280",
                marginTop: "4px",
                display: "block",
              }}
            >
              Applies API Compendium onshore mud degassing emission factor adjusted for site gas composition.
            </small>
          </div>

          <div
            style={{
              marginTop: "15px",
              padding: "14px",
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
            }}
          >
            <h5
              style={{
                margin: "0 0 10px 0",
                fontSize: "0.85rem",
                color: "#1e293b",
                fontWeight: 600,
              }}
            >
              Site-Specific Gas Composition Adjustment
            </h5>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "14px",
              }}
            >
              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.8rem" }}>
                  Site CH₄ Mole Fraction (X<sub>CH₄</sub>)
                </label>
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="1.0"
                  className="mole-input"
                  value={
                    data.ch4_fraction !== undefined
                      ? data.ch4_fraction
                      : "0.8385"
                  }
                  onChange={(e) => onChange("ch4_fraction", e.target.value)}
                  placeholder="0.8385"
                />
                <small
                  style={{
                    color: "#64748b",
                    fontSize: "0.72rem",
                  }}
                >
                  Default baseline is 0.8385 (83.85%). Scales Onshore EF by
                  (X<sub>CH₄</sub> / 0.8385).
                </small>
              </div>

              <div className="input-group" style={{ marginBottom: 0 }}>
                <label style={{ fontSize: "0.8rem" }}>
                  Site CO₂ Mole Fraction (X<sub>CO₂</sub>, Optional)
                </label>
                <input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="1.0"
                  className="mole-input"
                  value={
                    data.co2_fraction !== undefined ? data.co2_fraction : ""
                  }
                  onChange={(e) => onChange("co2_fraction", e.target.value)}
                  placeholder="0.0000"
                />
                <small
                  style={{
                    color: "#64748b",
                    fontSize: "0.72rem",
                  }}
                >
                  Optional. Calculates CO₂ mass emissions via stoichiometric
                  molar conversion (44.01/16.04).
                </small>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DrillingForm;
