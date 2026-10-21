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
const PVT_COMPONENTS = [
  { key: "ch4_mol_pct", label: "CH₄", shortName: "Methane", unit: "mol %", placeholder: "78.40" },
  { key: "c2h6_mol_pct", label: "C₂H₆", shortName: "Ethane", unit: "mol %", placeholder: "12.10" },
  { key: "c3h8_mol_pct", label: "C₃H₈", shortName: "Propane", unit: "mol %", placeholder: "5.20" },
  { key: "co2_mol_pct", label: "CO₂", shortName: "Carbon Dioxide", unit: "mol %", placeholder: "2.10" },
  { key: "ic4_mol_pct", label: "i-C₄H₁₀", shortName: "i-Butane", unit: "mol %", placeholder: "0.80" },
  { key: "nc4_mol_pct", label: "n-C₄H₁₀", shortName: "n-Butane", unit: "mol %", placeholder: "1.20" },
  { key: "ic5_mol_pct", label: "i-C₅H₁₂", shortName: "i-Pentane", unit: "mol %", placeholder: "0.40" },
  { key: "nc5_mol_pct", label: "n-C₅H₁₂", shortName: "n-Pentane", unit: "mol %", placeholder: "0.50" },
  { key: "c6_plus_mol_pct", label: "C₆+", shortName: "Hexanes+", unit: "mol %", placeholder: "0.30" },
  { key: "n2_mol_pct", label: "N₂", shortName: "Nitrogen", unit: "mol %", placeholder: "2.20" },
  { key: "h2s_ppm", label: "H₂S", shortName: "Hydrogen Sulfide", unit: "ppm", placeholder: "0.0" },
];

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
      <div className="[grid-column:1/-1]! mb-1">
        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
          {t("Lab Certification / Source Reference")}
        </label>
        <Input
          type="text"
          name="source"
          value={factorForm.source || ""}
          onChange={handleFactorChange}
          placeholder={t("e.g. Lab GC Report #2026-ARZ-01 / ISO 17025 / EPD Ref")}
        />
      </div>
      <div className="[grid-column:1/-1]! mb-1">
        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
          {t("Description & Technical Justification")}
        </label>
        <Textarea
          name="description"
          value={factorForm.description || ""}
          onChange={handleFactorChange}
          rows={2}
          placeholder={t("Engineering justification, gas chromatography sampling conditions, or manufacturer test certificate details...")}
          className="[resize:vertical]!"
        />
      </div>
      <div className="[grid-column:1/-1]! mb-1">
        <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
          {t("Out-of-range justification")} <span className="font-normal lowercase text-slate-400">({t("only needed if a factor is above 500 CO₂, 100 CH₄ or 10 N₂O kg/MMBtu")})</span>
        </label>
        <Textarea
          name="justification"
          value={factorForm.justification || ""}
          onChange={handleFactorChange}
          rows={2}
          placeholder={t("Why this value is correct (at least 10 characters). The factor then waits for a different administrator to approve it.")}
          className="[resize:vertical]!"
        />
      </div>

      {/* Gas Stream Composition Trigger & Inputs */}
      {(() => {
        const gc = factorForm.gas_composition;
        const molSum = gc ? (
          (Number(gc.ch4_mol_pct) || 0) +
          (Number(gc.c2h6_mol_pct) || 0) +
          (Number(gc.c3h8_mol_pct) || 0) +
          (Number(gc.ic4_mol_pct) || 0) +
          (Number(gc.nc4_mol_pct) || 0) +
          (Number(gc.ic5_mol_pct) || 0) +
          (Number(gc.nc5_mol_pct) || 0) +
          (Number(gc.c6_plus_mol_pct) || 0) +
          (Number(gc.co2_mol_pct) || 0) +
          (Number(gc.n2_mol_pct) || 0)
        ) : 0;

        const handleNormalize = () => {
          if (!gc || molSum <= 0) return;
          const factor = 100.0 / molSum;
          const round3 = (v: any) => Number(((Number(v) || 0) * factor).toFixed(3));
          setFactorForm((prev: any) => ({
            ...prev,
            gas_composition: {
              ...prev.gas_composition,
              ch4_mol_pct: round3(prev.gas_composition?.ch4_mol_pct),
              c2h6_mol_pct: round3(prev.gas_composition?.c2h6_mol_pct),
              c3h8_mol_pct: round3(prev.gas_composition?.c3h8_mol_pct),
              ic4_mol_pct: round3(prev.gas_composition?.ic4_mol_pct),
              nc4_mol_pct: round3(prev.gas_composition?.nc4_mol_pct),
              ic5_mol_pct: round3(prev.gas_composition?.ic5_mol_pct),
              nc5_mol_pct: round3(prev.gas_composition?.nc5_mol_pct),
              c6_plus_mol_pct: round3(prev.gas_composition?.c6_plus_mol_pct),
              co2_mol_pct: round3(prev.gas_composition?.co2_mol_pct),
              n2_mol_pct: round3(prev.gas_composition?.n2_mol_pct),
            }
          }));
        };

        return (
          <div className="[grid-column:1/-1]! p-4 bg-orange-50/50 dark:bg-orange-950/20 rounded-xl border border-orange-200/90 dark:border-orange-800/50 shadow-xs">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-orange-700 dark:text-orange-400 uppercase tracking-wide">
                  {t("Gas Stream Composition (PVT / Chromatography)")}
                </span>
                {gc && (
                  <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-semibold ${
                    molSum >= 99.5 && molSum <= 100.5
                      ? "bg-green-100 text-green-800 border border-green-300"
                      : molSum === 0
                      ? "bg-slate-100 text-slate-600 border border-slate-300"
                      : "bg-amber-100 text-amber-800 border border-amber-300"
                  }`}>
                    {molSum >= 99.5 && molSum <= 100.5 ? `✓ ${molSum.toFixed(2)} mol%` : `Σ = ${molSum.toFixed(2)} mol%`}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {gc && molSum > 0 && Math.abs(molSum - 100) > 0.05 && (
                  <button
                    type="button"
                    onClick={handleNormalize}
                    className="text-xs px-2.5 py-1 bg-orange-600 hover:bg-orange-700 text-white rounded font-medium cursor-pointer transition-colors shadow-xs"
                    title={t("Scale all component percentages proportionally to 100.00%")}
                  >
                    {t("Normalize to 100%")}
                  </button>
                )}
                <button
                  type="button"
                  className="text-xs font-semibold text-orange-600 hover:text-orange-700 underline cursor-pointer"
                  onClick={() => {
                    const current = factorForm.gas_composition;
                    setFactorForm((prev: any) => ({
                      ...prev,
                      gas_composition: current ? null : {
                        ch4_mol_pct: 0, c2h6_mol_pct: 0, c3h8_mol_pct: 0,
                        ic4_mol_pct: 0, nc4_mol_pct: 0, ic5_mol_pct: 0,
                        nc5_mol_pct: 0, c6_plus_mol_pct: 0, co2_mol_pct: 0,
                        n2_mol_pct: 0, h2s_ppm: 0
                      }
                    }));
                  }}
                >
                  {factorForm.gas_composition ? t("Remove Gas Composition") : t("+ Add Gas Composition")}
                </button>
              </div>
            </div>

            {factorForm.gas_composition && (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-3">
                {PVT_COMPONENTS.map((c) => (
                  <div
                    key={c.key}
                    className="bg-white dark:bg-slate-800 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 shadow-xs flex flex-col justify-between hover:border-orange-400 transition-colors"
                  >
                    <div className="flex items-baseline justify-between gap-1 mb-1.5">
                      <div className="flex items-baseline gap-1.5 overflow-hidden">
                        <span className="font-bold text-sm text-slate-900 dark:text-slate-100">{c.label}</span>
                        <span className="text-[11px] text-slate-500 font-normal truncate">{c.shortName}</span>
                      </div>
                      <span className="text-[10px] font-semibold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded shrink-0">
                        {c.unit}
                      </span>
                    </div>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      value={factorForm.gas_composition[c.key] ?? ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        setFactorForm((prev: any) => ({
                          ...prev,
                          gas_composition: {
                            ...prev.gas_composition,
                            [c.key]: val === "" ? "" : parseFloat(val)
                          }
                        }));
                      }}
                      placeholder={c.placeholder}
                      className="w-full px-3 py-1.5 text-sm bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-md text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 font-mono"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })()}
    </div>

    {/* EF Uncertainty Workbench */}
    <div className="mt-6 p-5 bg-slate-50/80 dark:bg-slate-800/40 rounded-xl border border-slate-200/80 dark:border-slate-700/60 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h4 className="m-0 text-sm font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <Database size={16} className="text-blue-600" />
          {t("EF Uncertainty Workbench (ISO 14064-1 method)")}
        </h4>
        <span className="text-xs text-slate-500">Root Sum of Squares (SRSS) Combination</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
            {t("Meter Precision (±%)")}
          </label>
          <Input
            type="number"
            step="0.1"
            value={workbench.meter_precision}
            onChange={(e) =>
              setWorkbench({ ...workbench, meter_precision: parseFloat(e.target.value) || 0 })
            }
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
            {t("Lab Analysis (±%)")}
          </label>
          <Input
            type="number"
            step="0.1"
            value={workbench.lab_precision}
            onChange={(e) =>
              setWorkbench({ ...workbench, lab_precision: parseFloat(e.target.value) || 0 })
            }
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-1.5">
            {t("GWP Standard Selection")}
          </label>
          <NativeSelect
            className="component-select"
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
        type="button"
        className="mt-3 text-blue-600 hover:text-blue-700 font-semibold text-xs flex items-center gap-1.5 cursor-pointer"
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
        ⚡ {t("Calculate Combined Uncertainty (SRSS)")}
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
              justification: "",
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
                  {f.gas_composition && (
                    <div className="text-[10px] text-orange-600 font-mono mt-0.5">
                      GC: {f.gas_composition.ch4_mol_pct}% CH₄, {f.gas_composition.co2_mol_pct}% CO₂
                    </div>
                  )}
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
                  {/* a superuser or admin accepts a factor, never one they created (server enforces it too) */}
                  {(user?.role === "admin" || user?.role === "superuser") &&
                    f.status === "Pending" &&
                    (f.created_by == null || String(f.created_by) !== String(user?.id)) && (
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
