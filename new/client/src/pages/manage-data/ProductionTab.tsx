import React, { useState } from "react";
import { Button, Input, Field, Sheet } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from "../../components/CustomDropdown";
import { Upload, Plus, Download, Calculator, Trash2 } from "lucide-react";
import PaginationControls from "./PaginationControls";
import AdvancedSection from "../../components/AdvancedSection";
import { t } from "../../i18n";

export interface ProductionRecord {
  id: string | number;
  activity?: string;
  division?: string;
  facilityId?: string | number;
  year?: number | string;
  month?: number;
  oil?: number;
  oilUnit?: string;
  gas?: number;
  gasUnit?: string;
  gross_gas_mmsm3?: number | string;
  total_production_mmboe?: number | string;
  saleable_production_mmboe?: number | string;
  [key: string]: any;
}

export interface ProductionTabProps {
  ACTIVITY_LABELS: Record<string, string>;
  ITEMS_PER_PAGE: number;
  currentPage: number;
  exportToCSV: (data: any[], filename: string) => void;
  facilities: Array<{
    id: string | number;
    name: string;
    field?: string;
    activity?: string;
    division?: string;
    [key: string]: any;
  }>;
  filteredProduction: ProductionRecord[];
  getAvailableActivities: () => string[];
  getAvailableDivisions: (activity?: string) => string[];
  handleDeleteProduction: (id: string | number) => void;
  handleSaveProduction: () => void;
  isSubmitting?: boolean;
  isPrivileged: boolean;
  openGasConverter: () => void;
  openOilConverter: () => void;
  prodForm: Record<string, any>;
  productionData: ProductionRecord[];
  setCurrentPage: (page: number) => void;
  setImportModal: (modal: { isOpen: boolean; type: string }) => void;
  setProdForm: React.Dispatch<React.SetStateAction<any>>;
}

const ProductionTab: React.FC<ProductionTabProps> = ({
  ACTIVITY_LABELS,
  ITEMS_PER_PAGE,
  currentPage,
  exportToCSV,
  facilities,
  filteredProduction,
  getAvailableActivities,
  getAvailableDivisions,
  handleDeleteProduction,
  handleSaveProduction,
  isSubmitting,
  isPrivileged,
  openGasConverter,
  openOilConverter,
  prodForm,
  productionData,
  setCurrentPage,
  setImportModal,
  setProdForm,
}) => {
  const [isAddDrawerOpen, setIsAddDrawerOpen] = useState(false);

  const onSave = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    handleSaveProduction();
    setIsAddDrawerOpen(false);
  };

  const rows = filteredProduction.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  );

  return (
    <div className="manage-card glass-panel min-w-0">
      {/* Header with Table-First Action Bar */}
      <div className="flex flex-wrap justify-between items-start gap-3 mb-6">
        <div>
          <h2 className="mb-1 text-xl font-bold text-text">{t("Production Data Inventory")}</h2>
          <p className="text-text-secondary m-0 text-sm">
            {t("Manage annual hydrocarbon production data used for carbon intensity and flaring benchmark KPIs.")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            onClick={() => setIsAddDrawerOpen(true)}
            className="gap-2"
          >
            <Plus className="size-4" aria-hidden="true" />
            {t("+ Add Production Record")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setImportModal({ isOpen: true, type: "production" })}
            className="gap-2"
          >
            <Upload className="size-4" aria-hidden="true" />
            {t("Bulk Import")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => exportToCSV(productionData, "production_data.csv")}
            className="gap-2"
          >
            <Download className="size-4" aria-hidden="true" />
            {t("Export CSV")}
          </Button>
        </div>
      </div>

      {/* Table-First View */}
      <div className="table-container" tabIndex={0} role="region" aria-label={t("Production data records")}>
        <table className="data-table w-full">
          <thead>
            <tr>
              <th>{t("Region")}</th>
              <th>{t("Year")}</th>
              <th>{t("Month")}</th>
              <th>{t("Oil Production")}</th>
              <th>{t("Gas Production")}</th>
              <th>{t("Total (MMBOE)")}</th>
              <th>{t("Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <td>
                  {(() => {
                    const fac = facilities.find((f) => f.id === p.facilityId);
                    if (!fac) return p.facilityId;
                    return (
                      <>
                        <strong>{fac.name}</strong>
                        {fac.field && (
                          <span className="text-xs text-ink-400 font-normal ml-1">
                            -{fac.field}
                          </span>
                        )}
                      </>
                    );
                  })()}
                </td>
                <td>
                  <strong>{p.year}</strong>
                </td>
                <td>{p.month ? t("Month {{m}}", { m: p.month }) : t("Annual")}</td>
                <td>
                  {p.oil != null
                    ? `${Number(p.oil).toLocaleString()} ${p.oilUnit || "bbl"}`
                    : "—"}
                </td>
                <td>
                  {p.gas != null
                    ? `${Number(p.gas).toLocaleString()} ${p.gasUnit || "mscf"}`
                    : "—"}
                </td>
                <td>
                  {p.total_production_mmboe != null
                    ? `${Number(p.total_production_mmboe).toFixed(3)} MMBOE`
                    : "—"}
                </td>
                <td>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDeleteProduction(p.id)}
                    className="gap-1 h-7 px-2 text-xs"
                  >
                    <Trash2 className="size-3" />
                    {t("Delete")}
                  </Button>
                </td>
              </tr>
            ))}
            {filteredProduction.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center p-10 text-text-secondary">
                  {t("No production records found.")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <PaginationControls
          currentPage={currentPage}
          totalItems={filteredProduction.length}
          itemsPerPage={ITEMS_PER_PAGE}
          onPageChange={setCurrentPage}
        />
      </div>

      {/* Side Drawer Form with Progressive Disclosure */}
      <Sheet
        open={isAddDrawerOpen}
        onOpenChange={setIsAddDrawerOpen}
        title={t("Add Production Record")}
        description={t("Log operational hydrocarbon throughput for intensity baselining.")}
        icon={Plus}
        width="38rem"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="secondary" onClick={() => setIsAddDrawerOpen(false)}>
              {t("Cancel")}
            </Button>
            <Button variant="primary" onClick={onSave} disabled={isSubmitting}>
              {t("Save Production Record")}
            </Button>
          </div>
        }
      >
        <form onSubmit={onSave} className="flex flex-col gap-5">
          {/* Essential Location & Date Parameters */}
          <div className="flex flex-col gap-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 pb-1 border-b border-border/60">
              {t("Essential Facility & Timing")}
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field
                label={
                  <span className="inline-flex items-center gap-1.5">
                    {t("Activity")} *
                    {!isPrivileged && getAvailableActivities().length === 1 && (
                      <span className="rounded bg-blue-100 px-1.5 py-0 text-[0.65rem] font-bold text-blue-700">
                        {t("Auto")}
                      </span>
                    )}
                  </span>
                }
              >
                <NativeSelect
                  value={prodForm.activity || ""}
                  onChange={(e) =>
                    setProdForm({ ...prodForm, activity: e.target.value, division: "", facility_id: "" })
                  }
                  disabled={!isPrivileged && getAvailableActivities().length === 1}
                >
                  <option value="">{t("Select Activity")}</option>
                  {getAvailableActivities().map((a) => (
                    <option key={a} value={a}>
                      {ACTIVITY_LABELS[a] || a}
                    </option>
                  ))}
                </NativeSelect>
              </Field>

              <Field
                label={
                  <span className="inline-flex items-center gap-1.5">
                    {t("Division")}
                    {!isPrivileged && getAvailableDivisions(prodForm.activity).length === 1 && (
                      <span className="rounded bg-blue-100 px-1.5 py-0 text-[0.65rem] font-bold text-blue-700">
                        {t("Auto")}
                      </span>
                    )}
                  </span>
                }
              >
                <NativeSelect
                  value={prodForm.division || ""}
                  onChange={(e) =>
                    setProdForm({ ...prodForm, division: e.target.value, facility_id: "" })
                  }
                  disabled={!prodForm.activity || (!isPrivileged && getAvailableDivisions(prodForm.activity).length === 1)}
                >
                  <option value="">{t("Select Division")}</option>
                  {getAvailableDivisions(prodForm.activity).map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
            </div>

            <Field
              label={
                <span className="inline-flex items-center gap-1.5">
                  {t("Region")} *
                  {!isPrivileged &&
                    facilities.filter((f) => f.activity === prodForm.activity && f.division === prodForm.division).length === 1 && (
                      <span className="rounded bg-blue-100 px-1.5 py-0 text-[0.65rem] font-bold text-blue-700">
                        {t("Auto")}
                      </span>
                    )}
                </span>
              }
            >
              <CustomDropdown
                options={[
                  { value: "", label: t("Select Region") },
                  ...facilities
                    .filter((f) => f.activity === prodForm.activity && f.division === prodForm.division)
                    .map((f) => ({ value: f.id.toString(), label: f.name, subLabel: f.region || f.field })),
                ]}
                value={prodForm.facility_id != null ? String(prodForm.facility_id) : ""}
                onChange={(val) => setProdForm({ ...prodForm, facility_id: val })}
                placeholder={t("Select Region")}
                disabled={
                  !prodForm.division ||
                  (!isPrivileged &&
                    facilities.filter((f) => f.activity === prodForm.activity && f.division === prodForm.division).length === 1)
                }
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label={`${t("Reporting Year")} *`}>
                <Input
                  type="number"
                  value={prodForm.year || ""}
                  onChange={(e) => setProdForm({ ...prodForm, year: e.target.value })}
                  placeholder={new Date().getFullYear().toString()}
                  required
                />
              </Field>

              <Field label={t("Month (Optional)")}>
                <NativeSelect
                  value={prodForm.month || ""}
                  onChange={(e) => setProdForm({ ...prodForm, month: e.target.value })}
                >
                  <option value="">{t("Annual / Whole Year")}</option>
                  {Array.from({ length: 12 }, (_, i) => (
                    <option key={i + 1} value={i + 1}>
                      {t("Month {{m}}", { m: i + 1 })}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
            </div>

            {/* Essential Production Quantities */}
            <div className="flex flex-col gap-4 mt-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 pb-1 border-b border-border/60">
                {t("Hydrocarbon Volumes")}
              </h4>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-sm font-medium text-text">{t("Crude Oil / Liquids")}</span>
                  <button
                    type="button"
                    onClick={openOilConverter}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:text-brand-800 bg-transparent border-0 cursor-pointer"
                  >
                    <Calculator className="size-3" />
                    {t("Convert m³ / tonnes")}
                  </button>
                </div>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.oil_amount || ""}
                    onChange={(e) => setProdForm({ ...prodForm, oil_amount: e.target.value })}
                    className="flex-1"
                    placeholder="0.0"
                  />
                  <NativeSelect
                    value={prodForm.oil_unit || "bbl"}
                    onChange={(e) => setProdForm({ ...prodForm, oil_unit: e.target.value })}
                    wrapperClassName="w-28 shrink-0"
                  >
                    <option value="bbl">{t("bbl")}</option>
                    <option value="m³">m³</option>
                  </NativeSelect>
                </div>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="text-sm font-medium text-text">{t("Gas Production")}</span>
                  <button
                    type="button"
                    onClick={openGasConverter}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:text-brand-800 bg-transparent border-0 cursor-pointer"
                  >
                    <Calculator className="size-3" />
                    {t("Convert m³ to mscf")}
                  </button>
                </div>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.gas_amount || ""}
                    onChange={(e) => setProdForm({ ...prodForm, gas_amount: e.target.value })}
                    className="flex-1"
                    placeholder="0.0"
                  />
                  <NativeSelect
                    value={prodForm.gas_unit || "mscf"}
                    onChange={(e) => setProdForm({ ...prodForm, gas_unit: e.target.value })}
                    wrapperClassName="w-28 shrink-0"
                  >
                    <option value="mscf">{t("mscf")}</option>
                    <option value="m³">m³</option>
                  </NativeSelect>
                </div>
              </div>
            </div>
          </div>

          {/* Progressive Disclosure: MMBOE & Specialized Gas Deliverability */}
          <AdvancedSection
            id="production-advanced"
            title={t("Field Deliverability & MMBOE Accounting")}
            fieldCount={7}
            description={t("Gross gas deliverability, re-injection volumes, and barrel of oil equivalent totals.")}
          >
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <Field label={t("Gross Gas (MMSm³)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.gross_gas_mmsm3 || ""}
                    onChange={(e) => setProdForm({ ...prodForm, gross_gas_mmsm3: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
                <Field label={t("Gas w/o Injection (MMSm³)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.gas_without_injected_mmsm3 || ""}
                    onChange={(e) => setProdForm({ ...prodForm, gas_without_injected_mmsm3: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
                <Field label={t("Injected Gas (MMSm³)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.injected_gas_mmsm3 || ""}
                    onChange={(e) => setProdForm({ ...prodForm, injected_gas_mmsm3: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <Field label={t("Crude Oil (MMBOE)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.crude_oil_mmboe || ""}
                    onChange={(e) => setProdForm({ ...prodForm, crude_oil_mmboe: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
                <Field label={t("Condensate (MMBOE)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.condensate_mmboe || ""}
                    onChange={(e) => setProdForm({ ...prodForm, condensate_mmboe: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
                <Field label={t("LPG (MMBOE)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.lpg_mmboe || ""}
                    onChange={(e) => setProdForm({ ...prodForm, lpg_mmboe: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
                <Field label={t("Gas (MMBOE)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.gas_mmboe || ""}
                    onChange={(e) => setProdForm({ ...prodForm, gas_mmboe: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <Field label={t("Total Production (MMBOE)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.total_production_mmboe || ""}
                    onChange={(e) => setProdForm({ ...prodForm, total_production_mmboe: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
                <Field label={t("Saleable Production (MMBOE)")}>
                  <Input
                    type="number"
                    step="any"
                    value={prodForm.saleable_production_mmboe || ""}
                    onChange={(e) => setProdForm({ ...prodForm, saleable_production_mmboe: e.target.value })}
                    placeholder="0.0"
                  />
                </Field>
              </div>
            </div>
          </AdvancedSection>
        </form>
      </Sheet>
    </div>
  );
};

export default ProductionTab;
