import React from "react";
import { Button, Input, Textarea, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { Database, Upload } from "lucide-react";
import PaginationControls from "./PaginationControls";
import { t } from "../../i18n";

export interface CustomFactorRecord {
  id: string | number;
  factor_name?: string;
  name?: string;
  unit: string;
  co2_factor: number | string;
  ch4_factor: number | string;
  n2o_factor: number | string;
  source?: string;
  description?: string;
  co2_uncertainty?: number | string;
  ch4_uncertainty?: number | string;
  n2o_uncertainty?: number | string;
  status?: string;
  parent_fuel?: string;
  [key: string]: any;
}

export interface FactorWorkbenchState {
  meter_precision: number;
  lab_precision: number;
  gwp_uncertainty: number;
  [key: string]: any;
}

export interface FactorsTabProps {
  ITEMS_PER_PAGE: number;
  currentPage: number;
  editingFactorId: string | number | null;
  factorForm: Record<string, any>;
  filteredFactors: CustomFactorRecord[];
  handleArchiveFactor: (id: string | number) => void;
  handleApproveFactor?: (id: string | number) => void;
  user?: { role?: string; [key: string]: any } | null;
  handleDeleteFactor: (id: string | number) => void;
  handleEditFactor: (factor: CustomFactorRecord) => void;
  handleFactorChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void;
  handleSaveFactor: () => void;
  setCurrentPage: (page: number) => void;
  setEditingFactorId: (id: string | number | null) => void;
  setFactorForm: React.Dispatch<React.SetStateAction<any>>;
  setImportModal: (modal: { isOpen: boolean; type: string }) => void;
  setWorkbench: React.Dispatch<React.SetStateAction<any>>;
  workbench: FactorWorkbenchState;
}

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const FactorsTab: React.FC<FactorsTabProps> = ({
  ITEMS_PER_PAGE,
  currentPage,
  editingFactorId,
  factorForm,
  filteredFactors,
  handleArchiveFactor,
  handleApproveFactor,
  user,
  handleDeleteFactor,
  handleEditFactor,
  handleFactorChange,
  handleSaveFactor,
  setCurrentPage,
  setEditingFactorId,
  setFactorForm,
  setImportModal,
  setWorkbench,
  workbench,
}) => (
  <div className="manage-card glass-panel">
    <div className="flex! flex-wrap! justify-between! items-start! gap-[12px]! mb-[32px]!">
      <div>
        <h2 className="mb-[8px]! font-bold!">{t("Custom Emission Factors")}</h2>
        <p className="text-[color:var(--text-secondary)]! m-[0px]!">
          {t("Define custom factors for specialized equipment.")}
        </p>
      </div>
      <button
        className="action-btn [display:flex]! [align-items:center]! [gap:8px]! [padding:8px_16px]! [font-size:0.9rem]! [width:auto]! [white-space:nowrap]!"
        onClick={() => setImportModal({ isOpen: true, type: "custom_factors" })}
       
      >
        <Upload size={16} />{" "}{t("Bulk Import (CSV)")}
      </button>
    </div>

    {/* Create/Edit Form */}
    <div className="grid-forms md:[grid-template-columns:repeat(3,1fr)]!">
      <Field className="input-group" label={t("Factor Name")}>
        <Input
          type="text"
          name="factor_name"
          value={factorForm.factor_name || ""}
          onChange={handleFactorChange}
          placeholder={t("e.g. Flare High Efficiency")}
        />
      </Field>
      <Field className="input-group" label={t("Parent Fuel (Internal Reference)")}>
        <NativeSelect
          name="parent_fuel"
          value={factorForm.parent_fuel || ""}
          onChange={(e) => setFactorForm({ ...factorForm, parent_fuel: e.target.value })}
          className="component-select"
        >
          <option value="">{t("Searchable Reference...")}</option>
          <option value="Natural Gas">{t("Natural Gas (Standard)")}</option>
          <option value="Diesel">{t("Diesel (Generic)")}</option>
          <option value="Gasoline">{t("Gasoline (Generic)")}</option>
          <option value="Propane">{t("Propane (Generic)")}</option>
          <option value="Crude Oil">{t("Crude Oil (Heavy)")}</option>
          <option value="Fuel Oil">{t("Fuel Oil (No. 4/6)")}</option>
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Unit")}>
        <NativeSelect
          name="unit"
          value={factorForm.unit || "scf"}
          onChange={handleFactorChange}
          className="component-select"
        >
          <option value="scf">{t("scf")}</option>
          <option value="m³">m³</option>
          <option value="gal">{t("gal")}</option>
          <option value="bbl">{t("bbl")}</option>
          <option value="kg">{t("kg")}</option>
          <option value="tonne">{t("tonne")}</option>
        </NativeSelect>
      </Field>
      <Field className="input-group" label={t("CO₂ Factor (kg/unit)")}>
        <Input
          type="number"
          name="co2_factor"
          value={factorForm.co2_factor || ""}
          onChange={handleFactorChange}
          placeholder="0.0"
          step="0.001"
        />
      </Field>
      <Field className="input-group" label={t("CH₄ Factor (kg/unit)")}>
        <Input
          type="number"
          name="ch4_factor"
          value={factorForm.ch4_factor || ""}
          onChange={handleFactorChange}
          placeholder="0.0"
          step="0.001"
        />
      </Field>
      <Field className="input-group" label={t("N₂O Factor (kg/unit)")}>
        <Input
          type="number"
          name="n2o_factor"
          value={factorForm.n2o_factor || ""}
          onChange={handleFactorChange}
          placeholder="0.0"
          step="0.001"
        />
      </Field>
      <Field className="input-group" label={t("CO₂ Uncertainty (±%)")}>
        <Input
          type="number"
          name="co2_uncertainty"
          value={factorForm.co2_uncertainty || ""}
          onChange={handleFactorChange}
          placeholder="e.g. 5.0"
          step="0.1"
        />
      </Field>
      <Field className="input-group" label={t("CH₄ Uncertainty (±%)")}>
        <Input
          type="number"
          name="ch4_uncertainty"
          value={factorForm.ch4_uncertainty || ""}
          onChange={handleFactorChange}
          placeholder="e.g. 50.0"
          step="0.1"
        />
      </Field>
      <Field className="input-group" label={t("N₂O Uncertainty (±%)")}>
        <Input
          type="number"
          name="n2o_uncertainty"
          value={factorForm.n2o_uncertainty || ""}
          onChange={handleFactorChange}
          placeholder="e.g. 150.0"
          step="0.1"
        />
      </Field>
      <div className="input-group md:[grid-column:span_2]!">
        <label>{t("Lab Certification / Source Reference")}</label>
        <Input
          type="text"
          name="source"
          value={factorForm.source || ""}
          onChange={handleFactorChange}
          placeholder={t("e.g. Lab GC Report #2026-ARZ-01 / ISO 17025 / EPD Ref")}
        />
      </div>
      <div className="input-group md:[grid-column:span_3]!">
        <label>{t("Description & Technical Justification")}</label>
        <Textarea
          name="description"
          value={factorForm.description || ""}
          onChange={handleFactorChange}
          rows={2}
          placeholder={t("Engineering justification, gas chromatography sampling conditions, or manufacturer test certificate details...")}
          className="[resize:vertical]!"
        />
      </div>
    </div>

    {/* EF Uncertainty Workbench */}
    <div className="mt-[20px]! p-[20px]! bg-[color:rgba(30,_41,_59,_0.03)]! rounded-[12px]! [border:1px_solid_rgba(0,0,0,0.05)]!">
      <h4 className="m-[0_0_15px_0]! text-[length:1rem]! flex! items-center! gap-[8px]!">
        <Database size={16} />{" "}{t("EF Uncertainty Workbench (ISO 14064-1 method)")}
      </h4>
      <div className="grid grid-cols-1 gap-[15px] md:grid-cols-3">
        <div className="input-group">
          <label className="text-[length:0.8rem]!">{t("Meter Precision (±%)")}</label>
          <Input
            type="number"
            step="0.1"
            value={workbench.meter_precision}
            onChange={(e) =>
              setWorkbench({ ...workbench, meter_precision: parseFloat(e.target.value) || 0 })
            }
            className="p-[8px]!"
          />
        </div>
        <div className="input-group">
          <label className="text-[length:0.8rem]!">{t("Lab Analysis (±%)")}</label>
          <Input
            type="number"
            step="0.1"
            value={workbench.lab_precision}
            onChange={(e) =>
              setWorkbench({ ...workbench, lab_precision: parseFloat(e.target.value) || 0 })
            }
            className="p-[8px]!"
          />
        </div>
        <div className="input-group">
          <label className="text-[length:0.8rem]!">{t("GWP Standard Selection")}</label>
          <NativeSelect
            className="component-select p-[8px]! text-[length:0.85rem]!"
            value={workbench.gwp_uncertainty}
            onChange={(e) =>
              setWorkbench({ ...workbench, gwp_uncertainty: parseFloat(e.target.value) || 0 })
            }
          >
            <option value="20.0">{t("IPCC AR4 (±20.0%)")}</option>
            <option value="15.0">{t("IPCC AR5 (±15.0%)")}</option>
            <option value="11.0">{t("IPCC AR6 (±11.0%)")}</option>
          </NativeSelect>
        </div>
      </div>
      <Button
        variant="ghost"
        type="submit"
        className="mt-[15px]! text-[color:var(--color-blue-700)]! font-semibold! text-[length:0.85rem]!"
        onClick={() => {
          const co2_u = Math.sqrt(
            Math.pow(workbench.meter_precision, 2) + Math.pow(workbench.lab_precision, 2),
          );
          // IPCC typically suggests ±50% for CH4 and ±150% for N2O technology uncertainty
          const ch4_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(50.0, 2));
          const n2o_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(150.0, 2));

          setFactorForm({
            ...factorForm,
            co2_uncertainty: co2_u.toFixed(2),
            ch4_uncertainty: ch4_u.toFixed(2),
            n2o_uncertainty: n2o_u.toFixed(2),
          });
        }}
      >
        {t("Calculate Combined Uncertainty (SRSS)")}
      </Button>
    </div>

    <div className="flex! gap-[10px]! mt-[20px]!">
      <button className="action-btn" onClick={handleSaveFactor}>
        {editingFactorId ? t("Update Factor") : t("Save Factor")}
      </button>
      {editingFactorId && (
        <button
          className="action-btn"
          onClick={() => {
            setEditingFactorId(null);
            setFactorForm({
              factor_name: "",
              parent_fuel: "",
              unit: "scf",
              co2_factor: "",
              ch4_factor: "",
              n2o_factor: "",
              co_factor: "",
              co2_uncertainty: "",
              ch4_uncertainty: "",
              n2o_uncertainty: "",
              source: "",
              description: "",
            });
          }}
        >
          {t("Cancel Edit")}
        </button>
      )}
    </div>

    <div className="table-container mt-[40px]!" tabIndex={0} role="region" aria-label={t("Custom emission factors")}>
      <div className="flex! justify-between! items-center! mb-[16px]!">
        <h3 className="m-[0px]!">{t("Custom Factors")}</h3>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>{t("Factor Name")}</th>
            <th>{t("Unit")}</th>
            <th>CO2</th>
            <th>CH4</th>
            <th>N2O</th>
            <th>{t("Certification / Description")}</th>
            <th>{t("CO₂ Unc.")}</th>
            <th>{t("CH₄ Unc.")}</th>
            <th>{t("N₂O Unc.")}</th>
            <th>{t("Status")}</th>
            <th>{t("Actions")}</th>
          </tr>
        </thead>
        <tbody>
          {filteredFactors
            .slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)
            .map((f) => (
              <tr key={f.id}>
                <td>
                  <strong>{f.factor_name || f.name}</strong>
                </td>
                <td>{f.unit}</td>
                <td>{f.co2_factor}</td>
                <td>{f.ch4_factor}</td>
                <td>{f.n2o_factor}</td>
                <td className="max-w-[240px]!">
                  {f.source && (
                    <span className="inline-block! text-[length:0.75rem]! bg-[color:var(--color-legacy-dbeafe)]! text-[color:var(--color-blue-700)]! p-[1px_6px]! rounded-[4px]! font-semibold! mb-[2px]!">
                      {f.source}
                    </span>
                  )}
                  {f.description && (
                    <div
                      className="text-[length:0.75rem]! text-[color:var(--text-secondary)]! overflow-hidden! [text-overflow:ellipsis]! whitespace-nowrap!"
                      title={f.description}
                    >
                      {f.description}
                    </div>
                  )}
                  {!f.source && !f.description && (
                    <span className="text-[color:var(--text-secondary)]!">—</span>
                  )}
                </td>
                <td className={f.co2_uncertainty ? "[color:var(--color-green-700)]!" : "[color:inherit]!"}>
                  {f.co2_uncertainty ? `±${f.co2_uncertainty}%` : "—"}
                </td>
                <td className={f.ch4_uncertainty ? "[color:var(--color-blue-700)]!" : "[color:inherit]!"}>
                  {f.ch4_uncertainty ? `±${f.ch4_uncertainty}%` : "—"}
                </td>
                <td className={f.n2o_uncertainty ? "[color:var(--color-violet-700)]!" : "[color:inherit]!"}>
                  {f.n2o_uncertainty ? `±${f.n2o_uncertainty}%` : "—"}
                </td>
                <td>
                  {f.status === "Pending" ? (
                    <span className="inline-block! text-[length:0.75rem]! bg-[color:var(--color-legacy-fef3c7)]! text-[color:var(--color-legacy-92400e)]! p-[2px_8px]! rounded-[4px]! font-semibold!">
                      {t("Pending")}
                    </span>
                  ) : f.status === "Rejected" ? (
                    <span className="inline-block! text-[length:0.75rem]! bg-[color:var(--color-legacy-fee2e2)]! text-[color:var(--color-red-700)]! p-[2px_8px]! rounded-[4px]! font-semibold!">
                      {t("Rejected")}
                    </span>
                  ) : (
                    <span className="inline-block! text-[length:0.75rem]! bg-[color:var(--color-legacy-dcfce7)]! text-[color:var(--color-legacy-15803d)]! p-[2px_8px]! rounded-[4px]! font-semibold!">
                      {t("Approved")}
                    </span>
                  )}
                </td>
                <td>
                  {user?.role === "admin" && f.status === "Pending" && (
                    <button
                      onClick={() => handleApproveFactor && handleApproveFactor(f.id)}
                      className="text-[color:var(--color-legacy-15803d)]! font-semibold! mr-[6px]!"
                      title={t("Approve custom factor")}
                    >
                      {t("Approve")}
                    </button>
                  )}
                  <button onClick={() => handleEditFactor(f)}>{t("Edit")}</button>
                  <button
                    onClick={() => handleArchiveFactor(f.id)}
                    title={t("Hide from new entries; records that use it keep it")}
                  >
                    {t("Archive")}
                  </button>
                  <button onClick={() => handleDeleteFactor(f.id)}>{t("Delete")}</button>
                </td>
              </tr>
            ))}
          {filteredFactors.length === 0 && (
            <tr>
              <td colSpan={11} className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                {t("No custom emission factors found.")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <PaginationControls
        currentPage={currentPage}
        totalItems={filteredFactors.length}
        itemsPerPage={ITEMS_PER_PAGE}
        onPageChange={setCurrentPage}
      />
    </div>
  </div>
);

export default FactorsTab;
