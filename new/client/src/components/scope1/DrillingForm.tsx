import React, { useEffect } from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  sourceType?: string;
}

export const DrillingForm: React.FC<Scope1SubFormProps> = ({ data, onChange, sourceType }) => {
  const currentTier = String(
    data.drilling_tier || data.tier || sourceType || "default",
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
  }, [isTier1, isDefaultDays, data.unit, onChange]);

  return (
    <div className="drilling-form mt-[15px]!">
      <div className="form-grid-2">
        <Field
          className="input-group"
          label={
            <>
              {isTier1 && !isDefaultDays ? "Wells Drilled" : "Drilling Days"}
              <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
            </>
          }
        >
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
        </Field>
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

          <div className="mt-[15px]! p-[14px]! bg-[color:var(--color-ink-50)]! [border:1px_solid_var(--color-ink-200)]! rounded-[6px]!">
            <h5 className="m-[0_0_10px_0]! text-[length:0.85rem]! text-[color:var(--color-ink-800)]! font-semibold!">
              Gas composition
            </h5>
            <div className="grid gap-[14px] [grid-template-columns:1fr_1fr] max-[600px]:[grid-template-columns:1fr]">
              <div className="input-group mb-[0px]!">
                <label className="text-[length:0.8rem]!">CH₄ fraction</label>
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
                <label className="text-[length:0.8rem]!">CO₂ fraction</label>
                <Input
                  type="number"
                  step="0.0001"
                  min="0"
                  max="1.0"
                  value={data.co2_fraction !== undefined ? data.co2_fraction : ""}
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
