import React from "react";
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import PaginationControls from "./PaginationControls";
import { t } from "../../i18n";

export interface CbamRecord {
  id: string | number;
  facility_id?: string | number;
  facilityId?: string | number;
  facility_name?: string;
  facilityName?: string;
  product_name?: string;
  productName?: string;
  cn_code?: string;
  cnCode?: string;
  year?: number | string;
  month?: number | string;
  export_destination?: string;
  exportDestination?: string;
  quantity_tonnes?: number | string;
  quantityTonnes?: number | string;
  specific_embedded_direct?: number | string;
  specificEmbeddedDirect?: number | string;
  specific_embedded_indirect?: number | string;
  specificEmbeddedIndirect?: number | string;
  notes?: string;
  [key: string]: any;
}

export interface CbamTabProps {
  ACTIVITY_LABELS: Record<string, string>;
  ITEMS_PER_PAGE: number;
  cbamForm: Record<string, any>;
  currentPage: number;
  editingCbamId: string | number | null;
  facilities: Array<{
    id: string | number;
    name: string;
    field?: string;
    location?: string;
    activity?: string;
    division?: string;
    [key: string]: any;
  }>;
  filteredCbam: CbamRecord[];
  getAvailableActivities: () => string[];
  getAvailableDivisions: (activity?: string) => string[];
  handleDeleteCbamExport: (id: string | number) => void;
  handleSaveCbamExport: () => void;
  setCbamForm: React.Dispatch<React.SetStateAction<any>>;
  setCurrentPage: (page: number) => void;
  setEditingCbamId: (id: string | number | null) => void;
}

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const CbamTab: React.FC<CbamTabProps> = ({
  ACTIVITY_LABELS,
  ITEMS_PER_PAGE,
  cbamForm,
  currentPage,
  editingCbamId,
  facilities,
  filteredCbam,
  getAvailableActivities,
  getAvailableDivisions,
  handleDeleteCbamExport,
  handleSaveCbamExport,
  setCbamForm,
  setCurrentPage,
  setEditingCbamId,
}) => (
  <div className="tab-pane active">
    <div className="section-header mb-[24px]!">
      <h2>{t("EU CBAM Export & Embedded Emission Tracking")}</h2>
      <p className="text-[color:var(--text-secondary)]! mt-[4px]!">
        {t("Record product exports subject to EU Carbon Border Adjustment Mechanism (CBAM) with direct and indirect embedded emissions under EU Regulation (EU) 2023/956.")}
      </p>
    </div>

    <div className="form-grid-3">
      <Field className="input-group" label={t("Activity")}>
        <NativeSelect
          value={cbamForm.activity || ""}
          onChange={(e) => {
            const act = e.target.value;
            const divs = getAvailableDivisions(act);
            const autoDiv = divs.length === 1 ? divs[0] : "";
            const facs = facilities.filter(
              (f) => (!act || f.activity === act) && (!autoDiv || f.division === autoDiv),
            );
            const autoFac = facs.length === 1 ? facs[0].id.toString() : "";
            setCbamForm({ ...cbamForm, activity: act, division: autoDiv, facility_id: autoFac });
          }}
          className="component-select"
        >
          <option value="">{t("-- Select Activity --")}</option>
          {getAvailableActivities().map((a) => (
            <option key={a} value={a}>
              {ACTIVITY_LABELS[a] || a}
            </option>
          ))}
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Division")}>
        <NativeSelect
          value={cbamForm.division || ""}
          onChange={(e) => {
            const div = e.target.value;
            const facs = facilities.filter(
              (f) => (!cbamForm.activity || f.activity === cbamForm.activity) && (!div || f.division === div),
            );
            const autoFac = facs.length === 1 ? facs[0].id.toString() : "";
            setCbamForm({ ...cbamForm, division: div, facility_id: autoFac });
          }}
          className="component-select"
          disabled={!cbamForm.activity}
        >
          <option value="">{t("-- Select Division --")}</option>
          {getAvailableDivisions(cbamForm.activity).map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Facility / Region *")}>
        <NativeSelect
          value={cbamForm.facility_id || ""}
          onChange={(e) => setCbamForm({ ...cbamForm, facility_id: e.target.value })}
          className="component-select"
        >
          <option value="">{t("-- Select Facility --")}</option>
          {facilities
            .filter(
              (f) =>
                (!cbamForm.activity || f.activity === cbamForm.activity) &&
                (!cbamForm.division || f.division === cbamForm.division),
            )
            .map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.location || f.field || t("General")})
              </option>
            ))}
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Product Name *")}>
        <Input
          type="text"
          value={cbamForm.product_name || ""}
          onChange={(e) => setCbamForm({ ...cbamForm, product_name: e.target.value })}
          placeholder={t("e.g. Export Blend Crude Oil")}
        />
      </Field>

      <Field className="input-group" label={t("EU CN Code *")}>
        <NativeSelect
          value={cbamForm.cn_code || "2709 00"}
          onChange={(e) => setCbamForm({ ...cbamForm, cn_code: e.target.value })}
          className="component-select"
        >
          <option value="2709 00">{t("2709 00 - Crude Petroleum Oil")}</option>
          <option value="2711 11">{t("2711 11 - Natural Gas (Liquefied / LNG)")}</option>
          <option value="2711 21">{t("2711 21 - Natural Gas (Gaseous / Pipeline)")}</option>
          <option value="2710 12">{t("2710 12 - Light Oils & Preparations")}</option>
          <option value="2710 19">{t("2710 19 - Heavy Oils / Diesel / Gas Oil")}</option>
          <option value="2814 10">{t("2814 10 - Anhydrous Ammonia")}</option>
          <option value="2901 21">{t("2901 21 - Ethylene / Petrochemicals")}</option>
          <option value="3102 10">{t("3102 10 - Urea & Nitrogenous Fertilizers")}</option>
          <option value="Custom">{t("Custom / Other CN Code")}</option>
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Export Destination")}>
        <NativeSelect
          value={cbamForm.export_destination || "EU"}
          onChange={(e) => setCbamForm({ ...cbamForm, export_destination: e.target.value })}
          className="component-select"
        >
          <option value="EU">{t("European Union (EU-27)")}</option>
          <option value="UK">{t("United Kingdom")}</option>
          <option value="US">{t("United States")}</option>
          <option value="APAC">{t("Asia-Pacific")}</option>
          <option value="Non-EU">{t("Other Non-EU")}</option>
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Reporting Year")}>
        <Input
          type="number"
          value={cbamForm.year || ""}
          onChange={(e) => setCbamForm({ ...cbamForm, year: e.target.value })}
        />
      </Field>

      <Field className="input-group" label={t("Reporting Month")}>
        <NativeSelect
          value={cbamForm.month || 1}
          onChange={(e) => setCbamForm({ ...cbamForm, month: e.target.value })}
          className="component-select"
        >
          {Array.from({ length: 12 }, (_, i) => (
            <option key={i + 1} value={i + 1}>
              {new Date(2000, i).toLocaleString("default", { month: "long" })}
            </option>
          ))}
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Export Quantity (Metric Tonnes) *")}>
        <Input
          type="number"
          value={cbamForm.quantity_tonnes || ""}
          onChange={(e) => setCbamForm({ ...cbamForm, quantity_tonnes: e.target.value })}
          placeholder="0.00"
        />
      </Field>

      <Field className="input-group" label={t("Direct Specific Embedded (tCO₂e / t)")}>
        <Input
          type="number"
          step="0.001"
          value={cbamForm.specific_embedded_direct || ""}
          onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_direct: e.target.value })}
          placeholder="0.000"
        />
      </Field>

      <Field className="input-group" label={t("Indirect Specific Embedded (tCO₂e / t)")}>
        <Input
          type="number"
          step="0.001"
          value={cbamForm.specific_embedded_indirect || ""}
          onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_indirect: e.target.value })}
          placeholder="0.000"
        />
      </Field>

      <Field className="input-group" label={t("Notes & Verification References")}>
        <Input
          type="text"
          value={cbamForm.notes || ""}
          onChange={(e) => setCbamForm({ ...cbamForm, notes: e.target.value })}
          placeholder={t("Accredited Verifier / Certificate ID")}
        />
      </Field>
    </div>

    <div className="flex! gap-[12px]! mt-[20px]!">
      <button className="action-btn" onClick={handleSaveCbamExport}>
        {editingCbamId ? t("Update CBAM Record") : t("Save CBAM Record")}
      </button>
      {editingCbamId && (
        <button
          className="action-btn bg-[color:var(--text-secondary)]!"
          onClick={() => {
            setEditingCbamId(null);
            setCbamForm({
              id: null,
              activity: "",
              division: "",
              facility_id: "",
              year: new Date().getFullYear(),
              month: 1,
              product_name: "Crude Petroleum Oil",
              cn_code: "2709 00",
              quantity_tonnes: "",
              export_destination: "EU",
              specific_embedded_direct: "",
              specific_embedded_indirect: "",
              notes: "",
            });
          }}
        >
          {t("Cancel Edit")}
        </button>
      )}
    </div>

    <div className="table-container mt-[40px]!" tabIndex={0} role="region" aria-label={t("CBAM product export records")}>
      <div className="flex! justify-between! items-center! mb-[16px]!">
        <h3>{t("CBAM Product Export Records")}</h3>
        <span className="text-[length:0.85rem]! text-[color:var(--text-secondary)]!">
          {t("Total Records:")}{" "}{filteredCbam.length}
        </span>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th>{t("Facility")}</th>
            <th>{t("Product")}</th>
            <th>{t("EU CN Code")}</th>
            <th>{t("Period")}</th>
            <th>{t("Destination")}</th>
            <th className="text-right!">{t("Quantity (t)")}</th>
            <th className="text-right!">{t("Direct (tCO₂e/t)")}</th>
            <th className="text-right!">{t("Indirect (tCO₂e/t)")}</th>
            <th className="text-right!">{t("Total Embedded (tCO₂e)")}</th>
            <th className="text-center!">{t("Actions")}</th>
          </tr>
        </thead>
        <tbody>
          {filteredCbam
            .slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)
            .map((c) => {
              const fid = c.facility_id || c.facilityId;
              const fac = facilities.find((f) => f.id === fid);
              const fName = c.facility_name || c.facilityName || fac?.name || `Facility #${fid}`;
              const pName = c.product_name || c.productName || "Product";
              const cnCode = c.cn_code || c.cnCode || "-";
              const dest = c.export_destination || c.exportDestination || "EU";
              const qTonnes = parseFloat(String(c.quantity_tonnes ?? c.quantityTonnes ?? 0));
              const direct = parseFloat(String(c.specific_embedded_direct ?? c.specificEmbeddedDirect ?? 0));
              const indirect = parseFloat(String(c.specific_embedded_indirect ?? c.specificEmbeddedIndirect ?? 0));
              const totalEmbedded = (direct + indirect) * qTonnes;
              return (
                <tr key={c.id}>
                  <td>
                    <strong>{fName}</strong>
                  </td>
                  <td>{pName}</td>
                  <td>
                    <span className="font-mono! bg-[color:var(--bg-card)]! p-[2px_6px]! rounded-[4px]!">
                      {cnCode}
                    </span>
                  </td>
                  <td>
                    {c.year} - M{c.month || "1"}
                  </td>
                  <td>
                    <span className="status-badge active">{dest}</span>
                  </td>
                  <td className="text-right! font-semibold!">{qTonnes.toLocaleString()}</td>
                  <td className="text-right!">{direct.toFixed(3)}</td>
                  <td className="text-right!">{indirect.toFixed(3)}</td>
                  <td className="text-right! text-[color:var(--color-blue-700)]! font-bold!">
                    {totalEmbedded.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                  </td>
                  <td className="text-center!">
                    <div className="flex! gap-[6px]! justify-center!">
                      <button
                        className="action-btn p-[4px_8px]! text-[length:0.75rem]! bg-[color:var(--color-blue-500)]!"
                        onClick={() => {
                          setEditingCbamId(c.id);
                          setCbamForm({
                            id: c.id,
                            activity: fac?.activity || "",
                            division: fac?.division || "",
                            facility_id: fid ? fid.toString() : "",
                            year: c.year,
                            month: c.month || 1,
                            product_name: pName,
                            cn_code: cnCode,
                            quantity_tonnes: qTonnes.toString(),
                            export_destination: dest,
                            specific_embedded_direct: direct ? direct.toString() : "",
                            specific_embedded_indirect: indirect ? indirect.toString() : "",
                            notes: c.notes || "",
                          });
                          window.scrollTo({ top: 0, behavior: "smooth" });
                        }}
                      >
                        {t("Edit")}
                      </button>
                      <button
                        className="[background:var(--color-legacy-fee2e2)] [color:var(--color-red-700)] [border:1px_solid_var(--color-legacy-fecaca)] [&&]:[border-radius:var(--radius-md)] [cursor:pointer] [transition:all_0.2s] hover:[background:var(--color-red-700)] hover:[color:white] p-[4px_8px]! text-[length:0.75rem]!"
                        onClick={() => handleDeleteCbamExport(c.id)}
                      >
                        {t("Delete")}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          {filteredCbam.length === 0 && (
            <tr>
              <td colSpan={10} className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                {t("No CBAM product export records found.")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <PaginationControls
        currentPage={currentPage}
        totalItems={filteredCbam.length}
        itemsPerPage={ITEMS_PER_PAGE}
        onPageChange={setCurrentPage}
      />
    </div>
  </div>
);

export default CbamTab;
