import React from "react";
import { Input, Field } from "../../ui";
import CustomDropdown from "../CustomDropdown";
import { t } from "../../i18n";

export interface Scope1SubFormProps {
  data: Record<string, any>;
  onChange: (field: string, val: any) => void;
  sourceType?: string;
}

export const AGRForm: React.FC<Scope1SubFormProps> = ({ data, onChange, sourceType }) => {
  return (
    <div className="agr-form">
      <div className="input-group">
        <label>
          {t("Inlet (sour) gas throughput")}
          <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
        </label>
        <div className="grid gap-[10px] [grid-template-columns:1fr_130px] max-[600px]:[grid-template-columns:1fr]">
          <Input
            type="number"
            value={data.agr_throughput || ""}
            onChange={(e) => onChange("agr_throughput", e.target.value)}
            placeholder={t("Volume")}
            required
          />
          <CustomDropdown
            options={[
              { value: "MMscf/yr", label: "MMscf/yr" },
              { value: "MMscf/day", label: t("MMscfd") },
              { value: "Mcf/day", label: "Mcf/day" },
              { value: "m3/yr", label: "m³/yr" },
            ]}
            value={data.agr_unit || "MMscf/yr"}
            onChange={(val) => onChange("agr_unit", val)}
          />
        </div>
      </div>

      {sourceType === "specific" && (
        <>
          <div className="input-group">
            <label>{t("Solvent")}</label>
            <CustomDropdown
              options={[
                { value: "MEA", label: t("Monoethanolamine (MEA)") },
                { value: "DEA", label: t("Diethanolamine (DEA)") },
                { value: "MDEA", label: t("Methyldiethanolamine (MDEA)") },
                { value: "DGA", label: t("Diglycolamine (DGA)") },
                { value: "Sulfinol", label: t("Sulfinol") },
              ]}
              value={data.solvent_type || "MDEA"}
              onChange={(val) => onChange("solvent_type", val)}
            />
          </div>

          <Field
            className="input-group"
            label={
              <>
                {t("Inlet CO2 (%)")}
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </>
            }
          >
            <Input
              type="number"
              value={data.agr_co2_in !== undefined && data.agr_co2_in !== null ? data.agr_co2_in : ""}
              onChange={(e) => onChange("agr_co2_in", e.target.value)}
              placeholder="e.g. 5.0"
              required
            />
          </Field>

          <Field
            className="input-group"
            label={
              <>
                {t("Outlet CO2 (%)")}
                <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
              </>
            }
          >
            <Input
              type="number"
              value={data.agr_co2_out !== undefined && data.agr_co2_out !== null ? data.agr_co2_out : ""}
              onChange={(e) => onChange("agr_co2_out", e.target.value)}
              placeholder="e.g. 0.05"
              required
            />
          </Field>

          <Field className="input-group" label={t("CH₄ (%)")}>
            <Input
              type="number"
              value={data.ch4_mole_pct !== undefined && data.ch4_mole_pct !== null ? data.ch4_mole_pct : ""}
              onChange={(e) => onChange("ch4_mole_pct", e.target.value)}
              placeholder="e.g. 85.0"
            />
          </Field>

          <Field className="input-group" label={t("CH₄ slip (fraction of inlet CH₄)")}>
            <Input
              type="number"
              value={
                data.methane_slip_factor !== undefined && data.methane_slip_factor !== null
                  ? data.methane_slip_factor
                  : ""
              }
              onChange={(e) => onChange("methane_slip_factor", e.target.value)}
              placeholder={t("blank = Compendium factor")}
              step="any"
            />
          </Field>

          {/* BUG-090: the old "flash gas recycled" / "routed to flare" checkboxes were read by no
              server code. Control is now sent as the keys the calculator uses. */}
          <div className="input-group">
            <label>{t("Offgas control")}</label>
            <CustomDropdown
              options={[
                { value: "vent", label: t("Vented (uncontrolled)") },
                { value: "flare", label: t("Routed to flare") },
                { value: "thermal_oxidizer", label: t("Thermal oxidizer / incinerator") },
                { value: "claus", label: t("Claus sulfur recovery unit") },
                { value: "agi", label: t("Acid gas injection / CCS") },
              ]}
              value={data.agr_control_type || "vent"}
              onChange={(val) => onChange("agr_control_type", val)}
            />
          </div>
          {(data.agr_control_type || "vent") !== "vent" && (
            <Field
              className="input-group"
              label={
                <>
                  {t("Control Efficiency (%)")}
                  <span className="text-[color:var(--color-red-700)]! ml-[3px]!">*</span>
                </>
              }
            >
              <Input
                type="number"
                min="0"
                max="100"
                value={data.agr_control_eff ?? ""}
                onChange={(e) => onChange("agr_control_eff", e.target.value)}
                placeholder="e.g. 98"
                required
              />
            </Field>
          )}
        </>
      )}
    </div>
  );
};

export default AGRForm;
