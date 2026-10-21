import React from "react";
import { Input, Field } from "../../ui";
import ColumnMappingWizard from "../ColumnMappingWizard";
import CustomDropdown from "../CustomDropdown";
import { currentLanguage, t } from "../../i18n";
import { ACTIVITY_YEAR_MIN, activityYearMax } from "../../constants";

export interface Scope3FormNewScope3Props {
  UNIT_MULTIPLIERS: Record<string, Record<string, number>>;
  activityType: string;
  amount: string | number;
  baseUnit: string;
  category: string;
  eeioNaics?: string;
  eeioResult?: {
    industry_name?: string;
    emission_factor?: number | string;
    ef_unit?: string;
    co2e: number;
    [key: string]: any;
  } | null;
  eeioSpend?: string | number;
  emissionFactor: string | number;
  facilityId: string | number;
  getActivityOptions: () => Array<{ value: string; label: string }>;
  getCategoryOptions: () => Array<{ value: string; label: string }>;
  getFacilityOptions: () => Array<{ value: string; label: string }>;
  handleAddEntry: (status: "Draft" | "Verified") => void;
  handleCalculateEeio?: () => void;
  handleImportSuccess: () => void;
  handleUnitChange: (newUnit: string) => void;
  importModal: { isOpen: boolean; type?: string };
  month: string | number;
  naicsOptions?: Array<{ naics: string; name: string; kg_co2e_per_usd: number | string }>;
  searchNaics?: (query: string) => void;
  setActivityType: (val: string) => void;
  setAmount: (val: string) => void;
  setCategory: (val: string) => void;
  setEeioNaics?: (val: string) => void;
  setEeioSpend?: (val: string) => void;
  setEmissionFactor: (val: string) => void;
  setFacilityId: (val: string) => void;
  setImportModal: React.Dispatch<React.SetStateAction<{ isOpen: boolean; type?: string }>>;
  setMonth: (val: string | number) => void;
  setShowEeioCalc?: React.Dispatch<React.SetStateAction<boolean>>;
  setYear: (val: string | number) => void;
  showEeioCalc?: boolean;
  submitting: boolean;
  unit: string;
  year: string | number;
}

// Extracted from Scope3Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
export const Scope3FormNewScope3: React.FC<Scope3FormNewScope3Props> = ({
  UNIT_MULTIPLIERS,
  activityType,
  amount,
  baseUnit,
  category,
  emissionFactor,
  facilityId,
  getActivityOptions,
  getCategoryOptions,
  getFacilityOptions,
  handleAddEntry,
  handleImportSuccess,
  handleUnitChange,
  importModal,
  month,
  setActivityType,
  setAmount,
  setCategory,
  setEmissionFactor,
  setFacilityId,
  setImportModal,
  setMonth,
  setYear,
  submitting,
  unit,
  year,
}) => (
  <div className="calc-panel">
    <div className="flex! justify-between! items-center! mb-[20px]!">
      <h3 className="m-[0px]!">{t("New Scope 3 Entry")}</h3>
      <div className="text-right!">
        <span className="text-[color:var(--color-violet-700)]! font-semibold! text-[length:0.9rem]!">
          {t("Scope 3: Other Indirect")}
        </span>
      </div>
    </div>

    <div
      className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(200px,_1fr))]! [gap:20px]! [margin-bottom:20px]!"
    >
      <Field className="input-group" label={t("Year")}>
        <Input
          type="number"
          min={ACTIVITY_YEAR_MIN}
          max={activityYearMax()}
          value={year || ""}
          onChange={(e) => setYear(e.target.value)}
        />
      </Field>
      <div className="input-group">
        <label>{t("Month")}</label>
        <CustomDropdown
          options={[...Array(12)].map((_, i) => ({
            value: i + 1,
            label: new Date(2025, i, 1).toLocaleString(currentLanguage() === "fr" ? "fr-FR" : "en-US", { month: "long" }),
          }))}
          value={Number(month) || 1}
          onChange={(val) => setMonth(Number(val))}
          placeholder={t("Select Month...")}
        />
      </div>
      <div className="input-group">
        <label>{t("Facility")}</label>
        <CustomDropdown
          options={getFacilityOptions()}
          value={facilityId || ""}
          onChange={setFacilityId}
        />
      </div>
      <div className="input-group">
        <label>{t("Category")}</label>
        <CustomDropdown
          options={getCategoryOptions()}
          value={category}
          onChange={setCategory}
        />
      </div>
    </div>

    <div
      className="[display:grid]! [grid-template-columns:repeat(auto-fit,_minmax(200px,_1fr))]! [gap:20px]!"
    >
      <div className="input-group">
        <label>{t("Activity Type")}</label>
        <CustomDropdown
          options={getActivityOptions()}
          value={activityType}
          onChange={setActivityType}
        />
      </div>
      <Field className="input-group" label={t("Amount")}>
        <Input
          type="number"
          min="0"
          value={amount || ""}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.00"
          step="0.01"
        />
      </Field>
      <div className="input-group">
        <label>{t("Unit")}</label>
        {UNIT_MULTIPLIERS[baseUnit] ? (
          <CustomDropdown
            options={Object.keys(UNIT_MULTIPLIERS[baseUnit]).map((u) => ({
              value: u,
              label: u,
            }))}
            value={unit}
            onChange={(val) => handleUnitChange(String(val))}
          />
        ) : (
          <Input
            type="text"
            value={unit}
            readOnly
            className="bg-[color:rgba(255,255,255,0.03)]! cursor-not-allowed!"
          />
        )}
      </div>
      <Field className="input-group" label={t("EF (kg CO₂e/unit)")}>
        <Input
          type="number"
          min="0"
          value={emissionFactor || ""}
          onChange={(e) => setEmissionFactor(e.target.value)}
          step="0.01"
        />
      </Field>
    </div>

    <div className="mt-[24px]!">
      <button
        type="button"
        className={`btn-add-activity w-full ${submitting ? "[cursor:not-allowed]! [opacity:0.6]!" : "[cursor:pointer]! [opacity:1]!"}`}
        disabled={submitting}
        onClick={() => handleAddEntry("Verified")}
      >
        {submitting ? t("Processing...") : t("+ Calculate & Submit for Review")}
      </button>
    </div>

    {importModal.isOpen && (
      <ColumnMappingWizard
        onClose={() => setImportModal({ ...importModal, isOpen: false })}
        onUploadSuccess={handleImportSuccess}
        type={importModal.type}
      />
    )}
  </div>
);

export default Scope3FormNewScope3;
