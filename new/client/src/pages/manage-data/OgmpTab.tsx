import React, { useState } from "react";
import { Badge, Button, Field, Input, Sheet, StatusBadge } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { Plus, Trash2, Edit2 } from "lucide-react";
import PaginationControls from "./PaginationControls";
import { RecordTable, TabCard, Td, Tr } from "./MdParts";
import AdvancedSection from "../../components/AdvancedSection";
import { t } from "../../i18n";

export interface OgmpSurveyRecord {
  id: string | number;
  facility_id?: string | number;
  facilityId?: string | number;
  facility_name?: string;
  facilityName?: string;
  survey_date?: string;
  surveyDate?: string;
  survey_type?: string;
  surveyType?: string;
  measured_rate_kg_hr?: number | string;
  measuredRateKgHr?: number | string;
  estimated_annual_tch4?: number | string;
  estimatedAnnualTch4?: number | string;
  reconciliation_status?: string;
  reconciliationStatus?: string;
  operator_notes?: string;
  operatorNotes?: string;
  year?: number | string;
  [key: string]: any;
}

export interface OgmpTabProps {
  ACTIVITY_LABELS: Record<string, string>;
  ITEMS_PER_PAGE: number;
  NON_OG_ACTIVITIES: string[];
  currentPage: number;
  editingOgmpId: string | number | null;
  facilities: Array<{
    id: string | number;
    name: string;
    field?: string;
    location?: string;
    activity?: string;
    division?: string;
    [key: string]: any;
  }>;
  filteredOgmp: OgmpSurveyRecord[];
  getAvailableActivities: () => string[];
  getAvailableDivisions: (activity?: string) => string[];
  handleDeleteOgmpSurvey: (id: string | number) => void;
  handleSaveOgmpSurvey: () => void;
  ogmpForm: Record<string, any>;
  setCurrentPage: (page: number) => void;
  setEditingOgmpId: (id: string | number | null) => void;
  setOgmpForm: React.Dispatch<React.SetStateAction<any>>;
}

const getOgmpTone = (status: string): "success" | "danger" | "warning" | "info" | "neutral" => {
  if (status === "Reconciled") return "success";
  if (status === "Discrepancy Detected") return "danger";
  if (status === "Investigation Pending") return "warning";
  if (status === "Under Review") return "info";
  return "neutral";
};

const OgmpTab: React.FC<OgmpTabProps> = ({
  ACTIVITY_LABELS,
  ITEMS_PER_PAGE,
  NON_OG_ACTIVITIES,
  currentPage,
  editingOgmpId,
  facilities,
  filteredOgmp,
  getAvailableActivities,
  getAvailableDivisions,
  handleDeleteOgmpSurvey,
  handleSaveOgmpSurvey,
  ogmpForm,
  setCurrentPage,
  setEditingOgmpId,
  setOgmpForm,
}) => {
  const [isAddDrawerOpen, setIsAddDrawerOpen] = useState(false);

  const openAdd = () => {
    setEditingOgmpId(null);
    setOgmpForm({
      activity: "",
      division: "",
      facility_id: "",
      year: new Date().getFullYear(),
      survey_date: new Date().toISOString().split("T")[0],
      survey_type: "Satellite (Sentinel-5P/MethaneSAT)",
      measured_rate_kg_hr: "",
      reconciliation_status: "Reconciled",
      operator_notes: "",
    });
    setIsAddDrawerOpen(true);
  };

  const openEdit = (o: OgmpSurveyRecord) => {
    const fid = o.facility_id || o.facilityId;
    const fac = facilities.find((f) => f.id === fid);
    const sDate = o.survey_date || o.surveyDate || "";
    const sType = o.survey_type || o.surveyType || "Satellite";
    const mRate = parseFloat(String(o.measured_rate_kg_hr ?? o.measuredRateKgHr ?? 0));
    const rStatus = o.reconciliation_status || o.reconciliationStatus || "Reconciled";
    const notes = o.operator_notes || o.operatorNotes || "";

    setEditingOgmpId(o.id);
    setOgmpForm({
      id: o.id,
      activity: fac?.activity || "",
      division: fac?.division || "",
      facility_id: fid ? fid.toString() : "",
      year: o.year || (sDate ? new Date(sDate).getFullYear() : new Date().getFullYear()),
      survey_date: sDate,
      survey_type: sType,
      measured_rate_kg_hr: mRate.toString(),
      reconciliation_status: rStatus,
      operator_notes: notes === "-" ? "" : notes,
    });
    setIsAddDrawerOpen(true);
  };

  const onSave = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    handleSaveOgmpSurvey();
    setIsAddDrawerOpen(false);
  };

  const rows = filteredOgmp.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  return (
    <TabCard
      title={t("OGMP 2.0 Site-Level Measurement Surveys")}
      description={t(
        "Manage top-down aerial, satellite, drone LiDAR, and site-level source measurements required for UNEP/IMEO Level 4 and Level 5 reconciliation.",
      )}
      actions={
        <div className="flex items-center gap-2">
          <Button variant="primary" onClick={openAdd} className="gap-2">
            <Plus className="size-4" aria-hidden="true" />
            {t("+ Add OGMP Survey")}
          </Button>
        </div>
      }
    >
      {/* Table-First View */}
      <RecordTable
        title={
          <span className="flex items-center justify-between">
            <span>{t("OGMP 2.0 Survey Records")}</span>
            <span className="text-sm font-normal text-text-secondary">
              {t("Total Surveys:")} {filteredOgmp.length}
            </span>
          </span>
        }
        head={[
          t("Facility"),
          t("Survey Date"),
          t("Measurement Method"),
          <span key="rate" className="block text-right">{t("Measured Rate (kg CH₄/hr)")}</span>,
          <span key="annual" className="block text-right">{t("Annualized (tCH₄/yr)")}</span>,
          t("Reconciliation Status"),
          t("Campaign Notes"),
          <span key="actions" className="block text-center">{t("Actions")}</span>,
        ]}
        empty={filteredOgmp.length === 0 && t("No OGMP survey records found.")}
        footer={
          <PaginationControls
            currentPage={currentPage}
            totalItems={filteredOgmp.length}
            itemsPerPage={ITEMS_PER_PAGE}
            onPageChange={setCurrentPage}
          />
        }
      >
        {rows.map((o) => {
          const fid = o.facility_id || o.facilityId;
          const fac = facilities.find((f) => f.id === fid);
          const fName = o.facility_name || o.facilityName || fac?.name || `Facility #${fid}`;
          const sDate = o.survey_date || o.surveyDate || "";
          const sType = o.survey_type || o.surveyType || "Satellite";
          const mRate = parseFloat(String(o.measured_rate_kg_hr ?? o.measuredRateKgHr ?? 0));
          const annualizedTonne = o.estimated_annual_tch4 ?? o.estimatedAnnualTch4 ?? (mRate * 8760) / 1000.0;
          const rStatus = o.reconciliation_status || o.reconciliationStatus || "Reconciled";
          const notes = o.operator_notes || o.operatorNotes || "-";

          return (
            <Tr key={o.id}>
              <Td>
                <strong className="font-semibold text-text">{fName}</strong>
              </Td>
              <Td className="whitespace-nowrap">{sDate}</Td>
              <Td>
                <span className="font-medium text-text">{sType}</span>
              </Td>
              <Td className="text-right font-semibold">
                {mRate.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })}
              </Td>
              <Td className="text-right font-bold text-success-fg">
                {parseFloat(String(annualizedTonne)).toLocaleString(undefined, {
                  minimumFractionDigits: 1,
                  maximumFractionDigits: 1,
                })}
              </Td>
              <Td>
                <StatusBadge status={rStatus} size="sm" />
              </Td>
              <Td className="max-w-xs truncate text-xs text-text-secondary" title={notes === "-" ? undefined : notes}>
                {notes}
              </Td>
              <Td className="text-center">
                <div className="flex items-center justify-center gap-1.5">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => openEdit(o)}
                    className="gap-1 h-7 px-2 text-xs"
                    title={t("Edit")}
                  >
                    <Edit2 className="size-3" />
                    {t("Edit")}
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleDeleteOgmpSurvey(o.id)}
                    className="gap-1 h-7 px-2 text-xs"
                    title={t("Delete")}
                  >
                    <Trash2 className="size-3" />
                    {t("Delete")}
                  </Button>
                </div>
              </Td>
            </Tr>
          );
        })}
      </RecordTable>

      {/* Side Drawer Form with Progressive Disclosure */}
      <Sheet
        open={isAddDrawerOpen}
        onOpenChange={setIsAddDrawerOpen}
        title={editingOgmpId ? t("Edit OGMP 2.0 Survey") : t("Add OGMP 2.0 Survey")}
        description={t("Record empirical site-level or aerial measurement results for Level 4/5 reconciliation.")}
        icon={Plus}
        width="38rem"
        footer={
          <div className="flex items-center justify-end gap-2 w-full">
            <Button
              variant="secondary"
              onClick={() => {
                setIsAddDrawerOpen(false);
                setEditingOgmpId(null);
              }}
            >
              {t("Cancel")}
            </Button>
            <Button variant="primary" onClick={onSave}>
              {editingOgmpId ? t("Update Survey Record") : t("Save Survey Record")}
            </Button>
          </div>
        }
      >
        <form onSubmit={onSave} className="flex flex-col gap-5">
          {/* Essential Measurement Parameters */}
          <div className="flex flex-col gap-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-ink-500 m-0 pb-1 border-b border-border/60">
              {t("Essential Measurement Parameters")}
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label={`${t("Activity")} *`}>
                <NativeSelect
                  value={ogmpForm.activity || ""}
                  onChange={(e) => {
                    const act = e.target.value;
                    const divs = getAvailableDivisions(act);
                    const autoDiv = divs.length === 1 ? divs[0] : "";
                    const facs = facilities.filter(
                      (f) => (!act || f.activity === act) && (!autoDiv || f.division === autoDiv),
                    );
                    const autoFac = facs.length === 1 ? facs[0].id.toString() : "";
                    setOgmpForm({ ...ogmpForm, activity: act, division: autoDiv, facility_id: autoFac });
                  }}
                  required
                >
                  <option value="">{t("Select Activity")}</option>
                  {getAvailableActivities().map((a) => (
                    <option key={a} value={a}>
                      {ACTIVITY_LABELS[a] || a}
                    </option>
                  ))}
                </NativeSelect>
              </Field>

              <Field label={t("Division")}>
                <NativeSelect
                  value={ogmpForm.division || ""}
                  onChange={(e) => {
                    const div = e.target.value;
                    const facs = facilities.filter(
                      (f) => (!ogmpForm.activity || f.activity === ogmpForm.activity) && (!div || f.division === div),
                    );
                    const autoFac = facs.length === 1 ? facs[0].id.toString() : "";
                    setOgmpForm({ ...ogmpForm, division: div, facility_id: autoFac });
                  }}
                  disabled={!ogmpForm.activity}
                >
                  <option value="">{t("Select Division")}</option>
                  {getAvailableDivisions(ogmpForm.activity).map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </NativeSelect>
              </Field>
            </div>

            <Field label={`${t("Facility / Operational Asset")} *`}>
              <NativeSelect
                value={ogmpForm.facility_id || ""}
                onChange={(e) => setOgmpForm({ ...ogmpForm, facility_id: e.target.value })}
                required
              >
                <option value="">{t("Select Facility")}</option>
                {facilities
                  .filter((f) => !NON_OG_ACTIVITIES.includes(f.activity || ""))
                  .filter(
                    (f) =>
                      (!ogmpForm.activity || f.activity === ogmpForm.activity) &&
                      (!ogmpForm.division || f.division === ogmpForm.division),
                  )
                  .map((f) => (
                    <option key={f.id} value={f.id.toString()}>
                      {f.name} {f.field ? `(${f.field})` : ""}
                    </option>
                  ))}
              </NativeSelect>
            </Field>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label={`${t("Survey Date")} *`}>
                <Input
                  type="date"
                  value={ogmpForm.survey_date || ""}
                  onChange={(e) => {
                    const d = e.target.value;
                    setOgmpForm({
                      ...ogmpForm,
                      survey_date: d,
                      year: d ? new Date(d).getFullYear() : ogmpForm.year,
                    });
                  }}
                  required
                />
              </Field>

              <Field label={`${t("Measurement Method")} *`}>
                <NativeSelect
                  value={ogmpForm.survey_type || "Satellite (Sentinel-5P/MethaneSAT)"}
                  onChange={(e) => setOgmpForm({ ...ogmpForm, survey_type: e.target.value })}
                  required
                >
                  <option value="Satellite (Sentinel-5P/MethaneSAT)">{t("Satellite (Sentinel-5P/MethaneSAT)")}</option>
                  <option value="Drone LiDAR / OGI Survey">{t("Drone LiDAR / OGI Survey")}</option>
                  <option value="Aircraft / Hyperspectral Imaging">{t("Aircraft / Hyperspectral Imaging")}</option>
                  <option value="Mobile Van OGI / Tracer Gas">{t("Mobile Van OGI / Tracer Gas")}</option>
                  <option value="Fixed Continuous Sensor Network">{t("Fixed Continuous Sensor Network")}</option>
                  <option value="High-Flow Sampler Source Measurement">{t("High-Flow Sampler Source Measurement")}</option>
                </NativeSelect>
              </Field>
            </div>

            <Field label={`${t("Measured Emission Rate (kg CH₄/hr)")} *`}>
              <Input
                type="number"
                step="any"
                min="0"
                value={ogmpForm.measured_rate_kg_hr || ""}
                onChange={(e) => setOgmpForm({ ...ogmpForm, measured_rate_kg_hr: e.target.value })}
                placeholder="e.g. 14.8"
                required
              />
            </Field>
          </div>

          {/* Progressive Disclosure: Reconciliation Status & Field Campaign Notes */}
          <AdvancedSection
            id="ogmp-advanced"
            title={t("Reconciliation Status & Campaign Notes")}
            fieldCount={2}
            description={t("Level 4 source-level vs Level 5 site-level reconciliation status and campaign observations.")}
          >
            <div className="flex flex-col gap-4">
              <Field label={t("Level 4/5 Reconciliation Status")}>
                <NativeSelect
                  value={ogmpForm.reconciliation_status || "Reconciled"}
                  onChange={(e) => setOgmpForm({ ...ogmpForm, reconciliation_status: e.target.value })}
                >
                  <option value="Reconciled">{t("Reconciled (Within ±10% agreement)")}</option>
                  <option value="Discrepancy Detected">{t("Discrepancy Detected (> 10% deviation)")}</option>
                  <option value="Investigation Pending">{t("Investigation Pending")}</option>
                  <option value="Under Review">{t("Under Review")}</option>
                </NativeSelect>
              </Field>

              <Field label={t("Campaign Notes & Meteorological Conditions")}>
                <Input
                  type="text"
                  value={ogmpForm.operator_notes || ""}
                  onChange={(e) => setOgmpForm({ ...ogmpForm, operator_notes: e.target.value })}
                  placeholder={t("Wind speed, detection threshold, cloud cover, flight altitude...")}
                />
              </Field>
            </div>
          </AdvancedSection>
        </form>
      </Sheet>
    </TabCard>
  );
};

export default OgmpTab;
