import React from "react";
import { Badge, Banner, Button, Field, Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import PaginationControls from "./PaginationControls";
import { FormActions, FormGrid, RecordTable, TabCard, Td, Tr } from "./MdParts";
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
  const rows = filteredOgmp.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  return (
    <TabCard
      title={t("OGMP 2.0 Level 4 & 5 Top-Down / Bottom-Up Surveys")}
      description={t(
        "Log site-level top-down measurements (satellite, aerial LiDAR, drone, ground OGI) to reconcile against inventory estimates under Oil and Gas Methane Partnership (OGMP 2.0) Level 4/5 standards.",
      )}
    >
      {/* O&G Scope Notice */}
      <Banner tone="info" title={t("Oil & Gas Scope Only")} className="mb-6">
        {t(
          "OGMP 2.0 applies exclusively to Oil & Gas operations (Upstream, Midstream, LNG). Heavy industry facilities (Steel, Cement, Chemicals) are not in scope.",
        )}
      </Banner>

      <FormGrid className="form-grid-3" cols="md:grid-cols-3">
        <Field label={t("Activity")}>
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
            className="component-select"
          >
            <option value="">{t("-- Select Activity (Oil & Gas) --")}</option>
            {getAvailableActivities()
              .filter((a) => !NON_OG_ACTIVITIES.includes(a))
              .map((a) => (
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
            className="component-select"
            disabled={!ogmpForm.activity}
          >
            <option value="">{t("-- Select Division --")}</option>
            {getAvailableDivisions(ogmpForm.activity).map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </NativeSelect>
        </Field>

        <Field label={t("Facility / Region *")}>
          <NativeSelect
            value={ogmpForm.facility_id || ""}
            onChange={(e) => setOgmpForm({ ...ogmpForm, facility_id: e.target.value })}
            className="component-select"
          >
            <option value="">{t("-- Select O& Gas Facility --")}</option>
            {facilities
              .filter(
                (f) =>
                  !NON_OG_ACTIVITIES.includes(f.activity || "") &&
                  (!ogmpForm.activity || f.activity === ogmpForm.activity) &&
                  (!ogmpForm.division || f.division === ogmpForm.division),
              )
              .map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({f.location || f.field || t("General")})
                </option>
              ))}
          </NativeSelect>
        </Field>

        <Field label={t("Survey Date *")}>
          <Input
            type="date"
            value={ogmpForm.survey_date || ""}
            onChange={(e) => {
              const dateVal = e.target.value;
              const yr = dateVal ? new Date(dateVal).getFullYear() : ogmpForm.year;
              setOgmpForm({ ...ogmpForm, survey_date: dateVal, year: yr });
            }}
          />
        </Field>

        <Field label={t("Measurement Technology (Level 4/5) *")}>
          <NativeSelect
            value={ogmpForm.survey_type || "Satellite (Sentinel-5P/MethaneSAT)"}
            onChange={(e) => setOgmpForm({ ...ogmpForm, survey_type: e.target.value })}
            className="component-select"
          >
            <option value="Satellite (Sentinel-5P/MethaneSAT)">{t("Satellite (Sentinel-5P / MethaneSAT / GHGSat)")}</option>
            <option value="Aircraft OGI / Hyperspectral">{t("Aircraft Hyperspectral / LiDAR Aerial")}</option>
            <option value="Drone / UAV LiDAR Scanning">{t("Drone / UAV Tunable Diode Laser (TDLAS)")}</option>
            <option value="Ground Mobile / OGI FLIR Camera">{t("Ground Mobile / Optical Gas Imaging (OGI FLIR)")}</option>
            <option value="Fixed Continuous Sensor Array">{t("Fixed Continuous Point Sensor Array")}</option>
            <option value="Bottom-Up Source Component Measurement">{t("Bottom-Up High-Flow Component Sampling")}</option>
          </NativeSelect>
        </Field>

        <Field label={t("Measured Emission Rate (kg CH₄ / hr) *")}>
          <Input
            type="number"
            step="0.1"
            value={ogmpForm.measured_rate_kg_hr || ""}
            onChange={(e) => setOgmpForm({ ...ogmpForm, measured_rate_kg_hr: e.target.value })}
            placeholder="0.0"
          />
        </Field>

        <Field label={t("Reconciliation Status")}>
          <NativeSelect
            value={ogmpForm.reconciliation_status || "Reconciled"}
            onChange={(e) => setOgmpForm({ ...ogmpForm, reconciliation_status: e.target.value })}
            className="component-select"
          >
            <option value="Reconciled">{t("Reconciled (Within Uncertainty Margin)")}</option>
            <option value="Discrepancy Detected">{t("Discrepancy Detected (Bottom-Up Underestimated)")}</option>
            <option value="Investigation Pending">{t("Investigation Pending / Root Cause Analysis")}</option>
            <option value="Under Review">{t("Under Review by Operations")}</option>
          </NativeSelect>
        </Field>

        <div className="sm:col-span-2">
          <Field label={t("Operator Notes & Campaign Metadata")}>
            <Input
              type="text"
              value={ogmpForm.operator_notes || ""}
              onChange={(e) => setOgmpForm({ ...ogmpForm, operator_notes: e.target.value })}
              placeholder={t("Wind speed, flight altitude, pass number, observation conditions")}
            />
          </Field>
        </div>
      </FormGrid>

      <FormActions>
        <Button className="action-btn" onClick={handleSaveOgmpSurvey}>
          {editingOgmpId ? t("Update Survey Record") : t("Save OGMP Survey")}
        </Button>
        {editingOgmpId && (
          <Button
            variant="secondary"
            onClick={() => {
              setEditingOgmpId(null);
              setOgmpForm({
                id: null,
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
            }}
          >
            {t("Cancel Edit")}
          </Button>
        )}
      </FormActions>

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
                <Badge tone={getOgmpTone(rStatus)} className="text-xs">
                  {rStatus}
                </Badge>
              </Td>
              <Td className="max-w-xs truncate text-xs text-text-secondary" title={notes === "-" ? undefined : notes}>
                {notes}
              </Td>
              <Td className="text-center">
                <div className="flex items-center justify-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
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
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  >
                    {t("Edit")}
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleDeleteOgmpSurvey(o.id)}
                  >
                    {t("Delete")}
                  </Button>
                </div>
              </Td>
            </Tr>
          );
        })}
      </RecordTable>
    </TabCard>
  );
};

export default OgmpTab;
