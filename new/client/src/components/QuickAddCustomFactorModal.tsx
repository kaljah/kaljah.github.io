import React, { useState } from "react";
import { Input } from "../ui";
import CustomDropdown from "./CustomDropdown";
import { X, PlusCircle, CheckCircle2, AlertCircle } from "lucide-react";
import api from "../api";
import { useToast } from "./Toast";
import { t } from "../i18n";

export interface QuickAddCustomFactorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFactorCreated?: (factor: any) => void;
  processType?: string;
  defaultParentFuel?: string;
}

const QuickAddCustomFactorModal: React.FC<QuickAddCustomFactorModalProps> = ({
  isOpen,
  onClose,
  onFactorCreated,
  processType = "combustion",
  defaultParentFuel = "",
}) => {
  const toast = useToast();
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [includeGasComp, setIncludeGasComp] = useState<boolean>(false);
  const [gasComp, setGasComp] = useState({
    ch4_mol_pct: "",
    c2h6_mol_pct: "",
    c3h8_mol_pct: "",
    ic4_mol_pct: "",
    nc4_mol_pct: "",
    ic5_mol_pct: "",
    nc5_mol_pct: "",
    c6_plus_mol_pct: "",
    co2_mol_pct: "",
    n2_mol_pct: "",
    h2s_ppm: "",
  });

  const [formData, setFormData] = useState({
    factor_name: "",
    unit: "kg/MMBtu",
    co2_factor: "",
    ch4_factor: "",
    n2o_factor: "",
    hhv_factor: "",
    uncertainty: "7.0", // Tier 2 default ±7%
    parent_fuel: defaultParentFuel || "",
    source: "",
    description: "",
  });

  if (!isOpen) return null;

  const handleChange = (field: string, val: string) => {
    setFormData((prev) => ({ ...prev, [field]: val }));
    if (error) setError(null);
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!formData.factor_name.trim()) {
      setError(t("Please provide a factor name (e.g. 'Skikda Refinery Off-Gas 2026')"));
      return;
    }
    if (!formData.co2_factor && !formData.ch4_factor) {
      setError(t("At least one emission factor (CO₂ or CH₄) is required."));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload: Record<string, any> = {
        factor_name: formData.factor_name.trim(),
        unit: formData.unit,
        co2_factor: formData.co2_factor ? parseFloat(formData.co2_factor) : 0,
        ch4_factor: formData.ch4_factor ? parseFloat(formData.ch4_factor) : 0,
        n2o_factor: formData.n2o_factor ? parseFloat(formData.n2o_factor) : 0,
        hhv_factor: formData.hhv_factor ? parseFloat(formData.hhv_factor) : undefined,
        uncertainty: formData.uncertainty ? parseFloat(formData.uncertainty) : 7.0,
        usage: processType || "combustion",
        parent_fuel: formData.parent_fuel || undefined,
        source: formData.source.trim() || "Facility Laboratory GC / Delivery Analysis",
        description: formData.description.trim() || undefined,
        gas_composition: includeGasComp ? {
          ch4_mol_pct: parseFloat(gasComp.ch4_mol_pct) || 0,
          c2h6_mol_pct: parseFloat(gasComp.c2h6_mol_pct) || 0,
          c3h8_mol_pct: parseFloat(gasComp.c3h8_mol_pct) || 0,
          ic4_mol_pct: parseFloat(gasComp.ic4_mol_pct) || 0,
          nc4_mol_pct: parseFloat(gasComp.nc4_mol_pct) || 0,
          ic5_mol_pct: parseFloat(gasComp.ic5_mol_pct) || 0,
          nc5_mol_pct: parseFloat(gasComp.nc5_mol_pct) || 0,
          c6_plus_mol_pct: parseFloat(gasComp.c6_plus_mol_pct) || 0,
          co2_mol_pct: parseFloat(gasComp.co2_mol_pct) || 0,
          n2_mol_pct: parseFloat(gasComp.n2_mol_pct) || 0,
          h2s_ppm: parseFloat(gasComp.h2s_ppm) || 0,
        } : undefined,
      };

      const res = await api.post("/custom-factors", payload);
      const status = res.data?.status || "Approved";
      if (status === "Approved") {
        toast.success(t("Tier 2 custom factor registered successfully"));
      } else {
        // a new factor calculates once a superuser or administrator approves it (Manage Data > Factors)
        toast.success(t("Custom factor saved. It can be used once a superuser or administrator approves it."));
      }
      const createdFactor = res.data?.factor || {
        id: res.data?.id,
        factor_name: formData.factor_name.trim(),
        status,
        ...payload,
      };

      if (onFactorCreated) {
        onFactorCreated(createdFactor);
      }
      onClose();
    } catch (err: any) {
      console.error("Failed to create custom factor:", err);
      const errMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        "Failed to create custom factor. Please verify inputs.";
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div role="presentation"
      className="modal-overlay [position:fixed]! [top:0]! [left:0]! [right:0]! [bottom:0]! [background-color:rgba(17,_24,_39,_0.6)]! [backdrop-filter:blur(4px)]! [display:flex]! [align-items:center]! [justify-content:center]! [z-index:9999]! [padding:16px]!"
     
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        className="modal-card [background:var(--color-white)]! [border-radius:12px]! [width:100%]! [max-width:560px]! [box-shadow:0_20px_25px_-5px_rgba(0,_0,_0,_0.1),_0_10px_10px_-5px_rgba(0,_0,_0,_0.04)]! [border:1px_solid_var(--color-legacy-e5e7eb)]! [overflow:hidden]!"
       
      >
        {/* Header */}
        <div
          className="p-[16px_20px]! [border-bottom:1px_solid_var(--color-legacy-e5e7eb)]! flex! items-center! justify-between! bg-[color:var(--color-legacy-f9fafb)]!"
        >
          <div className="flex! items-center! gap-[8px]!">
            <div
              className="w-[32px]! h-[32px]! rounded-[8px]! bg-[color:rgba(255,_102,_0,_0.1)]! text-[color:var(--color-link)]! flex! items-center! justify-center!"
            >
              <PlusCircle size={18} />
            </div>
            <div>
              <h3 className="m-[0px]! text-[length:1rem]! font-semibold! text-[color:var(--color-legacy-111827)]!">
                {t("Register Tier 2 Custom Factor")}
              </h3>
              <p className="m-[0px]! text-[length:0.75rem]! text-[color:var(--color-legacy-6b7280)]!">
                {t("Add a site-calibrated or supplier emission factor without leaving this form")}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            aria-label="Close"
            className="close-btn [border:none]! bg-[color:transparent]! text-[color:var(--color-legacy-9ca3af)]! cursor-pointer! p-[4px]! rounded-[4px]!"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-[20px]!">
          {error && (
            <div
              className="[display:flex]! [align-items:center]! [gap:8px]! [padding:10px_12px]! [background-color:var(--color-red-50)]! [border:1px_solid_var(--color-legacy-fee2e2)]! [border-radius:6px]! [color:var(--color-red-700)]! [font-size:0.8rem]! [margin-bottom:16px]!"
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div className="flex! flex-col! gap-[14px]!">
            {/* Factor Name */}
            <div>
              <label
                className="block! text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-374151)]! mb-[4px]!"
              >
                {t("Factor Name")}{" "}<span className="text-[color:var(--color-red-700)]!">*</span>
              </label>
              <Input
                type="text"
               
                className="w-full! p-[8px_10px]! text-[length:0.85rem]!"
                placeholder={t("e.g. Hassi R'Mel Fuel Gas 2026, Skikda Distillate")}
                value={formData.factor_name}
                onChange={(e) => handleChange("factor_name", e.target.value)}
                required
              />
            </div>

            {/* Units & Base Fuel */}
            <div className="[display:grid]! [grid-template-columns:1fr_1fr]! [gap:12px]!">
              <div>
                <label
                  className="block! text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-374151)]! mb-[4px]!"
                >
                  {t("Factor Unit")}{" "}<span className="text-[color:var(--color-red-700)]!">*</span>
                </label>
                <CustomDropdown
                  options={[
                    { value: "kg/MMBtu", label: t("kg / MMBtu (Energy basis)") },
                    { value: "kg/m3", label: t("kg / m³ (Volumetric gas)") },
                    { value: "kg/scf", label: t("kg / scf (Volumetric gas)") },
                    { value: "kg/liter", label: t("kg / Liter (Liquid fuel)") },
                    { value: "kg/gal", label: t("kg / Gallon (Liquid fuel)") },
                    { value: "kg/kg", label: t("kg / kg (Mass basis)") },
                    { value: "tonne/tonne", label: t("tonne / tonne (Mass basis)") },
                  ]}
                  value={formData.unit}
                  onChange={(val) => handleChange("unit", String(val))}
                />
              </div>

              <div>
                <label
                  className="block! text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-374151)]! mb-[4px]!"
                >
                  {t("Parent / Reference Fuel")}
                </label>
                <Input
                  type="text"
                 
                  className="w-full! p-[8px_10px]! text-[length:0.85rem]!"
                  placeholder={t("e.g. Natural Gas, Diesel")}
                  value={formData.parent_fuel}
                  onChange={(e) => handleChange("parent_fuel", e.target.value)}
                />
              </div>
            </div>

            {/* Gas Emission Factors */}
            <div
              className="bg-[color:var(--color-legacy-f9fafb)]! [border:1px_solid_var(--color-legacy-e5e7eb)]! rounded-[8px]! p-[12px]!"
            >
              <div
                className="text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-4b5563)]! mb-[8px]! uppercase! [letter-spacing:0.025em]!"
              >
                {t("Emission Factors (")}{formData.unit})
              </div>
              <div className="[display:grid]! [grid-template-columns:1fr_1fr_1fr]! [gap:10px]!">
                <div>
                  <label
                    className="block! text-[length:0.7rem]! text-[color:var(--color-legacy-6b7280)]! mb-[2px]!"
                  >
                    {t("CO₂ Factor")}
                  </label>
                  <Input
                    type="number"
                    step="any"
                   
                    className="w-full! p-[6px_8px]! text-[length:0.85rem]!"
                    placeholder="e.g. 53.06"
                    value={formData.co2_factor}
                    onChange={(e) => handleChange("co2_factor", e.target.value)}
                  />
                </div>
                <div>
                  <label
                    className="block! text-[length:0.7rem]! text-[color:var(--color-legacy-6b7280)]! mb-[2px]!"
                  >
                    {t("CH₄ Factor")}
                  </label>
                  <Input
                    type="number"
                    step="any"
                   
                    className="w-full! p-[6px_8px]! text-[length:0.85rem]!"
                    placeholder="e.g. 0.001"
                    value={formData.ch4_factor}
                    onChange={(e) => handleChange("ch4_factor", e.target.value)}
                  />
                </div>
                <div>
                  <label
                    className="block! text-[length:0.7rem]! text-[color:var(--color-legacy-6b7280)]! mb-[2px]!"
                  >
                    {t("N₂O Factor")}
                  </label>
                  <Input
                    type="number"
                    step="any"
                   
                    className="w-full! p-[6px_8px]! text-[length:0.85rem]!"
                    placeholder="e.g. 0.0001"
                    value={formData.n2o_factor}
                    onChange={(e) => handleChange("n2o_factor", e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* HHV & Uncertainty */}
            <div className="[display:grid]! [grid-template-columns:1fr_1fr]! [gap:12px]!">
              <div>
                <label
                  className="block! text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-374151)]! mb-[4px]!"
                >
                  {t("Heating Value (HHV)")}
                </label>
                <Input
                  type="number"
                  step="any"
                 
                  className="w-full! p-[8px_10px]! text-[length:0.85rem]!"
                  placeholder={t("e.g. 1085 (Btu/scf)")}
                  value={formData.hhv_factor}
                  onChange={(e) => handleChange("hhv_factor", e.target.value)}
                />
              </div>

              <div>
                <label
                  className="block! text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-374151)]! mb-[4px]!"
                >
                  {t("Factor Uncertainty (±%)")}
                </label>
                <div className="relative!">
                  <Input
                    type="number"
                    step="0.1"
                   
                    className="w-full! p-[8px_10px]! text-[length:0.85rem]!"
                    placeholder="7.0"
                    value={formData.uncertainty}
                    onChange={(e) => handleChange("uncertainty", e.target.value)}
                  />
                  <span
                    className="[position:absolute]! [right:10px]! [top:50%]! [transform:translateY(-50%)]! text-[length:0.75rem]! text-[color:var(--color-legacy-9ca3af)]!"
                  >
                    {t("% (Tier 2 default: ±7%)")}
                  </span>
                </div>
              </div>
            </div>

            {/* Gas Stream Composition Trigger & Inputs */}
            {(() => {
              const molSum = (
                (Number(gasComp.ch4_mol_pct) || 0) +
                (Number(gasComp.c2h6_mol_pct) || 0) +
                (Number(gasComp.c3h8_mol_pct) || 0) +
                (Number(gasComp.ic4_mol_pct) || 0) +
                (Number(gasComp.nc4_mol_pct) || 0) +
                (Number(gasComp.ic5_mol_pct) || 0) +
                (Number(gasComp.nc5_mol_pct) || 0) +
                (Number(gasComp.c6_plus_mol_pct) || 0) +
                (Number(gasComp.co2_mol_pct) || 0) +
                (Number(gasComp.n2_mol_pct) || 0)
              );

              const handleNormalizeModal = () => {
                if (molSum <= 0) return;
                const factor = 100.0 / molSum;
                const round3 = (v: any) => (Number(v) || 0) > 0 ? ((Number(v) || 0) * factor).toFixed(3) : "";
                setGasComp({
                  ch4_mol_pct: round3(gasComp.ch4_mol_pct),
                  c2h6_mol_pct: round3(gasComp.c2h6_mol_pct),
                  c3h8_mol_pct: round3(gasComp.c3h8_mol_pct),
                  ic4_mol_pct: round3(gasComp.ic4_mol_pct),
                  nc4_mol_pct: round3(gasComp.nc4_mol_pct),
                  ic5_mol_pct: round3(gasComp.ic5_mol_pct),
                  nc5_mol_pct: round3(gasComp.nc5_mol_pct),
                  c6_plus_mol_pct: round3(gasComp.c6_plus_mol_pct),
                  co2_mol_pct: round3(gasComp.co2_mol_pct),
                  n2_mol_pct: round3(gasComp.n2_mol_pct),
                  h2s_ppm: gasComp.h2s_ppm,
                });
              };

              const MODAL_PVT_FIELDS = [
                { key: "ch4_mol_pct" as const, label: "CH₄", name: "Methane", unit: "mol %", placeholder: "78.4" },
                { key: "c2h6_mol_pct" as const, label: "C₂H₆", name: "Ethane", unit: "mol %", placeholder: "12.1" },
                { key: "c3h8_mol_pct" as const, label: "C₃H₈", name: "Propane", unit: "mol %", placeholder: "5.2" },
                { key: "ic4_mol_pct" as const, label: "i-C₄H₁₀", name: "i-Butane", unit: "mol %", placeholder: "0.8" },
                { key: "nc4_mol_pct" as const, label: "n-C₄H₁₀", name: "n-Butane", unit: "mol %", placeholder: "1.2" },
                { key: "ic5_mol_pct" as const, label: "i-C₅H₁₂", name: "i-Pentane", unit: "mol %", placeholder: "0.4" },
                { key: "nc5_mol_pct" as const, label: "n-C₅H₁₂", name: "n-Pentane", unit: "mol %", placeholder: "0.5" },
                { key: "c6_plus_mol_pct" as const, label: "C₆+", name: "Hexanes+", unit: "mol %", placeholder: "0.3" },
                { key: "co2_mol_pct" as const, label: "CO₂", name: "Carbon Dioxide", unit: "mol %", placeholder: "2.1" },
                { key: "n2_mol_pct" as const, label: "N₂", name: "Nitrogen", unit: "mol %", placeholder: "2.2" },
                { key: "h2s_ppm" as const, label: "H₂S", name: "Hydrogen Sulfide", unit: "ppm", placeholder: "0.0" },
              ];

              return (
                <div className="bg-[color:var(--color-legacy-f9fafb)]! [border:1px_solid_var(--color-legacy-e5e7eb)]! rounded-[8px]! p-[12px]!">
                  <div className="flex! items-center! justify-between! mb-[6px]!">
                    <div className="flex items-center gap-2">
                      <label className="text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-4b5563)]! uppercase! [letter-spacing:0.025em]!">
                        {t("PVT & Chromatography Stream Composition")}
                      </label>
                      {includeGasComp && (
                        <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold ${
                          molSum >= 99.5 && molSum <= 100.5
                            ? "bg-green-100 text-green-800"
                            : molSum === 0
                            ? "bg-slate-100 text-slate-600"
                            : "bg-amber-100 text-amber-800"
                        }`}>
                          {molSum >= 99.5 && molSum <= 100.5 ? `✓ ${molSum.toFixed(2)}%` : `Σ = ${molSum.toFixed(2)}%`}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {includeGasComp && molSum > 0 && Math.abs(molSum - 100) > 0.05 && (
                        <button
                          type="button"
                          onClick={handleNormalizeModal}
                          className="text-[11px] px-2 py-0.5 bg-orange-600 text-white rounded font-medium hover:bg-orange-700"
                        >
                          Normalize
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setIncludeGasComp(!includeGasComp)}
                        className="text-[length:0.75rem]! text-orange-600 font-semibold hover:underline flex! items-center! gap-[4px]!"
                      >
                        <PlusCircle size={13} />
                        {includeGasComp ? t("Remove Composition") : t("Include Gas Composition")}
                      </button>
                    </div>
                  </div>
                  {includeGasComp && (
                    <div className="[display:grid]! [grid-template-columns:repeat(3,1fr)]! sm:[grid-template-columns:repeat(4,1fr)]! [gap:6px]! mt-[8px]!">
                      {MODAL_PVT_FIELDS.map((fld) => (
                        <div key={fld.key} className="bg-white p-1.5 rounded border border-slate-200">
                          <div className="flex justify-between items-center mb-0.5">
                            <span className="text-[10px] font-bold text-slate-700">{fld.label}</span>
                            <span className="text-[9px] text-slate-400">{fld.unit}</span>
                          </div>
                          <Input
                            type="number"
                            step="any"
                            className="w-full! p-[3px_6px]! text-[length:0.75rem]! font-mono"
                            placeholder={fld.placeholder}
                            value={gasComp[fld.key]}
                            onChange={(e) => setGasComp({ ...gasComp, [fld.key]: e.target.value })}
                          />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Audit Reference / Source */}
            <div>
              <label
                className="block! text-[length:0.75rem]! font-semibold! text-[color:var(--color-legacy-374151)]! mb-[4px]!"
              >
                {t("Data Source / Lab Certificate Reference")}
              </label>
              <Input
                type="text"
               
                className="w-full! p-[8px_10px]! text-[length:0.85rem]!"
                placeholder={t("e.g. Sonatrach Analysis Certificate #2026-GC-041, Naftal Slip")}
                value={formData.source}
                onChange={(e) => handleChange("source", e.target.value)}
              />
            </div>
          </div>

          {/* Footer Actions */}
          <div
            className="mt-[20px]! pt-[14px]! [border-top:1px_solid_var(--color-legacy-e5e7eb)]! flex! justify-end! gap-[10px]!"
          >
            <button
              type="button"
              className="btn btn-secondary p-[8px_16px]! text-[length:0.85rem]!"
              onClick={onClose}
              disabled={loading}
             
            >
              {t("Cancel")}
            </button>
            <button
              type="submit"
              className="btn btn-primary p-[8px_20px]! text-[length:0.85rem]! flex! items-center! gap-[6px]!"
              disabled={loading}
             
            >
              {loading ? (
                t("Saving...")
              ) : (
                <>
                  <CheckCircle2 size={16} />
                  <span>{t("Save & Apply Factor")}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuickAddCustomFactorModal;
