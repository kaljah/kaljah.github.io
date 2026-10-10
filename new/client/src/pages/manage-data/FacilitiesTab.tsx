import React from "react";
import { Upload } from "lucide-react";
import { Button, Field, Input, controlClass } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { BOUNDARY_OPTIONS } from "../../constants";
import PaginationControls from "./PaginationControls";
import { FormActions, FormGrid, RecordTable, TabCard, Td, Tr } from "./MdParts";
import { t } from "../../i18n";

const SEGMENTS = ["Upstream", "Midstream", "Downstream", "Heavy Industry", "Utilities", "Other"];

export interface FacilityRecord {
  id: string | number;
  name: string;
  activity?: string;
  division?: string;
  field?: string;
  location?: string;
  boundary_notes?: string;
  boundary_type?: string;
  boundary_detail?: string;
  equity_share_pct?: number | string;
  segment?: string;
  latitude?: number | string;
  longitude?: number | string;
  [key: string]: any;
}

export interface FacilitiesTabProps {
  ACTIVITY_LABELS: Record<string, string>;
  HIERARCHY: Record<string, string[]>;
  ITEMS_PER_PAGE: number;
  currentPage: number;
  exportToCSV: (data: any[], filename: string) => void;
  facilities: FacilityRecord[];
  facilityForm: Record<string, any>;
  filteredFacilities: FacilityRecord[];
  handleAddFacility: () => void;
  handleDeleteFacility: (id: string | number) => void;
  handleFacilityChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => void;
  setCurrentPage: (page: number) => void;
  setFacilityForm: React.Dispatch<React.SetStateAction<any>>;
  setImportModal: (modal: { isOpen: boolean; type: string }) => void;
  user?: { role?: string; [key: string]: any } | null;
}

const FacilitiesTab: React.FC<FacilitiesTabProps> = ({
  ACTIVITY_LABELS,
  HIERARCHY,
  ITEMS_PER_PAGE,
  currentPage,
  exportToCSV,
  facilities,
  facilityForm,
  filteredFacilities,
  handleAddFacility,
  handleDeleteFacility,
  handleFacilityChange,
  setCurrentPage,
  setFacilityForm,
  setImportModal,
  user,
}) => {
  const canEdit = ["admin", "superuser"].includes(user?.role || "");
  const patch = (fields: Record<string, any>) => setFacilityForm({ ...facilityForm, ...fields });
  const select = (
    name: string,
    onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void,
    options: React.ReactNode,
    placeholder: string,
    disabled?: boolean,
  ) => (
    <NativeSelect
      name={name}
      value={facilityForm[name] || ""}
      onChange={onChange}
      className={controlClass}
      disabled={disabled}
    >
      <option value="">{placeholder}</option>
      {options}
    </NativeSelect>
  );
  const rows = filteredFacilities.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  return (
    <TabCard title={t("Active Regions")} description={t("Manage operational regions and their boundaries.")}>
      {canEdit && (
        <>
          <FormGrid>
            <Field label={t("Region Name")}>
              <Input
                type="text"
                name="name"
                value={facilityForm.name || ""}
                onChange={handleFacilityChange}
                placeholder={t("e.g. Hassi R'Mel")}
              />
            </Field>
            <Field label={t("Activity")}>
              {select(
                "activity",
                (e) => patch({ activity: e.target.value, division: "" }),
                Object.keys(HIERARCHY).map((a) => (
                  <option key={a} value={a}>
                    {ACTIVITY_LABELS[a]}
                  </option>
                )),
                t("Select Activity"),
              )}
            </Field>
            <Field label={t("Division")}>
              {select(
                "division",
                handleFacilityChange,
                facilityForm.activity &&
                  HIERARCHY[facilityForm.activity]?.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  )),
                t("Select Division"),
                !facilityForm.activity,
              )}
            </Field>
            <Field label={t("Field / Block")}>
              <Input
                type="text"
                name="field"
                value={facilityForm.field || ""}
                onChange={handleFacilityChange}
                placeholder={t("Optional")}
              />
            </Field>
            <Field label={t("Location (Wilaya)")}>
              <Input
                type="text"
                name="location"
                value={facilityForm.location || ""}
                onChange={handleFacilityChange}
                placeholder={t("e.g. Laghouat")}
              />
            </Field>
            <Field label={t("Consolidation Approach")}>
              {select(
                "boundary_type",
                (e) => patch({ boundary_type: e.target.value, boundary_detail: "" }),
                Object.keys(BOUNDARY_OPTIONS).map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                )),
                t("Select Approach"),
              )}
            </Field>
            <Field label={t("Boundary Details")}>
              {select(
                "boundary_detail",
                (e) => patch({ boundary_detail: e.target.value }),
                facilityForm.boundary_type &&
                  BOUNDARY_OPTIONS[facilityForm.boundary_type]?.map((detail) => (
                    <option key={detail} value={detail}>
                      {detail}
                    </option>
                  )),
                t("Select Details"),
                !facilityForm.boundary_type,
              )}
            </Field>
            {facilityForm.boundary_type === "Equity Share" && (
              <Field label={t("Equity Share Percentage (%)")}>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="100"
                  name="equity_share_pct"
                  value={facilityForm.equity_share_pct !== undefined ? facilityForm.equity_share_pct : ""}
                  onChange={(e) => patch({ equity_share_pct: e.target.value })}
                  placeholder="e.g. 51.00"
                />
              </Field>
            )}
            <Field label={t("Supply Chain Segment")}>
              {select(
                "segment",
                handleFacilityChange,
                SEGMENTS.map((s) => (
                  <option key={s} value={s}>
                    {t(s)}
                  </option>
                )),
                t("Select Segment"),
              )}
            </Field>
            <Field label={t("Latitude")}>
              <Input
                type="number"
                step="any"
                name="latitude"
                value={facilityForm.latitude || ""}
                onChange={handleFacilityChange}
                placeholder="e.g. 33.8"
              />
            </Field>
            <Field label={t("Longitude")}>
              <Input
                type="number"
                step="any"
                name="longitude"
                value={facilityForm.longitude || ""}
                onChange={handleFacilityChange}
                placeholder="e.g. 6.07"
              />
            </Field>
          </FormGrid>

          <FormActions>
            <Button onClick={handleAddFacility}>{t("Add Region")}</Button>
            <Button variant="secondary" onClick={() => setImportModal({ isOpen: true, type: "facilities" })}>
              <Upload className="size-4" aria-hidden="true" />{" "}{t("Bulk Import (CSV)")}
            </Button>
            <Button variant="secondary" onClick={() => exportToCSV(facilities, "regions_export.csv")}>
              {t("Export CSV")}
            </Button>
          </FormActions>
        </>
      )}

      <RecordTable
        title={t("Active Regions")}
        head={[t("Region Name"), t("Activity"), t("Division"), t("Location"), t("Boundary"), t("Segment"), t("Coordinates"), ...(canEdit ? [t("Actions")] : [])]}
        empty={filteredFacilities.length === 0 && t("No regions found.")}
        footer={<PaginationControls currentPage={currentPage} totalItems={filteredFacilities.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />}
      >
        {rows.map((f) => (
          <Tr key={f.id}>
            <Td>
              <strong>{f.name}</strong>
            </Td>
            <Td>{ACTIVITY_LABELS[f.activity || ""] || f.activity}</Td>
            <Td>{f.division}</Td>
            <Td>{f.location || "-"}</Td>
            <Td>{f.boundary_notes || (f.boundary_type ? `${f.boundary_type}${f.boundary_detail ? " - " + f.boundary_detail : ""}` : "-")}</Td>
            <Td>{f.segment ? t(f.segment) : "-"}</Td>
            <Td className="text-sm">{f.latitude ? `${f.latitude}, ${f.longitude}` : t("Not Set")}</Td>
            {canEdit && (
              <Td>
                <Button variant="danger" size="sm" onClick={() => handleDeleteFacility(f.id)}>
                  {t("Delete")}
                </Button>
              </Td>
            )}
          </Tr>
        ))}
      </RecordTable>
    </TabCard>
  );
};

export default FacilitiesTab;
