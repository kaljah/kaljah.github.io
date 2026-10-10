import React from "react";
import { Input, Field } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from "../../components/CustomDropdown";
import { Upload } from "lucide-react";
import PaginationControls from "./PaginationControls";
import { t } from "../../i18n";

export interface MitigationRecord {
  id: string | number;
  name?: string;
  mitigation_type?: string;
  activity?: string;
  region?: string;
  division?: string;
  year?: number | string;
  type?: string;
  status?: string;
  quantity_tco2e: number | string;
  [key: string]: any;
}

export interface MitigationTabProps {
  ACTIVITY_LABELS: Record<string, string>;
  ITEMS_PER_PAGE: number;
  currentPage: number;
  facilities: Array<{
    id: string | number;
    name: string;
    field?: string;
    activity?: string;
    division?: string;
    [key: string]: any;
  }>;
  filteredMitigations: MitigationRecord[];
  getAvailableActivities: () => string[];
  getAvailableDivisions: (activity?: string) => string[];
  handleDeleteMitigation: (id: string | number) => void;
  handleSaveMitigation: () => void;
  isPrivileged: boolean;
  mitigationForm: Record<string, any>;
  mitigations: MitigationRecord[];
  setCurrentPage: (page: number) => void;
  setImportModal: (modal: { isOpen: boolean; type: string }) => void;
  setMitigationForm: React.Dispatch<React.SetStateAction<any>>;
}

// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const MitigationTab: React.FC<MitigationTabProps> = ({
  ACTIVITY_LABELS,
  ITEMS_PER_PAGE,
  currentPage,
  facilities,
  filteredMitigations,
  getAvailableActivities,
  getAvailableDivisions,
  handleDeleteMitigation,
  handleSaveMitigation,
  isPrivileged,
  mitigationForm,
  mitigations,
  setCurrentPage,
  setImportModal,
  setMitigationForm,
}) => (
  <div className="manage-card glass-panel">
    <div className="flex! justify-between! items-start! mb-[32px]!">
      <div>
        <h2 className="mb-[8px]! font-bold!">{t("Mitigation Projects")}</h2>
        <p className="text-[color:var(--text-secondary)]! m-[0px]!">
          {t("Record CCUS, RECs, and Carbon Offsets.")}
        </p>
      </div>
      <button
        className="action-btn [display:flex]! [align-items:center]! [gap:8px]! [padding:8px_16px]! [font-size:0.9rem]! [width:auto]!"
        onClick={() => setImportModal({ isOpen: true, type: "mitigation" })}
       
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
          value={mitigationForm.activity || ""}
          onChange={(e) =>
            setMitigationForm({ ...mitigationForm, activity: e.target.value, division: "", facility_id: "" })
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
            {!isPrivileged && getAvailableDivisions(mitigationForm.activity).length === 1 && (
              <span className="text-[length:0.65rem]! bg-[color:var(--color-legacy-dbeafe)]! text-[color:var(--color-blue-700)]! rounded-[4px]! p-[1px_5px]! font-semibold!">
                {t("Auto")}
              </span>
            )}
          </>
        }
      >
        <NativeSelect
          value={mitigationForm.division || ""}
          onChange={(e) =>
            setMitigationForm({ ...mitigationForm, division: e.target.value, facility_id: "" })
          }
          className="component-select"
          disabled={!mitigationForm.activity || (!isPrivileged && getAvailableDivisions(mitigationForm.activity).length === 1)}
        >
          <option value="">{t("Select Division")}</option>
          {getAvailableDivisions(mitigationForm.activity).map((d) => (
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
            facilities.filter((f) => f.activity === mitigationForm.activity && f.division === mitigationForm.division).length === 1 && (
              <span className="text-[length:0.65rem]! bg-[color:var(--color-legacy-dbeafe)]! text-[color:var(--color-blue-700)]! rounded-[4px]! p-[1px_5px]! font-semibold!">
                {t("Auto")}
              </span>
            )}
        </label>
        <CustomDropdown
          options={[
            { value: "", label: t("Select Region") },
            ...facilities
              .filter((f) => f.activity === mitigationForm.activity && f.division === mitigationForm.division)
              .map((f) => ({ value: f.id.toString(), label: f.name, subLabel: f.field })),
          ]}
          value={mitigationForm.facility_id != null ? String(mitigationForm.facility_id) : ""}
          onChange={(val) => setMitigationForm({ ...mitigationForm, facility_id: val })}
          placeholder={t("Select Region")}
          disabled={
            !mitigationForm.division ||
            (!isPrivileged &&
              facilities.filter((f) => f.activity === mitigationForm.activity && f.division === mitigationForm.division).length === 1)
          }
        />
      </div>

      <Field className="input-group" label={t("Project Name")}>
        <Input
          type="text"
          value={mitigationForm.name || ""}
          onChange={(e) => setMitigationForm({ ...mitigationForm, name: e.target.value })}
          placeholder={t("e.g. Flare Reduction Unit 1")}
        />
      </Field>

      <Field className="input-group" label={t("Year")}>
        <Input
          type="number"
          value={mitigationForm.year || ""}
          onChange={(e) => setMitigationForm({ ...mitigationForm, year: e.target.value })}
        />
      </Field>

      <Field className="input-group" label={t("Type")}>
        <NativeSelect
          value={mitigationForm.type || "CCUS"}
          onChange={(e) => setMitigationForm({ ...mitigationForm, type: e.target.value })}
          className="component-select"
        >
          <option value="CCUS">{t("CCUS (Carbon Capture)")}</option>
          <option value="REC">{t("REC (Renewable Energy Credit)")}</option>
          <option value="Offset">{t("Carbon Offset")}</option>
          <option value="Efficiency">{t("Energy Efficiency")}</option>
          <option value="Process">{t("Process Improvement")}</option>
        </NativeSelect>
      </Field>

      <Field className="input-group" label={t("Quantity (tCO₂e)")}>
        <Input
          type="number"
          value={mitigationForm.quantity_tco2e || ""}
          onChange={(e) => setMitigationForm({ ...mitigationForm, quantity_tco2e: e.target.value })}
          placeholder="0.0"
        />
      </Field>

      <Field className="input-group" label={t("Status")}>
        <NativeSelect
          value={mitigationForm.status || "Active"}
          onChange={(e) => setMitigationForm({ ...mitigationForm, status: e.target.value })}
          className="component-select"
        >
          <option value="Active">{t("Active")}</option>
          <option value="Planned">{t("Planned")}</option>
          <option value="Completed">{t("Completed")}</option>
        </NativeSelect>
      </Field>
    </div>

    <div className="flex! gap-[12px]! mt-[20px]!">
      <button className="action-btn" onClick={handleSaveMitigation}>
        {t("Save Record")}
      </button>
      <button
        className="action-btn bg-[color:var(--color-green-500)]!"
        onClick={() => setImportModal({ isOpen: true, type: "mitigation" })}
      >
        <Upload size={16} />{" "}{t("Import Mitigation CSV")}
      </button>
    </div>

    <div className="table-container mt-[40px]!" tabIndex={0} role="region" aria-label={t("Mitigation records")}>
      <h3>{t("Mitigation Records")}</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>{t("Project Name")}</th>
            <th>{t("Activity")}</th>
            <th>{t("Region")}</th>
            <th>{t("Year")}</th>
            <th>{t("Type")}</th>
            <th>{t("Status")}</th>
            <th className="text-right!">{t("Quantity (tCO₂e)")}</th>
            <th className="text-center!">{t("Actions")}</th>
          </tr>
        </thead>
        <tbody>
          {filteredMitigations
            .slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE)
            .map((m) => (
              <tr key={m.id}>
                <td>
                  <strong>{m.name || m.mitigation_type}</strong>
                </td>
                <td>{ACTIVITY_LABELS[m.activity || ""] || m.activity || "-"}</td>
                <td>
                  {m.region || "-"}
                  {m.division && m.division !== "-" ? (
                    <div className="text-[length:0.75rem]! text-[color:var(--text-secondary)]!">
                      {m.division}
                    </div>
                  ) : null}
                </td>
                <td>{m.year}</td>
                <td>{m.mitigation_type || m.type}</td>
                <td>
                  <span className={`status-badge ${m.status?.toLowerCase() || "active"}`}>
                    {m.status || t("Active")}
                  </span>
                </td>
                <td className="text-right! text-[color:var(--color-green-700)]! font-semibold!">
                  -{parseFloat(String(m.quantity_tco2e)).toLocaleString()}
                </td>
                <td className="text-center!">
                  <button
                    className="[background:var(--color-legacy-fee2e2)] [color:var(--color-red-700)] [border:1px_solid_var(--color-legacy-fecaca)] [&&]:[border-radius:var(--radius-md)] [cursor:pointer] [transition:all_0.2s] hover:[background:var(--color-red-700)] hover:[color:white] p-[6px_12px]! text-[length:0.8rem]!"
                    onClick={() => handleDeleteMitigation(m.id)}
                  >
                    {t("Delete")}
                  </button>
                </td>
              </tr>
            ))}
          {filteredMitigations.length === 0 && (
            <tr>
              <td colSpan={8} className="text-center! p-[40px]! text-[color:var(--text-secondary)]!">
                {mitigations.length === 0
                  ? t("No mitigation projects recorded yet.")
                  : t("No mitigation projects found matching active filters.")}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <PaginationControls
        currentPage={currentPage}
        totalItems={filteredMitigations.length}
        itemsPerPage={ITEMS_PER_PAGE}
        onPageChange={setCurrentPage}
      />
    </div>
  </div>
);

export default MitigationTab;
