import React, { useEffect } from "react";
import { Input } from "../../ui";
import CustomDropdown from "../CustomDropdown";

// Table 6-53 (CO2 and CH4 per tonne produced)
const CHEMICAL_OPTIONS = [
  { value: "Acrylonitrile", label: "Acrylonitrile (1.00 t CO₂/t, 0.18 kg CH₄/t)" },
  { value: "Carbon Black", label: "Carbon Black (2.63 t CO₂/t, 28.7 kg CH₄/t)" },
  { value: "Carbon Black (Thermal Abatement)", label: "Carbon Black, thermal abatement (2.63 t CO₂/t, 0.06 kg CH₄/t)" },
  { value: "Ethylene (Ethane Feedstock)", label: "Ethylene, ethane feedstock (0.77 t CO₂/t, 6 kg CH₄/t)" },
  { value: "Ethylene (Other Feedstocks)", label: "Ethylene, other feedstocks (0.77 t CO₂/t, 3 kg CH₄/t)" },
  { value: "Ethylene Dichloride", label: "Ethylene Dichloride (0.041 t CO₂/t)" },
  { value: "Ethylene Oxide", label: "Ethylene Oxide (0.46 t CO₂/t, 1.79 kg CH₄/t)" },
  { value: "Ethylene Oxide (Thermal Abatement)", label: "Ethylene Oxide, thermal abatement (0.46 t CO₂/t, 0.79 kg CH₄/t)" },
  { value: "Methanol", label: "Methanol (0.67 t CO₂/t, 2.3 kg CH₄/t)" },
];

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
}

export const ChemicalProductionForm: React.FC<Scope1SubFormProps> = ({ data, onChange }) => {
  // the product and unit shown by default must also be in the submitted data (browser test #8:
  // "Please select a unit" while the unit box showed a tonne)
  useEffect(() => {
    if (!data.fuel) onChange("fuel", "Ethylene (Ethane Feedstock)");
    if (!data.unit) onChange("unit", "tonne");
  }, [data.fuel, data.unit, onChange]);

  return (
    <div className="chemical-production-form">
      <div className="form-grid-2">
        <div className="input-group">
          <label>
            Chemical Product
            <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
          </label>
          <CustomDropdown
            options={CHEMICAL_OPTIONS}
            value={data.fuel || "Ethylene (Ethane Feedstock)"}
            onChange={(val) => onChange("fuel", val)}
            placeholder="Select Chemical..."
          />
        </div>

        <div className="input-group">
          <label>
            Production Quantity
            <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
          </label>
          <div className="grid gap-[10px] [grid-template-columns:1fr_120px] max-[600px]:[grid-template-columns:1fr]">
            <Input
              type="number"
              value={data.amount || ""}
              onChange={(e) => onChange("amount", e.target.value)}
              placeholder="0.00"
              required
            />
            <CustomDropdown
              options={[
                { value: "tonne", label: "tonne (metric)" },
                { value: "ton", label: "ton (short)" },
                { value: "kg", label: "kg" },
              ]}
              value={data.unit || "tonne"}
              onChange={(val) => onChange("unit", val)}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChemicalProductionForm;
