import React, { useState, useEffect } from "react";
import { Upload, Users, Trash2, Plus } from "lucide-react";
import { Badge, Button, Field, Input, controlClass } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import { BOUNDARY_OPTIONS } from "../../constants";
import PaginationControls from "./PaginationControls";
import { FormActions, FormGrid, RecordTable, TabCard, Td, Tr } from "./MdParts";
import Modal from "../../components/Modal";
import api from "../../api";
import { useToast } from "../../components/Toast";
import { apiError } from "../../utils/apiError";
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
  const [selectedFacilityForEquity, setSelectedFacilityForEquity] = useState<FacilityRecord | null>(null);
  const [partners, setPartners] = useState<Array<{ id: number; name: string; code: string; country: string }>>([]);
  const [shares, setShares] = useState<Array<any>>([]);
  const [loadingShares, setLoadingShares] = useState(false);
  const [partnerForm, setPartnerForm] = useState({ partner_id: "", equity_share_pct: "", agreement_reference: "", effective_start_date: "2021-01-01" });
  const toast = useToast();

  useEffect(() => {
    if (selectedFacilityForEquity) {
      loadEquityData(selectedFacilityForEquity.id);
    }
  }, [selectedFacilityForEquity]);

  const loadEquityData = async (facilityId: string | number) => {
    setLoadingShares(true);
    try {
      const [pRes, sRes] = await Promise.all([
        api.get("/equity/partners"),
        api.get(`/equity/shares?facility_id=${facilityId}`),
      ]);
      setPartners(pRes.data || []);
      setShares(sRes.data || []);
    } catch (err) {
      toast.show(apiError(err), "error");
    } finally {
      setLoadingShares(false);
    }
  };

  const handleSaveShare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFacilityForEquity || !partnerForm.partner_id || !partnerForm.equity_share_pct) {
      toast.show(t("Partner and equity share percentage are required"), "warning");
      return;
    }
    try {
      await api.post("/equity/shares", {
        facility_id: Number(selectedFacilityForEquity.id),
        partner_id: Number(partnerForm.partner_id),
        equity_share_pct: parseFloat(partnerForm.equity_share_pct),
        effective_start_date: partnerForm.effective_start_date || "2021-01-01",
        agreement_reference: partnerForm.agreement_reference || undefined,
      });
      toast.show(t("Equity share updated successfully"), "success");
      setPartnerForm({ partner_id: "", equity_share_pct: "", agreement_reference: "", effective_start_date: "2021-01-01" });
      loadEquityData(selectedFacilityForEquity.id);
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

  const handleDeleteShare = async (shareId: number) => {
    try {
      await api.delete(`/equity/shares/${shareId}`);
      toast.show(t("Equity share removed"), "success");
      if (selectedFacilityForEquity) loadEquityData(selectedFacilityForEquity.id);
    } catch (err) {
      toast.show(apiError(err), "error");
    }
  };

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
            <Field label={`${t("Field / Block")} *`}>
              <Input
                type="text"
                name="field"
                value={facilityForm.field || ""}
                onChange={handleFacilityChange}
                placeholder={t("e.g. Hassi Messaoud South")}
                required
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
        head={[t("Region"), t("Field / Facility"), t("Activity"), t("Division"), t("Location"), t("Boundary"), t("Segment"), t("Coordinates"), ...(canEdit ? [t("Actions")] : [])]}
        empty={filteredFacilities.length === 0 && t("No regions found.")}
        footer={<PaginationControls currentPage={currentPage} totalItems={filteredFacilities.length} itemsPerPage={ITEMS_PER_PAGE} onPageChange={setCurrentPage} />}
      >
        {rows.map((f) => (
          <Tr key={f.id}>
            <Td>
              <strong>{f.region || f.location || "-"}</strong>
            </Td>
            <Td>
              <strong>{f.name}</strong>
            </Td>
            <Td>{ACTIVITY_LABELS[f.activity || ""] || f.activity}</Td>
            <Td>{f.division}</Td>
            <Td>{f.location || "-"}</Td>
            <Td>
              <div>
                <span>{f.boundary_notes || (f.boundary_type ? `${f.boundary_type}${f.boundary_detail ? " - " + f.boundary_detail : ""}` : "-")}</span>
                {f.boundary_type === "Equity Share" && f.equity_share_pct !== undefined && f.equity_share_pct !== null && Number(f.equity_share_pct) < 100 && (
                  <div className="text-xs text-amber-600 dark:text-amber-400 font-medium mt-0.5" data-testid="unallocated-equity-flag">
                    {t("{{unallocated}}% unallocated 3rd-party interest (GHG Protocol Ch. 3)", { unallocated: (100 - Number(f.equity_share_pct)).toFixed(1) })}
                  </div>
                )}
              </div>
            </Td>
            <Td>{f.segment ? t(f.segment) : "-"}</Td>
            <Td className="text-sm">{f.latitude ? `${f.latitude}, ${f.longitude}` : t("Not Set")}</Td>
            {canEdit && (
              <Td>
                <div className="flex items-center gap-2">
                  <Button variant="secondary" size="sm" data-testid={`facility-jv-shares-${f.id}`} onClick={() => setSelectedFacilityForEquity(f)} title={t("Joint Venture Equity Partners")}>
                    <Users className="size-3.5 mr-1" />
                    {t("JV Partners")}
                  </Button>
                  <Button variant="danger" size="sm" onClick={() => handleDeleteFacility(f.id)}>
                    {t("Delete")}
                  </Button>
                </div>
              </Td>
            )}
          </Tr>
        ))}
      </RecordTable>

      {selectedFacilityForEquity && (
        <Modal
          title={t("Joint Venture Equity Partners: {{name}}", { name: selectedFacilityForEquity.name })}
          onClose={() => setSelectedFacilityForEquity(null)}
          maxWidth="640px"
        >
          <div className="space-y-4 p-2 w-full">
            <div className="flex items-center justify-between text-sm pb-2 border-b border-border">
              <span className="text-text-secondary">{t("Operational Boundary: {{boundary}}", { boundary: selectedFacilityForEquity.boundary_type || "Equity Share" })}</span>
              <Badge tone={shares.reduce((sum, s) => sum + Number(s.equity_share_pct || 0), 0) === 100 ? "success" : "warning"}>
                {t("Total Allocated: {{pct}}%", { pct: shares.reduce((sum, s) => sum + Number(s.equity_share_pct || 0), 0).toFixed(1) })}
              </Badge>
            </div>

            {loadingShares ? (
              <p className="text-sm text-text-secondary py-4">{t("Loading equity shares...")}</p>
            ) : shares.length === 0 ? (
              <p className="text-sm text-text-secondary py-4">{t("No partner equity shares assigned to this facility yet.")}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-border text-xs text-text-secondary">
                      <th className="py-2">{t("Partner")}</th>
                      <th className="py-2">{t("Code")}</th>
                      <th className="py-2">{t("Equity Share")}</th>
                      <th className="py-2">{t("Agreement Ref")}</th>
                      <th className="py-2">{t("Effective Date")}</th>
                      {canEdit && <th className="py-2 text-right">{t("Action")}</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {shares.map((s) => (
                      <tr key={s.id} className="border-b border-border/50">
                        <td className="py-2 font-medium">{s.partner_name}</td>
                        <td className="py-2 font-mono text-xs">{s.partner_code}</td>
                        <td className="py-2 font-mono font-semibold">{s.equity_share_pct}%</td>
                        <td className="py-2 text-xs text-text-secondary">{s.agreement_reference || "-"}</td>
                        <td className="py-2 text-xs">{s.effective_start_date}</td>
                        {canEdit && (
                          <td className="py-2 text-right">
                            <Button variant="danger" size="sm" onClick={() => handleDeleteShare(s.id)}>
                              <Trash2 className="size-3.5" />
                            </Button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {canEdit && (
              <form onSubmit={handleSaveShare} className="pt-3 border-t border-border space-y-3">
                <h4 className="text-xs font-semibold text-text uppercase tracking-wide">{t("Assign Partner Share")}</h4>
                <div className="grid grid-cols-2 gap-3">
                  <Field label={t("Partner")}>
                    <NativeSelect
                      value={partnerForm.partner_id}
                      onChange={(e) => setPartnerForm((prev) => ({ ...prev, partner_id: e.target.value }))}
                      className={controlClass}
                    >
                      <option value="">{t("Select Partner...")}</option>
                      {partners.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} ({p.code})
                        </option>
                      ))}
                    </NativeSelect>
                  </Field>
                  <Field label={t("Equity Share (%)")}>
                    <Input
                      type="number"
                      min="0"
                      max="100"
                      step="0.01"
                      placeholder="e.g. 51.0"
                      value={partnerForm.equity_share_pct}
                      onChange={(e) => setPartnerForm((prev) => ({ ...prev, equity_share_pct: e.target.value }))}
                    />
                  </Field>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label={t("Agreement Reference")}>
                    <Input
                      type="text"
                      placeholder="e.g. Production Sharing Contract §4"
                      value={partnerForm.agreement_reference}
                      onChange={(e) => setPartnerForm((prev) => ({ ...prev, agreement_reference: e.target.value }))}
                    />
                  </Field>
                  <Field label={t("Effective Start Date")}>
                    <Input
                      type="date"
                      value={partnerForm.effective_start_date}
                      onChange={(e) => setPartnerForm((prev) => ({ ...prev, effective_start_date: e.target.value }))}
                    />
                  </Field>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <Button variant="secondary" onClick={() => setSelectedFacilityForEquity(null)}>
                    {t("Close")}
                  </Button>
                  <Button variant="primary" type="submit">
                    <Plus className="size-3.5 mr-1" />
                    {t("Save Partner Share")}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </Modal>
      )}
    </TabCard>
  );
};

export default FacilitiesTab;
