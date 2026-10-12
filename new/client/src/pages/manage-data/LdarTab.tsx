import React, { useState, useEffect } from "react";
import { Badge, Button, Field, Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import Modal from "../../components/Modal";
import { useToast } from "../../components/Toast";
import { TabCard, RecordTable, Tr, Td } from "./MdParts";
import { t } from "../../i18n";
import api from "../../api";
import { apiError } from "../../utils/apiError";
import { Wrench, Plus, CheckCircle, AlertTriangle } from "lucide-react";

export interface LdarTabProps {
  facilities: Array<{
    id: string | number;
    name: string;
    activity?: string;
    division?: string;
    [key: string]: any;
  }>;
  isPrivileged?: boolean;
}

interface ComponentItem {
  id: number;
  facility_id: number;
  facility_name?: string;
  equipment_type: string;
  component_type: string;
  service_type: string;
  quantity: number;
  operating_hours: number;
  status: string;
  description?: string;
}

interface SurveyItem {
  id: number;
  facility_id: number;
  facility_name?: string;
  component_inventory_id?: number;
  survey_method: string;
  survey_date: string;
  detection_threshold_ppm?: number;
  screening_value_ppm?: number;
  leak_status: string;
  measured_emission_rate?: number;
  measurement_unit?: string;
  repair_date?: string;
  leaking_hours?: number;
  surveyor_name?: string;
  notes?: string;
}

export const LdarTab: React.FC<LdarTabProps> = ({ facilities, isPrivileged }) => {
  const toast = useToast();
  const [activeSubTab, setActiveSubTab] = useState<"surveys" | "components">("surveys");
  const [surveys, setSurveys] = useState<SurveyItem[]>([]);
  const [components, setComponents] = useState<ComponentItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // Repair Modal State
  const [repairModal, setRepairModal] = useState<{
    isOpen: boolean;
    survey: SurveyItem | null;
    repairDate: string;
    postRepairPpm: string;
    notes: string;
  }>({
    isOpen: false,
    survey: null,
    repairDate: new Date().toISOString().split("T")[0],
    postRepairPpm: "0",
    notes: "",
  });

  // Record Survey Modal State
  const [surveyModal, setSurveyModal] = useState<{
    isOpen: boolean;
    facility_id: string;
    component_inventory_id: string;
    survey_method: string;
    survey_date: string;
    screening_value_ppm: string;
    leak_status: string;
    leaking_hours: string;
    surveyor_name: string;
    notes: string;
  }>({
    isOpen: false,
    facility_id: "",
    component_inventory_id: "",
    survey_method: "Method 21",
    survey_date: new Date().toISOString().split("T")[0],
    screening_value_ppm: "0",
    leak_status: "Non-leaking",
    leaking_hours: "8760",
    surveyor_name: "",
    notes: "",
  });

  // Add Component Modal State
  const [compModal, setCompModal] = useState<{
    isOpen: boolean;
    facility_id: string;
    equipment_type: string;
    component_type: string;
    service_type: string;
    quantity: string;
    operating_hours: string;
    description: string;
  }>({
    isOpen: false,
    facility_id: "",
    equipment_type: "Valves",
    component_type: "Gate Valve",
    service_type: "Gas",
    quantity: "1",
    operating_hours: "8760",
    description: "",
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [surveysRes, compRes] = await Promise.all([
        api.get("/ldar/surveys"),
        api.get("/ldar/components"),
      ]);
      setSurveys(surveysRes.data?.surveys || []);
      setComponents(compRes.data?.components || []);
    } catch (err) {
      toast.show(apiError(err), "danger");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleOpenRepairModal = (survey: SurveyItem) => {
    setRepairModal({
      isOpen: true,
      survey,
      repairDate: new Date().toISOString().split("T")[0],
      postRepairPpm: "0",
      notes: survey.notes || "",
    });
  };

  const handleSaveRepair = async () => {
    if (!repairModal.survey) return;
    try {
      await api.put(`/ldar/surveys/${repairModal.survey.id}`, {
        leak_status: "Repaired",
        repair_date: repairModal.repairDate,
        screening_value_ppm: parseFloat(repairModal.postRepairPpm) || 0,
        notes: repairModal.notes
          ? `${repairModal.survey.notes ? repairModal.survey.notes + " | " : ""}Repaired: ${repairModal.notes}`
          : repairModal.survey.notes,
      });
      toast.show(t("Leak marked as repaired successfully"), "success");
      setRepairModal((prev) => ({ ...prev, isOpen: false, survey: null }));
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "danger");
    }
  };

  const handleSaveSurvey = async () => {
    if (!surveyModal.facility_id) {
      toast.show(t("Facility is required"), "warning");
      return;
    }
    try {
      await api.post("/ldar/surveys", {
        facility_id: parseInt(surveyModal.facility_id, 10),
        component_inventory_id: surveyModal.component_inventory_id
          ? parseInt(surveyModal.component_inventory_id, 10)
          : null,
        survey_method: surveyModal.survey_method,
        survey_date: surveyModal.survey_date,
        screening_value_ppm: parseFloat(surveyModal.screening_value_ppm) || 0,
        leak_status: surveyModal.leak_status,
        leaking_hours: parseFloat(surveyModal.leaking_hours) || 8760,
        surveyor_name: surveyModal.surveyor_name,
        notes: surveyModal.notes,
      });
      toast.show(t("Survey logged successfully"), "success");
      setSurveyModal((prev) => ({ ...prev, isOpen: false }));
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "danger");
    }
  };

  const handleSaveComponent = async () => {
    if (!compModal.facility_id) {
      toast.show(t("Facility is required"), "warning");
      return;
    }
    try {
      await api.post("/ldar/components", {
        facility_id: parseInt(compModal.facility_id, 10),
        equipment_type: compModal.equipment_type,
        component_type: compModal.component_type,
        service_type: compModal.service_type,
        quantity: parseInt(compModal.quantity, 10) || 1,
        operating_hours: parseFloat(compModal.operating_hours) || 8760,
        description: compModal.description,
      });
      toast.show(t("Component added successfully"), "success");
      setCompModal((prev) => ({ ...prev, isOpen: false }));
      fetchData();
    } catch (err) {
      toast.show(apiError(err), "danger");
    }
  };

  const getStatusBadge = (status: string) => {
    if (status === "Leaking") {
      return (
        <Badge tone="danger" className="inline-flex items-center gap-1">
          <AlertTriangle className="size-3" />
          {t("Leaking")}
        </Badge>
      );
    }
    if (status === "Repaired") {
      return (
        <Badge tone="success" className="inline-flex items-center gap-1">
          <CheckCircle className="size-3" />
          {t("Repaired")}
        </Badge>
      );
    }
    return <Badge tone="neutral">{t(status || "Non-leaking")}</Badge>;
  };

  return (
    <TabCard
      title={t("LDAR & Fugitive Leak Management")}
      description={t(
        "Track leak detection surveys (EPA Method 21 / OGI) and manage component inventories with leak repair workflow.",
      )}
      actions={
        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex rounded-md border border-border p-0.5">
            <button
              type="button"
              onClick={() => setActiveSubTab("surveys")}
              className={`px-3 py-1.5 text-xs font-semibold rounded ${
                activeSubTab === "surveys"
                  ? "bg-brand-500 text-white shadow-xs"
                  : "text-text-secondary hover:text-text"
              }`}
            >
              {t("Surveys & Repairs")} ({surveys.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveSubTab("components")}
              className={`px-3 py-1.5 text-xs font-semibold rounded ${
                activeSubTab === "components"
                  ? "bg-brand-500 text-white shadow-xs"
                  : "text-text-secondary hover:text-text"
              }`}
            >
              {t("Component Inventory")} ({components.length})
            </button>
          </div>
          {activeSubTab === "surveys" ? (
            <Button
              variant="primary"
              onClick={() =>
                setSurveyModal((prev) => ({
                  ...prev,
                  isOpen: true,
                  facility_id: facilities[0]?.id ? String(facilities[0].id) : "",
                }))
              }
              className="inline-flex items-center gap-1.5"
            >
              <Plus className="size-4" />
              {t("Record Survey")}
            </Button>
          ) : (
            <Button
              variant="primary"
              onClick={() =>
                setCompModal((prev) => ({
                  ...prev,
                  isOpen: true,
                  facility_id: facilities[0]?.id ? String(facilities[0].id) : "",
                }))
              }
              className="inline-flex items-center gap-1.5"
            >
              <Plus className="size-4" />
              {t("Add Component")}
            </Button>
          )}
        </div>
      }
    >
      {activeSubTab === "surveys" ? (
        <RecordTable
          title={t("Fugitive Leak Surveys")}
          head={[
            t("Facility"),
            t("Date"),
            t("Method"),
            t("Screening (PPM)"),
            t("Leak Status"),
            t("Repair Date"),
            t("Duration (hrs)"),
            t("Actions"),
          ]}
          empty={loading ? t("Loading surveys...") : t("No LDAR surveys recorded yet.")}
        >
          {surveys.map((s) => (
            <Tr key={s.id}>
              <Td className="font-medium text-text">
                {s.facility_name || facilities.find((f) => f.id === s.facility_id)?.name || s.facility_id}
              </Td>
              <Td>{s.survey_date}</Td>
              <Td>{s.survey_method}</Td>
              <Td className="font-mono">
                {s.screening_value_ppm !== undefined && s.screening_value_ppm !== null
                  ? `${s.screening_value_ppm.toLocaleString()} ppm`
                  : "-"}
              </Td>
              <Td>{getStatusBadge(s.leak_status)}</Td>
              <Td>{s.repair_date || "-"}</Td>
              <Td className="font-mono">{s.leaking_hours !== undefined ? s.leaking_hours : 8760}</Td>
              <Td>
                {s.leak_status === "Leaking" && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenRepairModal(s)}
                    className="inline-flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700"
                  >
                    <Wrench className="size-3.5" />
                    {t("Mark Repaired")}
                  </Button>
                )}
                {s.leak_status === "Repaired" && (
                  <span className="text-xs text-text-secondary">{t("Completed")}</span>
                )}
              </Td>
            </Tr>
          ))}
        </RecordTable>
      ) : (
        <RecordTable
          title={t("Component Inventory")}
          head={[
            t("Facility"),
            t("Equipment"),
            t("Component"),
            t("Service"),
            t("Quantity"),
            t("Operating Hours"),
            t("Status"),
          ]}
          empty={loading ? t("Loading components...") : t("No components in inventory.")}
        >
          {components.map((c) => (
            <Tr key={c.id}>
              <Td className="font-medium text-text">
                {c.facility_name || facilities.find((f) => f.id === c.facility_id)?.name || c.facility_id}
              </Td>
              <Td>{c.equipment_type}</Td>
              <Td>{c.component_type}</Td>
              <Td>{c.service_type}</Td>
              <Td className="font-mono">{c.quantity}</Td>
              <Td className="font-mono">{c.operating_hours}</Td>
              <Td>
                <Badge tone={c.status === "Active" ? "success" : "neutral"}>
                  {c.status || "Active"}
                </Badge>
              </Td>
            </Tr>
          ))}
        </RecordTable>
      )}

      {/* Repair Modal */}
      {repairModal.isOpen && (
        <Modal
          title={t("Record Leak Repair")}
          onClose={() => setRepairModal((prev) => ({ ...prev, isOpen: false, survey: null }))}
        >
          <div className="space-y-4 p-4">
            <p className="text-sm text-text-secondary">
              {t("Confirm repair details for survey #")}
              {repairModal.survey?.id} ({repairModal.survey?.survey_method}).
            </p>
            <Field label={t("Repair Date")}>
              <Input
                type="date"
                value={repairModal.repairDate}
                onChange={(e) =>
                  setRepairModal((prev) => ({ ...prev, repairDate: e.target.value }))
                }
              />
            </Field>
            <Field label={t("Post-Repair Screening (PPM)")}>
              <Input
                type="number"
                min="0"
                step="any"
                value={repairModal.postRepairPpm}
                onChange={(e) =>
                  setRepairModal((prev) => ({ ...prev, postRepairPpm: e.target.value }))
                }
              />
            </Field>
            <Field label={t("Repair Notes")}>
              <Input
                type="text"
                placeholder={t("e.g. Packing tightened, flange retorqued")}
                value={repairModal.notes}
                onChange={(e) =>
                  setRepairModal((prev) => ({ ...prev, notes: e.target.value }))
                }
              />
            </Field>
            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setRepairModal((prev) => ({ ...prev, isOpen: false, survey: null }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleSaveRepair}>
                {t("Save Repair")}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Record Survey Modal */}
      {surveyModal.isOpen && (
        <Modal
          title={t("Record Leak Detection Survey")}
          onClose={() => setSurveyModal((prev) => ({ ...prev, isOpen: false }))}
        >
          <div className="space-y-4 p-4">
            <Field label={t("Facility")}>
              <NativeSelect
                value={surveyModal.facility_id}
                onChange={(e) =>
                  setSurveyModal((prev) => ({ ...prev, facility_id: e.target.value }))
                }
              >
                <option value="">{t("Select facility...")}</option>
                {facilities.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Survey Method")}>
                <NativeSelect
                  value={surveyModal.survey_method}
                  onChange={(e) =>
                    setSurveyModal((prev) => ({ ...prev, survey_method: e.target.value }))
                  }
                >
                  <option value="Method 21">EPA Method 21</option>
                  <option value="OGI">Optical Gas Imaging (OGI)</option>
                  <option value="Acoustic">Acoustic Leak Detection</option>
                </NativeSelect>
              </Field>
              <Field label={t("Survey Date")}>
                <Input
                  type="date"
                  value={surveyModal.survey_date}
                  onChange={(e) =>
                    setSurveyModal((prev) => ({ ...prev, survey_date: e.target.value }))
                  }
                />
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Screening Value (PPM)")}>
                <Input
                  type="number"
                  min="0"
                  value={surveyModal.screening_value_ppm}
                  onChange={(e) => {
                    const ppm = parseFloat(e.target.value) || 0;
                    setSurveyModal((prev) => ({
                      ...prev,
                      screening_value_ppm: e.target.value,
                      leak_status: ppm >= 500 ? "Leaking" : "Non-leaking",
                    }));
                  }}
                />
              </Field>
              <Field label={t("Leak Status")}>
                <NativeSelect
                  value={surveyModal.leak_status}
                  onChange={(e) =>
                    setSurveyModal((prev) => ({ ...prev, leak_status: e.target.value }))
                  }
                >
                  <option value="Non-leaking">{t("Non-leaking")}</option>
                  <option value="Leaking">{t("Leaking")}</option>
                  <option value="Repaired">{t("Repaired")}</option>
                </NativeSelect>
              </Field>
            </div>
            <Field label={t("Surveyor Name")}>
              <Input
                type="text"
                placeholder={t("Operator or Inspector name")}
                value={surveyModal.surveyor_name}
                onChange={(e) =>
                  setSurveyModal((prev) => ({ ...prev, surveyor_name: e.target.value }))
                }
              />
            </Field>
            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setSurveyModal((prev) => ({ ...prev, isOpen: false }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleSaveSurvey}>
                {t("Log Survey")}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Add Component Modal */}
      {compModal.isOpen && (
        <Modal
          title={t("Add Component to Inventory")}
          onClose={() => setCompModal((prev) => ({ ...prev, isOpen: false }))}
        >
          <div className="space-y-4 p-4">
            <Field label={t("Facility")}>
              <NativeSelect
                value={compModal.facility_id}
                onChange={(e) =>
                  setCompModal((prev) => ({ ...prev, facility_id: e.target.value }))
                }
              >
                <option value="">{t("Select facility...")}</option>
                {facilities.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </NativeSelect>
            </Field>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Equipment Type")}>
                <NativeSelect
                  value={compModal.equipment_type}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, equipment_type: e.target.value }))
                  }
                >
                  <option value="Valves">Valves</option>
                  <option value="Flanges">Flanges</option>
                  <option value="Pumps">Pumps</option>
                  <option value="Compressors">Compressors</option>
                  <option value="Relief Valves">Relief Valves</option>
                  <option value="Open-ended Lines">Open-ended Lines</option>
                </NativeSelect>
              </Field>
              <Field label={t("Service Type")}>
                <NativeSelect
                  value={compModal.service_type}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, service_type: e.target.value }))
                  }
                >
                  <option value="Gas">Gas</option>
                  <option value="Light Liquid">Light Liquid</option>
                  <option value="Heavy Liquid">Heavy Liquid</option>
                  <option value="Water / Oil">Water / Oil</option>
                </NativeSelect>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Field label={t("Quantity")}>
                <Input
                  type="number"
                  min="1"
                  value={compModal.quantity}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, quantity: e.target.value }))
                  }
                />
              </Field>
              <Field label={t("Operating Hours / Year")}>
                <Input
                  type="number"
                  min="1"
                  max="8760"
                  value={compModal.operating_hours}
                  onChange={(e) =>
                    setCompModal((prev) => ({ ...prev, operating_hours: e.target.value }))
                  }
                />
              </Field>
            </div>
            <Field label={t("Description / Tag")}>
              <Input
                type="text"
                placeholder={t("e.g. Header isolation valves unit 4")}
                value={compModal.description}
                onChange={(e) =>
                  setCompModal((prev) => ({ ...prev, description: e.target.value }))
                }
              />
            </Field>
            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => setCompModal((prev) => ({ ...prev, isOpen: false }))}
              >
                {t("Cancel")}
              </Button>
              <Button variant="primary" onClick={handleSaveComponent}>
                {t("Save Component")}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </TabCard>
  );
};

export default LdarTab;
