import React, { useState } from "react";
import { Upload, Plus, Download, Trash2 } from "lucide-react";
import { Button, Field, Input, Sheet } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import CustomDropdown from "../../components/CustomDropdown";
import { PROCESS_TYPES } from "../../utils/EmissionFactors";
import PaginationControls from "./PaginationControls";
import AdvancedSection from "../../components/AdvancedSection";
import { t } from "../../i18n";

export interface SourceRecord {
  id: string | number;
  name: string;
  equipment_id?: string;
  type?: string;
  facility_id?: string | number;
  status?: string;
  fuel_type?: string;
  [key: string]: any;
}

export interface SourcesTabProps {
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
  filteredSources: SourceRecord[];
  getAvailableActivities: () => string[];
  getAvailableDivisions: (activity?: string) => string[];
  handleDeleteSource: (id: string | number) => void;
  handleSaveSource: () => void;
  isSubmitting?: boolean;
  isPrivileged: boolean;
  setCurrentPage: (page: number) => void;
  setImportModal: (modal: { isOpen: boolean; type: string }) => void;
  setSourceForm: React.Dispatch<React.SetStateAction<any>>;
  sourceForm: Record<string, any>;
  sources: SourceRecord[];
}

const SourcesTab: React.FC<SourcesTabProps> = ({
  ACTIVITY_LABELS,
  ITEMS_PER_PAGE,
  currentPage,
  exportToCSV,
  facilities,
  filteredSources,
  getAvailableActivities,
  getAvailableDivisions,
  handleDeleteSource,
  handleSaveSource,
  isSubmitting,
  isPrivileged,
  setCurrentPage,
  setImportModal,
  setSourceForm,
  sourceForm,
  sources,
}) => {
  const [isAddDrawerOpen, setIsAddDrawerOpen] = useState(false);

  const onSave = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    handleSaveSource();
    setIsAddDrawerOpen(false);
  };

  const rows = filteredSources.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE,
  );

  return (
    <div className="manage-card glass-panel min-w-0">
      {/* Header with Table-First Action Bar */}
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
        <div>
          <h2 className="m-0 mb-1 text-xl font-bold text-text">{t("Emission Sources Inventory")}</h2>
          <p className="m-0 text-sm text-text-secondary">
            {t("Manage operational equipment, combustion units and process emission points.")}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            onClick={() => setIsAddDrawerOpen(true)}
            className="gap-2"
          >
            <Plus className="size-4" aria-hidden="true" />
            {t("+ Add Emission Source")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => setImportModal({ isOpen: true, type: "sources" })}
            className="gap-2"
          >
            <Upload className="size-4" aria-hidden="true" />
            {t("Bulk Import")}
          </Button>
          <Button
            variant="secondary"
            onClick={() => exportToCSV(sources, "emission_sources.csv")}
            className="gap-2"
          >
            <Download className="size-4" aria-hidden="true" />
            {t("Export CSV")}
          </Button>
        </div>
      </div>

      {/* Table-First View */}
      <div className="table-container" tabIndex={0} role="region" aria-label={t("Emission sources")}>
        <table className="data-table w-full">
          <thead>
            <tr>
              <th>{t("Name")}</th>
              <th>{t("Equipment ID")}</th>
              <th>{t("Type")}</th>
              <th>{t("Region")}</th>
              <th>{t("Status")}</th>
              <th>{t("Actions")}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}>
                <td>
                  <strong>{s.name}</strong>
                </td>
                <td className="text-sm text-text-secondary">
                  {s.equipment_id || "—"}
                </td>
                <td>{t(String(PROCESS_TYPES[s.type as keyof typeof PROCESS_TYPES] || s.type))}</td>
                <td>
                  {(() => {
                    const fac = facilities.find((f) => f.id === s.facility_id);
                    if (!fac) return s.facility_id;
                    return (
                      <>
                        {fac.name}
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
                  <span className="inline-flex rounded-full bg-green-50 px-2 py-0.5 text-xs font-semibold text-green-700">
                    {s.status || t("Active")}
                  </span>
                </td>
                <td>
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDeleteSource(s.id)}
                    className="gap-1 h-7 px-2 text-xs"
                  >
                    <Trash2 className="size-3" />
                    {t("Delete")}
                  </Button>
                </td>
              </tr>
            ))}
            {filteredSources.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center p-10 text-text-secondary">
                  {t("No emission sources found.")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <PaginationControls
          currentPage={currentPage}
          totalItems={filteredSources.length}
          itemsPerPage={ITEMS_PER_PAGE}
          onPageChange={setCurrentPage}
        />
      </div>

      {/* Side Drawer Form with Progressive Disclosure */}
      <Sheet
        open={isAddDrawerOpen}
        onOpenChange={setIsAddDrawerOpen}
        title={t("Add Emission Source")}
        description={t("Register a new equipment unit, combustion source or venting point.")}
        icon={Plus}
        width="34rem"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button variant="secondary" onClick={() => setIsAddDrawerOpen(false)}>
              {t("Cancel")}
            </Button>
            <Button variant="primary" onClick={onSave} disabled={isSubmitting}>
              {t("Save Emission Source")}
            </Button>
          </div>
        }
      >
        <form onSubmit={onSave} className="flex flex-col gap-5">
          <div className="flex flex-col gap-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 pb-1 border-b border-border/60">
              {t("Essential Source Parameters")}
            </h4>

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
                value={sourceForm.activity || ""}
                onChange={(e) =>
                  setSourceForm({ ...sourceForm, activity: e.target.value, division: "", facility_id: "" })
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
                  {!isPrivileged && getAvailableDivisions(sourceForm.activity).length === 1 && (
                    <span className="rounded bg-blue-100 px-1.5 py-0 text-[0.65rem] font-bold text-blue-700">
                      {t("Auto")}
                    </span>
                  )}
                </span>
              }
            >
              <NativeSelect
                value={sourceForm.division || ""}
                onChange={(e) =>
                  setSourceForm({ ...sourceForm, division: e.target.value, facility_id: "" })
                }
                disabled={!sourceForm.activity || (!isPrivileged && getAvailableDivisions(sourceForm.activity).length === 1)}
              >
                <option value="">{t("Select Division")}</option>
                {getAvailableDivisions(sourceForm.activity).map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </NativeSelect>
            </Field>

            <Field
              label={
                <span className="inline-flex items-center gap-1.5">
                  {t("Region")} *
                  {!isPrivileged &&
                    facilities.filter((f) => f.activity === sourceForm.activity && f.division === sourceForm.division).length === 1 && (
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
                    .filter((f) => f.activity === sourceForm.activity && f.division === sourceForm.division)
                    .map((f) => ({ value: f.id.toString(), label: f.name, subLabel: f.region || f.field })),
                ]}
                value={sourceForm.facility_id != null ? String(sourceForm.facility_id) : ""}
                onChange={(val) => setSourceForm({ ...sourceForm, facility_id: val })}
                placeholder={t("Select Region")}
                disabled={
                  !sourceForm.division ||
                  (!isPrivileged &&
                    facilities.filter((f) => f.activity === sourceForm.activity && f.division === sourceForm.division).length === 1)
                }
              />
            </Field>

            <Field label={`${t("Source Name")} *`}>
              <Input
                type="text"
                value={sourceForm.name || ""}
                onChange={(e) => setSourceForm({ ...sourceForm, name: e.target.value })}
                placeholder={t("e.g. Flare A / Compressor K-101")}
                required
              />
            </Field>

            <Field label={`${t("Source Type")} *`}>
              <NativeSelect
                value={sourceForm.type || ""}
                onChange={(e) => setSourceForm({ ...sourceForm, type: e.target.value })}
                required
              >
                <option value="">{t("Select Type")}</option>
                {Object.entries(PROCESS_TYPES).map(([val, label]) => (
                  <option key={val} value={val}>
                    {t(label)}
                  </option>
                ))}
              </NativeSelect>
            </Field>
          </div>

          {/* Progressive Disclosure: Advanced Equipment & Fuel Properties */}
          <AdvancedSection
            id="sources-advanced"
            title={t("Equipment Metadata & Fuel Classification")}
            fieldCount={2}
            description={t("Asset tag, equipment identifier, and default primary fuel type.")}
          >
            <div className="flex flex-col gap-4">
              <Field label={t("Equipment ID / Asset Tag")}>
                <Input
                  type="text"
                  value={sourceForm.equipment_id || ""}
                  onChange={(e) => setSourceForm({ ...sourceForm, equipment_id: e.target.value })}
                  placeholder={t("e.g. COMP-001")}
                />
              </Field>

              <Field label={t("Fuel / Feedstock Type")}>
                <Input
                  type="text"
                  value={sourceForm.fuel_type || ""}
                  onChange={(e) => setSourceForm({ ...sourceForm, fuel_type: e.target.value })}
                  placeholder={t("e.g. Natural Gas / Associated Gas")}
                />
              </Field>
            </div>
          </AdvancedSection>
        </form>
      </Sheet>
    </div>
  );
};

export default SourcesTab;
