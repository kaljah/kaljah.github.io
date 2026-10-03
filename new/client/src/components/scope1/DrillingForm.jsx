import React, { useEffect } from "react";
import { Input } from "../../ui";
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
    <div className="drilling-form mt-[15px]!">

      <div className="form-grid-2">
        <div className="input-group">
          <label>
            {isTier1 && !isDefaultDays ? "Wells Drilled" : "Drilling Days"}
            <span style={{ color: "#ef4444", marginLeft: "3px" }}>*</span>
          </label>
          <Input
            type="number"
            min="0"
            step="1"
           
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

      </div>



      {isTier2Plus && (
        <>
          <div className="input-group mt-[12px]!">
            <label>Mud Type</label>
            <CustomDropdown
              options={[
                {
                  value: "water_based",
                  label: "Water-based",
                },
                {
                  value: "oil_based",
                  label: "Oil-based / synthetic",
                },
              ]}
              value={data.mud_type || "water_based"}
              onChange={(val) => onChange("mud_type", val)}
            />
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
              Gas composition
            </h5>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "14px",
              }}
            >
              <div className="input-group mb-[0px]!">
                <label style={{ fontSize: "0.8rem" }}>
                  CH₄ fraction
                </label>
                <Input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="1.0"
                 
                  value={
                    data.ch4_fraction !== undefined
                      ? data.ch4_fraction
                      : "0.8385"
                  }
                  onChange={(e) => onChange("ch4_fraction", e.target.value)}
                  placeholder="0.8385"
                />
              </div>

              <div className="input-group mb-[0px]!">
                <label style={{ fontSize: "0.8rem" }}>
                  CO₂ fraction
                </label>
                <Input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="1.0"
                 
                  value={
                    data.co2_fraction !== undefined ? data.co2_fraction : ""
                  }
                  onChange={(e) => onChange("co2_fraction", e.target.value)}
                  placeholder="0.0000"
                />
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DrillingForm;
