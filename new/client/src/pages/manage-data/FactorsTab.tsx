import React, { useState } from "react";
import { Button, Input, Textarea, Field, Sheet } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { Upload, Calculator, Check, Edit2, Archive, Trash2, Plus } from "lucide-react";
import PaginationControls from "./PaginationControls";
import AdvancedSection from "../../components/AdvancedSection";
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
  isSubmitting?: boolean;
  setCurrentPage: (page: number) => void;
  setEditingFactorId: (id: string | number | null) => void;
  setFactorForm: React.Dispatch<React.SetStateAction<any>>;
  setImportModal: (modal: { isOpen: boolean; type: string }) => void;
  setWorkbench: React.Dispatch<React.SetStateAction<any>>;
  workbench: FactorWorkbenchState;
}

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
  isSubmitting,
  setCurrentPage,
  setEditingFactorId,
  setFactorForm,
  setImportModal,
  setWorkbench,
  workbench,
}) => {
  const [isAddDrawerOpen, setIsAddDrawerOpen] = useState(false);

  const openAdd = () => {
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
    setIsAddDrawerOpen(true);
  };

  const openEdit = (factor: CustomFactorRecord) => {
    handleEditFactor(factor);
    setIsAddDrawerOpen(true);
  };

  const onSave = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    handleSaveFactor();
    setIsAddDrawerOpen(false);
  };

  const rows = filteredFactors.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  );

  return (
    <div className="manage-card glass-panel min-w-0">
      {/* Table-First Action Bar */}
      <div className="flex flex-wrap justify-between items-start gap-3 mb-6">
        <div className="min-w-0">
          <h2 className="mb-1 text-xl font-bold text-text">{t("Custom Emission Factors")}</h2>
          <p className="text-text-secondary m-0 text-sm">
            {t("Facility-specific Tier 2/3 emission factors, certified gas composition and uncertainty models.")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="primary" onClick={openAdd} className="gap-2">
            <Plus className="size-4" aria-hidden="true" />
            {t("+ Add Custom Factor")}
          </Button>
          <Button
            variant="secondary"
            className="gap-2 shrink-0"
            onClick={() => setImportModal({ isOpen: true, type: "custom_factors" })}
          >
            <Upload className="size-4" aria-hidden="true" />
            <span>{t("Bulk Import")}</span>
          </Button>
        </div>
      </div>

      {/* Table-First Presentation */}
      <div className="table-container" tabIndex={0} role="region" aria-label={t("Custom emission factors")}>
        <table className="data-table w-full">
          <thead>
            <tr>
              <th>{t("Factor Name")}</th>
              <th>{t("Unit")}</th>
              <th>CO₂</th>
              <th>CH₄</th>
              <th>N₂O</th>
              <th>{t("Certification / Description")}</th>
              <th>{t("CO₂ Unc.")}</th>
              <th>{t("CH₄ Unc.")}</th>
              <th>{t("N₂O Unc.")}</th>
              <th>{t("Status")}</th>
              <th>{t("Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => (
              <tr key={f.id}>
                <td>
                  <strong>{f.factor_name || f.name}</strong>
                  {f.gas_composition && (
                    <div className="text-xs text-brand-700 font-mono mt-0.5">
                      GC: {f.gas_composition.ch4_mol_pct}% CH₄, {f.gas_composition.co2_mol_pct}% CO₂
                    </div>
                  )}
                </td>
                <td>{f.unit}</td>
                <td>{f.co2_factor}</td>
                <td>{f.ch4_factor}</td>
                <td>{f.n2o_factor}</td>
                <td className="max-w-[240px]">
                  {f.source && (
                    <span className="inline-block text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-semibold mb-0.5">
                      {f.source}
                    </span>
                  )}
                  {f.description && (
                    <div
                      className="text-xs text-text-secondary overflow-hidden text-ellipsis whitespace-nowrap"
                      title={f.description}
                    >
                      {f.description}
                    </div>
                  )}
                </td>
                <td>{f.co2_uncertainty ? `±${f.co2_uncertainty}%` : "—"}</td>
                <td>{f.ch4_uncertainty ? `±${f.ch4_uncertainty}%` : "—"}</td>
                <td>{f.n2o_uncertainty ? `±${f.n2o_uncertainty}%` : "—"}</td>
                <td>
                  <span
                    className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${
                      f.status === "approved"
                        ? "bg-green-100 text-green-800"
                        : f.status === "archived"
                          ? "bg-ink-100 text-ink-600"
                          : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {f.status || t("Pending Review")}
                  </span>
                </td>
                <td>
                  <div className="flex gap-1 items-center">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => openEdit(f)}
                      className="gap-1 h-7 px-2 text-xs"
                      title={t("Edit")}
                    >
                      <Edit2 className="size-3" />
                      {t("Edit")}
                    </Button>
                    {user?.role && ["admin", "superuser"].includes(user.role) && f.status !== "approved" && handleApproveFactor && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleApproveFactor(f.id)}
                        className="gap-1 h-7 px-2 text-xs bg-green-50 text-green-700 hover:bg-green-100"
                        title={t("Approve Factor")}
                      >
                        <Check className="size-3" />
                      </Button>
                    )}
                    {f.status !== "archived" && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleArchiveFactor(f.id)}
                        className="gap-1 h-7 px-2 text-xs"
                        title={t("Archive")}
                      >
                        <Archive className="size-3" />
                      </Button>
                    )}
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleDeleteFactor(f.id)}
                      className="gap-1 h-7 px-2 text-xs"
                      title={t("Delete")}
                    >
                      <Trash2 className="size-3" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
            {filteredFactors.length === 0 && (
              <tr>
                <td colSpan={11} className="text-center p-10 text-text-secondary">
                  {t("No custom emission factors defined.")}
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

      {/* Side Drawer Form with Progressive Disclosure */}
      <Sheet
        open={isAddDrawerOpen}
        onOpenChange={setIsAddDrawerOpen}
        title={editingFactorId ? t("Edit Custom Emission Factor") : t("Add Custom Emission Factor")}
        description={t("Specify Tier 2/3 calibrated coefficients, gas composition, and uncertainty bounds.")}
        icon={Plus}
        width="44rem"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button
              variant="secondary"
              onClick={() => {
                setIsAddDrawerOpen(false);
                setEditingFactorId(null);
              }}
            >
              {t("Cancel")}
            </Button>
            <Button variant="primary" onClick={onSave} disabled={isSubmitting}>
              {editingFactorId ? t("Update Factor") : t("Save Factor")}
            </Button>
          </div>
        }
      >
        <form onSubmit={onSave} className="flex flex-col gap-5">
          {/* Essential Parameters */}
          <div className="flex flex-col gap-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 pb-1 border-b border-border/60">
              {t("Essential Factor Coefficients")}
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label={`${t("Factor Name")} *`}>
                <Input
                  type="text"
                  name="factor_name"
                  value={factorForm.factor_name || ""}
                  onChange={handleFactorChange}
                  placeholder={t("e.g. Flare High Efficiency")}
                  required
                />
              </Field>

              <Field label={t("Parent Fuel Reference")}>
                <NativeSelect
                  name="parent_fuel"
                  value={factorForm.parent_fuel || ""}
                  onChange={(e) => setFactorForm({ ...factorForm, parent_fuel: e.target.value })}
                >
                  <option value="">{t("Select Fuel Reference...")}</option>
                  <option value="Natural Gas">{t("Natural Gas (Standard)")}</option>
                  <option value="Diesel">{t("Diesel (Generic)")}</option>
                  <option value="Gasoline">{t("Gasoline (Generic)")}</option>
                  <option value="Propane">{t("Propane (Generic)")}</option>
                  <option value="Crude Oil">{t("Crude Oil (Heavy)")}</option>
                  <option value="Fuel Oil">{t("Fuel Oil (No. 4/6)")}</option>
                </NativeSelect>
              </Field>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
              <Field label={`${t("Unit")} *`}>
                <NativeSelect
                  name="unit"
                  value={factorForm.unit || "scf"}
                  onChange={handleFactorChange}
                >
                  <option value="scf">scf</option>
                  <option value="m3">m³</option>
                  <option value="mmbtu">MMBtu</option>
                  <option value="tonnes">{t("tonnes")}</option>
                  <option value="litres">{t("litres")}</option>
                  <option value="gallons">{t("gallons")}</option>
                  <option value="bbl">bbl</option>
                  <option value="boe">boe</option>
                  <option value="kwh">kWh</option>
                  <option value="mwh">MWh</option>
                </NativeSelect>
              </Field>

              <Field label={`${t("CO₂ Factor (kg/unit)")} *`}>
                <Input
                  type="number"
                  step="any"
                  name="co2_factor"
                  value={factorForm.co2_factor || ""}
                  onChange={handleFactorChange}
                  placeholder="0.0544"
                  required
                />
              </Field>

              <Field label={`${t("CH₄ Factor (kg/unit)")} *`}>
                <Input
                  type="number"
                  step="any"
                  name="ch4_factor"
                  value={factorForm.ch4_factor || ""}
                  onChange={handleFactorChange}
                  placeholder="0.0010"
                  required
                />
              </Field>

              <Field label={`${t("N₂O Factor (kg/unit)")} *`}>
                <Input
                  type="number"
                  step="any"
                  name="n2o_factor"
                  value={factorForm.n2o_factor || ""}
                  onChange={handleFactorChange}
                  placeholder="0.0001"
                  required
                />
              </Field>
            </div>
          </div>

          {/* Progressive Disclosure: Uncertainty Workbench */}
          <AdvancedSection
            id="factors-uncertainty"
            title={t("Uncertainty Workbench (SRSS Methodology)")}
            fieldCount={3}
            description={t("Calculate 95% confidence interval uncertainty using ISO 14064-1 root sum of squares.")}
          >
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Field label={t("Flow Meter Precision (±%)")}>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={workbench.meter_precision}
                    onChange={(e) =>
                      setWorkbench({ ...workbench, meter_precision: parseFloat(e.target.value) || 0 })
                    }
                  />
                </Field>
                <Field label={t("Lab Analysis Precision (±%)")}>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={workbench.lab_precision}
                    onChange={(e) =>
                      setWorkbench({ ...workbench, lab_precision: parseFloat(e.target.value) || 0 })
                    }
                  />
                </Field>
                <Field label={t("GWP Standard Uncertainty (±%)")}>
                  <Input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={workbench.gwp_uncertainty}
                    onChange={(e) =>
                      setWorkbench({ ...workbench, gwp_uncertainty: parseFloat(e.target.value) || 0 })
                    }
                  />
                </Field>
              </div>

              <div className="flex items-center justify-between gap-3 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    const gwpU = Number(workbench.gwp_uncertainty || 0);
                    const co2_u = Math.sqrt(
                      Math.pow(workbench.meter_precision, 2) + Math.pow(workbench.lab_precision, 2),
                    );
                    const ch4_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(50.0, 2) + Math.pow(gwpU, 2));
                    const n2o_u = Math.sqrt(Math.pow(workbench.meter_precision, 2) + Math.pow(150.0, 2) + Math.pow(gwpU, 2));

                    setFactorForm({
                      ...factorForm,
                      co2_uncertainty: co2_u.toFixed(2),
                      ch4_uncertainty: ch4_u.toFixed(2),
                      n2o_uncertainty: n2o_u.toFixed(2),
                    });
                  }}
                  className="gap-2"
                >
                  <Calculator className="size-4 text-brand-600" />
                  {t("Calculate Combined Uncertainty (SRSS)")}
                </Button>

                <div className="flex items-center gap-3 text-xs font-mono text-text-secondary">
                  <span>CO₂: ±{factorForm.co2_uncertainty || 0}%</span>
                  <span>CH₄: ±{factorForm.ch4_uncertainty || 0}%</span>
                  <span>N₂O: ±{factorForm.n2o_uncertainty || 0}%</span>
                </div>
              </div>
            </div>
          </AdvancedSection>

          {/* Progressive Disclosure: PVT Gas Composition */}
          <AdvancedSection
            id="factors-pvt"
            title={t("Gas Composition & PVT Analysis")}
            fieldCount={11}
            description={t("Gas chromatograph laboratory molar analysis (mol % and H₂S ppm).")}
          >
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {PVT_COMPONENTS.map((comp) => (
                <Field key={comp.key} label={`${comp.label} (${comp.unit})`}>
                  <Input
                    type="number"
                    step="0.01"
                    name={comp.key}
                    value={factorForm[comp.key] ?? ""}
                    onChange={handleFactorChange}
                    placeholder={comp.placeholder}
                  />
                </Field>
              ))}
            </div>
          </AdvancedSection>

          {/* Progressive Disclosure: Documentation */}
          <AdvancedSection
            id="factors-docs"
            title={t("Certification & Compliance Documentation")}
            fieldCount={2}
            description={t("Third-party verification reference, ISO 17025 certificate ID and justification notes.")}
          >
            <div className="flex flex-col gap-4">
              <Field label={t("Data Source / Certificate Ref")}>
                <Input
                  type="text"
                  name="source"
                  value={factorForm.source || ""}
                  onChange={handleFactorChange}
                  placeholder={t("e.g. Lab Report LAB-2026-0881 / ISO 17025")}
                />
              </Field>

              <Field label={t("Justification & Technical Notes")}>
                <Textarea
                  name="description"
                  value={factorForm.description || ""}
                  onChange={handleFactorChange}
                  placeholder={t("Explain measurement methodology, sampling frequency, and compliance notes...")}
                  rows={3}
                />
              </Field>
            </div>
          </AdvancedSection>
        </form>
      </Sheet>
    </div>
  );
};

export default FactorsTab;
