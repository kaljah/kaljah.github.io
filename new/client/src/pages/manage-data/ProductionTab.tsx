import React from "react";
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from "../../components/CustomDropdown";
import { Upload } from "lucide-react";
import PaginationControls from "./PaginationControls";
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
  isPrivileged: boolean;
  openGasConverter: () => void;
  openOilConverter: () => void;
  prodForm: Record<string, any>;
  productionData: ProductionRecord[];
  setCurrentPage: (page: number) => void;
  setImportModal: (modal: { isOpen: boolean; type: string }) => void;
  setProdForm: React.Dispatch<React.SetStateAction<any>>;
}

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
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
  isPrivileged,
  openGasConverter,
  openOilConverter,
  prodForm,
  productionData,
  setCurrentPage,
  setImportModal,
  setProdForm,
}) => (
  <div className="manage-card glass-panel">
    <div className="flex! justify-between! items-start! mb-[32px]!">
      <div>
        <h2 className="mb-[8px]! font-bold!">{t("Annual Production Records")}</h2>
        <p className="text-[color:var(--text-secondary)]! m-[0px]!">
          {t("Manage annual production data for emission intensity reporting.")}
        </p>
      </div>
      <button
        className="action-btn [display:flex]! [align-items:center]! [gap:8px]! [padding:8px_16px]! [font-size:0.9rem]! [width:auto]!"
        onClick={() => setImportModal({ isOpen: true, type: "production" })}
       
      >
        <Upload size={16} />{" "}{t("Bulk Import (CSV)")}
      </button>
    </div>

    <div className="grid-forms md:[grid-template-columns:repeat(3,1fr)]!">
      <Field
        className="input-group"
        label={
          <>
            {t("Activity")}
            {!isPrivileged && getAvailableActivities().length === 1 && (
              <span className="text-[length:0.65rem]! bg-[color:var(--color-legacy-dbeafe)]! text-[color:var(--color-blue-700)]! rounded-[4px]! p-[1px_5px]! font-semibold!">
                {t("Auto")}
              </span>
            )}
          </>
        }
      >
        <NativeSelect
          value={prodForm.activity || ""}
          onChange={(e) =>
            setProdForm({ ...prodForm, activity: e.target.value, division: "", facility_id: "" })
          }
          className="component-select"
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
        className="input-group"
        label={
          <>
            {t("Division")}
            {!isPrivileged && getAvailableDivisions(prodForm.activity).length === 1 && (
              <span className="text-[length:0.65rem]! bg-[color:var(--color-legacy-dbeafe)]! text-[color:var(--color-blue-700)]! rounded-[4px]! p-[1px_5px]! font-semibold!">
                {t("Auto")}
              </span>
            )}
          </>
        }
      >
        <NativeSelect
          value={prodForm.division || ""}
          onChange={(e) =>
            setProdForm({ ...prodForm, division: e.target.value, facility_id: "" })
          }
          className="component-select"
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

      <div className="input-group">
        <label className="flex! items-center! gap-[6px]!">
          {t("Region")}
          {!isPrivileged &&
            facilities.filter((f) => f.activity === prodForm.activity && f.division === prodForm.division).length === 1 && (
              <span className="text-[length:0.65rem]! bg-[color:var(--color-legacy-dbeafe)]! text-[color:var(--color-blue-700)]! rounded-[4px]! p-[1px_5px]! font-semibold!">
                {t("Auto")}
              </span>
            )}
        </label>
        <CustomDropdown
          options={[
            { value: "", label: t("Select Region") },
            ...facilities
              .filter((f) => f.activity === prodForm.activity && f.division === prodForm.division)
              .map((f) => ({ value: f.id.toString(), label: f.name, subLabel: f.field })),
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
      </div>

      <Field className="input-group" label={t("Month")}>
        <NativeSelect
          value={prodForm.month || 1}
          onChange={(e) => setProdForm({ ...prodForm, month: parseInt(e.target.value, 10) })}
          className="component-select"
        >
          {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
            <option key={m} value={m}>
              {new Date(2000, m - 1).toLocaleString("default", { month: "long" })}
            </option>
          ))}
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Year")}>
        <Input
          type="number"
          value={prodForm.year || ""}
          onChange={(e) => setProdForm({ ...prodForm, year: e.target.value })}
        />
      </Field>

      <div className="input-group">
        {/* The converter button sits beside the label, not inside it (a label may only hold its own control). */}
        <div className="mb-2 flex items-center gap-2">
          <label htmlFor="prod-oil-amount" className="m-0!">
            {t("Oil (")}{prodForm.oil_unit || t("bbl")})
          </label>
          <button
            type="button"
            onClick={openOilConverter}
            className="cursor-pointer rounded-sm border-0 bg-brand-700 px-1.5 py-0.5 text-xs font-semibold text-white hover:bg-brand-800"
          >
            {t("Convert m³")}
          </button>
        </div>
        <div className="flex! gap-[8px]!">
          <input
            id="prod-oil-amount"
            type="number"
            value={prodForm.oil_amount || ""}
            onChange={(e) => setProdForm({ ...prodForm, oil_amount: e.target.value })}
            className="mole-input flex-1!"
            placeholder="0.0"
          />
          <NativeSelect
            value={prodForm.oil_unit || "bbl"}
            onChange={(e) => setProdForm({ ...prodForm, oil_unit: e.target.value })}
            aria-label={t("Oil unit")}
            className="component-select w-[80px]!"
          >
            <option value="bbl">{t("bbl")}</option>
            <option value="m³">m³</option>
          </NativeSelect>
        </div>
      </div>

      <div className="input-group">
        {/* The converter button sits beside the label, not inside it (a label may only hold its own control). */}
        <div className="mb-2 flex items-center gap-2">
          <label htmlFor="prod-gas-amount" className="m-0!">
            {t("Gas (")}{prodForm.gas_unit || t("mscf")})
          </label>
          <button
            type="button"
            onClick={openGasConverter}
            className="cursor-pointer rounded-sm border-0 bg-brand-700 px-1.5 py-0.5 text-xs font-semibold text-white hover:bg-brand-800"
          >
            {t("Convert m³")}
          </button>
        </div>
        <div className="flex! gap-[8px]!">
          <input
            id="prod-gas-amount"
            type="number"
            value={prodForm.gas_amount || ""}
            onChange={(e) => setProdForm({ ...prodForm, gas_amount: e.target.value })}
            className="mole-input flex-1!"
            placeholder="0.0"
          />
          <NativeSelect
            value={prodForm.gas_unit || "mscf"}
            onChange={(e) => setProdForm({ ...prodForm, gas_unit: e.target.value })}
            aria-label={t("Gas unit")}
            className="component-select w-[80px]!"
          >
            <option value="mscf">{t("mscf")}</option>
            <option value="m³">m³</option>
          </NativeSelect>
        </div>
      </div>

      <Field className="input-group" label={t("Gross Gas (MMSm³)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.gross_gas_mmsm3 || ""}
          onChange={(e) => setProdForm({ ...prodForm, gross_gas_mmsm3: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("Gas w/o Injection (MMSm³)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.gas_without_injected_mmsm3 || ""}
          onChange={(e) => setProdForm({ ...prodForm, gas_without_injected_mmsm3: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("Injected Gas (MMSm³)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.injected_gas_mmsm3 || ""}
          onChange={(e) => setProdForm({ ...prodForm, injected_gas_mmsm3: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("Crude Oil (MMBOE)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.crude_oil_mmboe || ""}
          onChange={(e) => setProdForm({ ...prodForm, crude_oil_mmboe: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("Condensate (MMBOE)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.condensate_mmboe || ""}
          onChange={(e) => setProdForm({ ...prodForm, condensate_mmboe: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("LPG (MMBOE)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.lpg_mmboe || ""}
          onChange={(e) => setProdForm({ ...prodForm, lpg_mmboe: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("Total Production (MMBOE)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.total_production_mmboe || ""}
          onChange={(e) => setProdForm({ ...prodForm, total_production_mmboe: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("Total Saleable (MMBOE)")}>
        <Input
          type="number"
          step="any"
          value={prodForm.saleable_production_mmboe || ""}
          onChange={(e) => setProdForm({ ...prodForm, saleable_production_mmboe: e.target.value })}
          placeholder="0.0"
        />
      </Field>
    </div>

    <div className="flex! gap-[12px]! mt-[20px]!">
      <button className="action-btn" onClick={handleSaveProduction}>
        {t("Save Record")}
      </button>
    </div>
    <div className="flex! gap-[12px]! mt-[10px]!">
      <button
        className="action-btn bg-[color:var(--text-secondary)]!"
        onClick={() => exportToCSV(productionData, "production_data.csv")}
      >
        {t("Export CSV")}
      </button>
    </div>

    <div className="table-container mt-[40px]!" tabIndex={0} role="region" aria-label={t("Production records")}>
      <table className="data-table">
        <thead>
          <tr>
            <th>{t("Activity")}</th>
            <th>{t("Division")}</th>
            <th>{t("Region")}</th>
            <th>{t("Year")}</th>
            <th>{t("Month")}</th>
            <th className="text-right!">{t("Oil (bbl)")}</th>
            <th className="text-right!">{t("Gas (mcf)")}</th>
            <th className="text-right!">{t("Gross Gas (MMSm³)")}</th>
            <th className="text-right!">{t("Total (MMBOE)")}</th>
            <th className="text-right!">{t("Saleable (MMBOE)")}</th>
            <th className="text-center!">{t("Actions")}</th>
          </tr>
        </thead>
        <tbody>
          {filteredProduction
            .slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)
            .map((d) => (
              <tr key={d.id}>
                <td>{ACTIVITY_LABELS[d.activity || ""] || d.activity || "-"}</td>
                <td>{d.division || "-"}</td>
                <td>
                  {(() => {
                    const fac = facilities.find((f) => f.id === d.facilityId);
                    if (!fac) return d.facilityId;
                    return (
                      <>
                        {fac.name}
                        {fac.field && (
                          <span className="text-[length:0.85em]! text-[color:var(--color-legacy-9ca3af)]! font-normal!">
                            -{fac.field}
                          </span>
                        )}
                      </>
                    );
                  })()}
                </td>
                <td>{d.year}</td>
                <td>
                  {d.month
                    ? new Date(2000, d.month - 1).toLocaleString("default", { month: "short" })
                    : "-"}
                </td>
                <td className="text-right!">
                  {(d.oil || 0).toLocaleString()} {d.oilUnit || t("bbl")}
                </td>
                <td className="text-right!">
                  {(d.gas || 0).toLocaleString()} {d.gasUnit || t("mscf")}
                </td>
                <td className="text-right!">
                  {d.gross_gas_mmsm3 != null
                    ? Number(d.gross_gas_mmsm3).toLocaleString(undefined, { minimumFractionDigits: 2 })
                    : "-"}
                </td>
                <td className="text-right!">
                  {d.total_production_mmboe != null
                    ? Number(d.total_production_mmboe).toLocaleString(undefined, { minimumFractionDigits: 2 })
                    : "-"}
                </td>
                <td className="text-right!">
                  {d.saleable_production_mmboe != null
                    ? Number(d.saleable_production_mmboe).toLocaleString(undefined, { minimumFractionDigits: 2 })
                    : "-"}
                </td>
                <td className="text-center!">
                  <button
                    className="[background:var(--color-legacy-fee2e2)] [color:var(--color-red-700)] [border:1px_solid_var(--color-legacy-fecaca)] [&&]:[border-radius:var(--radius-md)] [cursor:pointer] [transition:all_0.2s] hover:[background:var(--color-red-700)] hover:[color:white] p-[6px_12px]! text-[length:0.8rem]!"
                    onClick={() => handleDeleteProduction(d.id)}
                  >
                    {t("Delete")}
                  </button>
                </td>
              </tr>
            ))}
          {filteredProduction.length === 0 && (
            <tr>
              <td colSpan={11} className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
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
  </div>
);

export default ProductionTab;
