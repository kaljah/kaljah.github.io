import React, { useState } from "react";
import { FileSpreadsheet, ShieldCheck, Layers, Coins, Landmark } from "lucide-react";
import { Badge, Button, Field, Input } from "../../ui";
import { NativeSelect } from "../../ui/NativeSelect";
import PaginationControls from "./PaginationControls";
import { FormActions, FormGrid, RecordTable, TabCard, Td, Tr } from "./MdParts";
import { t } from "../../i18n";
import api from "../../api";
import { useToast } from "../../components/Toast";

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
  quarter?: string;
  export_destination?: string;
  exportDestination?: string;
  quantity_tonnes?: number | string;
  quantityTonnes?: number | string;
  specific_embedded_direct?: number | string;
  specificEmbeddedDirect?: number | string;
  specific_embedded_indirect?: number | string;
  specificEmbeddedIndirect?: number | string;
  captured_co2_tonnes?: number | string;
  capturedCo2Tonnes?: number | string;
  ccs_certificate_id?: string;
  ccsCertificateId?: string;
  carbon_price_paid_eur?: number | string;
  carbonPricePaidEur?: number | string;
  carbon_price_legal_ref?: string;
  carbonPriceLegalRef?: string;
  is_complex_good?: boolean;
  isComplexGood?: boolean;
  precursor_name?: string;
  precursorName?: string;
  precursor_cn_code?: string;
  precursorCnCode?: string;
  precursor_ratio?: number | string;
  precursorRatio?: number | string;
  precursor_see_dir?: number | string;
  precursorSeeDir?: number | string;
  precursor_see_indir?: number | string;
  precursorSeeIndir?: number | string;
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

export const CN_OPTIONS = [
  { code: "2804 10 00", label: "2804 10 00 - Clean & Low-Carbon Hydrogen", name: "Clean & Low-Carbon Hydrogen", isComplex: false },
  { code: "2814 10 00", label: "2814 10 00 - Anhydrous Ammonia", name: "Anhydrous Ammonia", isComplex: false },
  { code: "2808 00 00", label: "2808 00 00 - Nitric Acid", name: "Nitric Acid (Concentrated)", isComplex: true, precName: "Anhydrous Ammonia", precCn: "2814 10 00", precRatio: "0.290" },
  { code: "3102 10 00", label: "3102 10 00 - Urea (Fertilizer)", name: "Technical Grade Urea", isComplex: true, precName: "Anhydrous Ammonia", precCn: "2814 10 00", precRatio: "0.567" },
  { code: "3102 80 00", label: "3102 80 00 - Mixtures of Urea & Ammonium Nitrate (UAN)", name: "Liquid Nitrogen Fertilizers (UAN 32%)", isComplex: true, precName: "Anhydrous Ammonia", precCn: "2814 10 00", precRatio: "0.450" },
  { code: "2709 00 00", label: "2709 00 00 - Crude Petroleum Oil", name: "Crude Petroleum Oil", isComplex: false },
  { code: "2711 11 00", label: "2711 11 00 - Liquefied Natural Gas (LNG)", name: "Liquefied Natural Gas (LNG)", isComplex: false },
  { code: "2711 21 00", label: "2711 21 00 - Pipeline Natural Gas", name: "Pipeline Natural Gas", isComplex: false },
  { code: "2710 12 11", label: "2710 12 11 - Light Naphtha & Refining Cuts", name: "Light Naphtha & Refining Cuts", isComplex: false },
  { code: "2710 19 43", label: "2710 19 43 - Heavy Gas Oil / Diesel", name: "Heavy Gas Oil / Diesel", isComplex: false },
  { code: "2902 20 00", label: "2902 20 00 - Pure Benzene (Petrochemical)", name: "Pure Benzene (Petrochemical)", isComplex: false },
  { code: "2902 43 00", label: "2902 43 00 - Paraxylene (Petrochemical)", name: "Paraxylene (Petrochemical)", isComplex: false },
];

const STANDARD_PRODUCT_NAMES = new Set(CN_OPTIONS.map((c) => c.name));

const formatMetric = (val: number | string | undefined | null, maxDecimals = 2): string => {
  const num = parseFloat(String(val ?? 0));
  if (!Number.isFinite(num)) return "—";
  if (Math.abs(num) >= 1e9) return num.toExponential(3);
  return num.toLocaleString(undefined, { maximumFractionDigits: maxDecimals });
};

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
}) => {
  const toast = useToast();
  const [exporting, setExporting] = useState<boolean>(false);
  const [isCustomCn, setIsCustomCn] = useState<boolean>(false);

  const handleExportCbamExcel = async () => {
    try {
      setExporting(true);
      toast.info(t("Generating EU CBAM Excel Communication Template..."));
      const res = await api.get("/reports/cbam-export?format=excel", {
        responseType: "blob",
      });
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "EU_CBAM_Communication_Template_Consolidated.xlsx";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      toast.success(t("EU CBAM Communication Template downloaded successfully."));
    } catch (err) {
      console.error("CBAM export failed:", err);
      toast.error(t("Failed to export CBAM template."));
    } finally {
      setExporting(false);
    }
  };

  const handleCnCodeChange = (newCode: string) => {
    if (newCode === "Custom") {
      setIsCustomCn(true);
      setCbamForm({ ...cbamForm, cn_code: "" });
      return;
    }
    setIsCustomCn(false);

    const matched = CN_OPTIONS.find((c) => c.code === newCode);
    const extra: Record<string, any> = { cn_code: newCode };

    // Auto-update product name if blank or set to a standard preset
    const currentName = cbamForm.product_name || "";
    if (!currentName || STANDARD_PRODUCT_NAMES.has(currentName)) {
      if (matched?.name) {
        extra.product_name = matched.name;
      }
    }

    if (matched?.isComplex) {
      extra.is_complex_good = true;
      extra.precursor_name = cbamForm.precursor_name || matched.precName || "Anhydrous Ammonia";
      extra.precursor_cn_code = cbamForm.precursor_cn_code || matched.precCn || "2814 10 00";
      extra.precursor_ratio = cbamForm.precursor_ratio || matched.precRatio || "0.567";
      extra.precursor_see_dir = cbamForm.precursor_see_dir || "1.7850";
      extra.precursor_see_indir = cbamForm.precursor_see_indir || "0.1420";
    } else if (matched) {
      extra.is_complex_good = false;
    }

    setCbamForm({ ...cbamForm, ...extra });
  };

  const handlePrecursorToggle = (checked: boolean) => {
    if (checked) {
      setCbamForm({
        ...cbamForm,
        is_complex_good: true,
        precursor_name: cbamForm.precursor_name || "Anhydrous Ammonia",
        precursor_cn_code: cbamForm.precursor_cn_code || "2814 10 00",
        precursor_ratio: cbamForm.precursor_ratio || "0.567",
        precursor_see_dir: cbamForm.precursor_see_dir || "1.7850",
        precursor_see_indir: cbamForm.precursor_see_indir || "0.1420",
      });
    } else {
      setCbamForm({
        ...cbamForm,
        is_complex_good: false,
      });
    }
  };

  const rows = filteredCbam.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

  // Precursor contribution
  const pRatio = parseFloat(String(cbamForm.precursor_ratio || 0));
  const pDir = parseFloat(String(cbamForm.precursor_see_dir || 0));
  const pIndir = parseFloat(String(cbamForm.precursor_see_indir || 0));
  const pContrib = cbamForm.is_complex_good ? pRatio * (pDir + pIndir) : 0;

  // Live Summary metrics
  const quantityVal = parseFloat(String(cbamForm.quantity_tonnes || 0));
  const dirSeeVal = parseFloat(String(cbamForm.specific_embedded_direct || 0));
  const indirSeeVal = parseFloat(String(cbamForm.specific_embedded_indirect || 0));
  const totalSeeVal = dirSeeVal + indirSeeVal + pContrib;
  const totalEmbeddedVal = quantityVal * totalSeeVal;
  const carbonTaxVal = parseFloat(String(cbamForm.carbon_price_paid_eur || 0));

  // Determine current CN code for selector (normalizing 6-digit legacy codes)
  const rawCn = cbamForm.cn_code || "";
  const currentCnCode = rawCn === "2709 00" ? "2709 00 00" : rawCn || "2804 10 00";
  const isKnownCn = CN_OPTIONS.some((o) => o.code === currentCnCode);

  return (
    <TabCard
      title={t("EU CBAM Export & Embedded Emission Tracking (Oil & Gas Scope)")}
      description={t(
        "Record product exports subject to EU Carbon Border Adjustment Mechanism tailored to Oil & Gas operations, including Clean Hydrogen, Ammonia, Fertilizers, Refinery streams, Carbon Capture & Storage (CCS), and Origin Carbon Taxes.",
      )}
    >
      <FormGrid className="form-grid-3" cols="md:grid-cols-3">
        <Field label={t("Activity")}>
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

        <Field label={t("Division")}>
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

        <Field label={t("Facility / Production Site *")}>
          <NativeSelect
            value={cbamForm.facility_id || ""}
            onChange={(e) => {
              const fid = e.target.value;
              const fac = facilities.find((f) => String(f.id) === String(fid));
              setCbamForm({
                ...cbamForm,
                facility_id: fid,
                activity: fac?.activity || cbamForm.activity,
                division: fac?.division || cbamForm.division,
              });
            }}
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

        <Field label={t("EU CN Code (Oil & Gas Scope) *")}>
          <NativeSelect
            value={isCustomCn ? "Custom" : currentCnCode}
            onChange={(e) => handleCnCodeChange(e.target.value)}
            className="component-select"
          >
            {CN_OPTIONS.map((opt) => (
              <option key={opt.code} value={opt.code}>
                {t(opt.label)}
              </option>
            ))}
            {!isKnownCn && currentCnCode && currentCnCode !== "Custom" && (
              <option value={currentCnCode}>{currentCnCode} ({t("Custom / Other")})</option>
            )}
            <option value="Custom">{t("Custom / Other CN Code")}</option>
          </NativeSelect>
        </Field>

        {isCustomCn && (
          <Field label={t("Enter Custom EU CN Code *")}>
            <Input
              type="text"
              value={cbamForm.cn_code || ""}
              onChange={(e) => setCbamForm({ ...cbamForm, cn_code: e.target.value })}
              placeholder={t("e.g. 2710 19 99")}
            />
          </Field>
        )}

        <Field label={t("Commercial Product Name *")}>
          <Input
            type="text"
            value={cbamForm.product_name || ""}
            onChange={(e) => setCbamForm({ ...cbamForm, product_name: e.target.value })}
            placeholder={t("e.g. Clean Blue Hydrogen / Low-Carbon Ammonia")}
          />
        </Field>

        <Field label={t("Export Destination")}>
          <NativeSelect
            value={cbamForm.export_destination || "EU"}
            onChange={(e) => setCbamForm({ ...cbamForm, export_destination: e.target.value })}
            className="component-select"
          >
            <option value="EU">{t("European Union (EU-27)")}</option>
            <option value="UK">{t("United Kingdom (UK CBAM)")}</option>
            <option value="US">{t("United States")}</option>
            <option value="APAC">{t("Asia-Pacific")}</option>
            <option value="Non-EU">{t("Other Non-EU")}</option>
          </NativeSelect>
        </Field>

        <Field label={t("Reporting Year")}>
          <Input
            type="number"
            value={cbamForm.year || ""}
            onChange={(e) => setCbamForm({ ...cbamForm, year: e.target.value })}
          />
        </Field>

        <Field label={t("Reporting Quarter (DG TAXUD)")}>
          <NativeSelect
            value={cbamForm.quarter || "Q1"}
            onChange={(e) => {
              const q = e.target.value;
              const qMonthMap: Record<string, number> = { Q1: 1, Q2: 4, Q3: 7, Q4: 10 };
              setCbamForm({ ...cbamForm, quarter: q, month: qMonthMap[q] || 1 });
            }}
            className="component-select"
          >
            <option value="Q1">{t("Q1 (Jan 01 - Mar 31)")}</option>
            <option value="Q2">{t("Q2 (Apr 01 - Jun 30)")}</option>
            <option value="Q3">{t("Q3 (Jul 01 - Sep 30)")}</option>
            <option value="Q4">{t("Q4 (Oct 01 - Dec 31)")}</option>
          </NativeSelect>
        </Field>

        <Field label={t("Reporting Month")}>
          <NativeSelect
            value={cbamForm.month || 1}
            onChange={(e) => {
              const m = parseInt(e.target.value, 10);
              const q = `Q${Math.floor((m - 1) / 3) + 1}`;
              setCbamForm({ ...cbamForm, month: m, quarter: q });
            }}
            className="component-select"
          >
            {Array.from({ length: 12 }, (_, i) => (
              <option key={i + 1} value={i + 1}>
                {new Date(2000, i).toLocaleString("default", { month: "long" })}
              </option>
            ))}
          </NativeSelect>
        </Field>

        <Field label={t("Export Quantity (Metric Tonnes) *")}>
          <Input
            type="number"
            value={cbamForm.quantity_tonnes || ""}
            onChange={(e) => setCbamForm({ ...cbamForm, quantity_tonnes: e.target.value })}
            placeholder="0.00"
          />
        </Field>

        <Field label={t("Direct Specific Embedded (SEE_dir) (tCO₂e / t)")}>
          <Input
            type="number"
            step="0.0001"
            value={cbamForm.specific_embedded_direct || ""}
            onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_direct: e.target.value })}
            placeholder={t("Auto-calculated from site if 0")}
          />
        </Field>

        <Field label={t("Indirect Specific Embedded (SEE_indir) (tCO₂e / t)")}>
          <Input
            type="number"
            step="0.0001"
            value={cbamForm.specific_embedded_indirect || ""}
            onChange={(e) => setCbamForm({ ...cbamForm, specific_embedded_indirect: e.target.value })}
            placeholder={t("Auto-calculated from Scope 2 if 0")}
          />
        </Field>
      </FormGrid>

      {/* Carbon Capture & Geological Storage (CCS) Section */}
      <div className="mt-6 rounded-xl border border-emerald-200/80 bg-emerald-50/40 p-5 shadow-xs transition-colors">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-emerald-100 pb-3">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="size-5 text-emerald-600" aria-hidden="true" />
            <h4 className="text-sm font-semibold text-text">
              {t("Carbon Capture & Permanent Storage (CCS)")}
            </h4>
          </div>
          <Badge tone="success" className="text-xs">
            {t("Net Direct SEE = max(0, Gross Direct - Captured CO₂) / Quantity")}
          </Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label={t("Captured & Geologically Sequestered CO₂ (Metric Tonnes)")}>
            <Input
              type="number"
              step="0.01"
              value={cbamForm.captured_co2_tonnes || ""}
              onChange={(e) => setCbamForm({ ...cbamForm, captured_co2_tonnes: e.target.value })}
              placeholder="0.00 (e.g. 1540.50)"
            />
          </Field>
          <Field label={t("CCS Geological Storage Certificate ID")}>
            <Input
              type="text"
              value={cbamForm.ccs_certificate_id || ""}
              onChange={(e) => setCbamForm({ ...cbamForm, ccs_certificate_id: e.target.value })}
              placeholder={t("e.g. DZ-CCS-2026-IN-SALAH-001")}
            />
          </Field>
        </div>
      </div>

      {/* Origin Carbon Price / Flaring Tax Section */}
      <div className="mt-5 rounded-xl border border-amber-200/80 bg-amber-50/40 p-5 shadow-xs transition-colors">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-amber-100 pb-3">
          <div className="flex items-center gap-2.5">
            <Coins className="size-5 text-amber-600" aria-hidden="true" />
            <h4 className="text-sm font-semibold text-text">
              {t("Carbon Price & Flaring Fiscality Paid in Country of Origin")}
            </h4>
          </div>
          <Badge tone="warning" className="text-xs">
            {t("Directly credited against EU CBAM certificate surrender")}
          </Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label={t("Carbon Price / Flaring Penalty Rate (€ / t product)")}>
            <Input
              type="number"
              step="0.01"
              value={cbamForm.carbon_price_paid_eur || ""}
              onChange={(e) => setCbamForm({ ...cbamForm, carbon_price_paid_eur: e.target.value })}
              placeholder="0.00 (e.g. 12.50)"
            />
          </Field>
          <Field label={t("National Legal Basis & Fiscal Receipt Reference")}>
            <Input
              type="text"
              value={cbamForm.carbon_price_legal_ref || ""}
              onChange={(e) => setCbamForm({ ...cbamForm, carbon_price_legal_ref: e.target.value })}
              placeholder={t("e.g. Hydrocarbon Law 19-13 Art. 42 / Decree 21-330")}
            />
          </Field>
        </div>
      </div>

      {/* Complex Downstream Goods Precursor Attribution Section */}
      <div className="mt-5 rounded-xl border border-blue-200/80 bg-blue-50/40 p-5 shadow-xs transition-colors">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-blue-100 pb-3">
          <div className="flex items-center gap-2.5">
            <Layers className="size-5 text-blue-600" aria-hidden="true" />
            <h4 className="text-sm font-semibold text-text">
              {t("Complex Downstream Goods & Upstream Precursors (Ammonia / Urea / UAN)")}
            </h4>
          </div>
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm font-medium text-text select-none">
            <input
              type="checkbox"
              checked={Boolean(cbamForm.is_complex_good)}
              onChange={(e) => handlePrecursorToggle(e.target.checked)}
              className="size-4 rounded border-border text-brand-600 focus:ring-brand-500 cursor-pointer"
            />
            <span>{t("Declare Upstream Precursor Attribution")}</span>
          </label>
        </div>

        {cbamForm.is_complex_good && (
          <div className="space-y-4 pt-1">
            <div className="grid gap-4 md:grid-cols-3">
              <Field label={t("Relevant Precursor Name")}>
                <Input
                  type="text"
                  value={cbamForm.precursor_name || ""}
                  onChange={(e) => setCbamForm({ ...cbamForm, precursor_name: e.target.value })}
                  placeholder={t("e.g. Anhydrous Ammonia")}
                />
              </Field>
              <Field label={t("Precursor EU CN Code")}>
                <Input
                  type="text"
                  value={cbamForm.precursor_cn_code || ""}
                  onChange={(e) => setCbamForm({ ...cbamForm, precursor_cn_code: e.target.value })}
                  placeholder="2814 10 00"
                />
              </Field>
              <Field label={t("Consumption Ratio (t precursor / t product)")}>
                <Input
                  type="number"
                  step="0.001"
                  value={cbamForm.precursor_ratio || ""}
                  onChange={(e) => setCbamForm({ ...cbamForm, precursor_ratio: e.target.value })}
                  placeholder="0.567"
                />
              </Field>
            </div>
            <div className="grid gap-4 md:grid-cols-3 items-start">
              <Field label={t("Precursor Direct SEE (tCO₂e / t precursor)")}>
                <Input
                  type="number"
                  step="0.0001"
                  value={cbamForm.precursor_see_dir || ""}
                  onChange={(e) => setCbamForm({ ...cbamForm, precursor_see_dir: e.target.value })}
                  placeholder="1.7850"
                />
              </Field>
              <Field label={t("Precursor Indirect SEE (tCO₂e / t precursor)")}>
                <Input
                  type="number"
                  step="0.0001"
                  value={cbamForm.precursor_see_indir || ""}
                  onChange={(e) => setCbamForm({ ...cbamForm, precursor_see_indir: e.target.value })}
                  placeholder="0.1420"
                />
              </Field>
              <Field label={t("Precursor SEE Contribution (tCO₂e / t)")}>
                <div className="flex min-h-[38px] items-center justify-between rounded-md border border-brand-200 bg-brand-50/90 px-3.5 py-1.5 shadow-xs">
                  <span className="text-xs font-semibold text-brand-900">{t("Total Precursor SEE:")}</span>
                  <span className="font-mono text-sm font-bold text-brand-700">
                    +{pContrib.toFixed(4)} tCO₂e / t
                  </span>
                </div>
              </Field>
            </div>
            <p className="text-xs text-text-secondary mt-1">
              {t("Stoichiometric precursor embedded emissions are automatically added to the product's total declaration.")}
            </p>
          </div>
        )}
      </div>

      <div className="mt-5">
        <Field label={t("Notes & Accredited Verification References")}>
          <Input
            type="text"
            value={cbamForm.notes || ""}
            onChange={(e) => setCbamForm({ ...cbamForm, notes: e.target.value })}
            placeholder={t("Accredited Verifier / ISO 14065 Certificate / Customs Documentation")}
          />
        </Field>
      </div>

      {/* Live Calculated Declaration Summary Strip */}
      <div className="mt-6 rounded-xl border border-border bg-ink-50/80 p-4 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-6">
            <div>
              <span className="block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                {t("Export Quantity")}
              </span>
              <span className="font-mono text-base font-bold text-text">
                {quantityVal > 0 ? quantityVal.toLocaleString() : "0.00"} t
              </span>
            </div>
            <div className="hidden h-8 w-px bg-border sm:block" />
            <div>
              <span className="block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                {t("Direct SEE")}
              </span>
              <span className="font-mono text-base font-bold text-text">
                {dirSeeVal.toFixed(4)} <span className="text-xs font-normal text-text-secondary">tCO₂e/t</span>
              </span>
            </div>
            <div className="hidden h-8 w-px bg-border sm:block" />
            <div>
              <span className="block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                {t("Total Specific SEE")}
              </span>
              <span className="font-mono text-base font-bold text-text">
                {totalSeeVal.toFixed(4)} <span className="text-xs font-normal text-text-secondary">tCO₂e/t</span>
              </span>
            </div>
            <div className="hidden h-8 w-px bg-border sm:block" />
            <div>
              <span className="block text-xs font-semibold uppercase tracking-wider text-text-secondary">
                {t("Total Embedded Emissions")}
              </span>
              <span className="font-mono text-base font-extrabold text-brand-600">
                {totalEmbeddedVal.toLocaleString(undefined, { maximumFractionDigits: 1 })} <span className="text-xs font-normal text-text-secondary">tCO₂e</span>
              </span>
            </div>
          </div>
          {carbonTaxVal > 0 && quantityVal > 0 && (
            <Badge tone="warning" className="text-xs font-medium">
              {t("Origin Tax Credit:")} €{(carbonTaxVal * quantityVal).toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </Badge>
          )}
        </div>
      </div>

      <FormActions className="mt-6">
        <Button className="action-btn" onClick={handleSaveCbamExport}>
          {editingCbamId ? t("Update CBAM Record") : t("Save CBAM Record")}
        </Button>
        {editingCbamId && (
          <Button
            variant="secondary"
            onClick={() => {
              setEditingCbamId(null);
              setIsCustomCn(false);
              setCbamForm({
                id: null,
                activity: "",
                division: "",
                facility_id: "",
                year: new Date().getFullYear(),
                month: 1,
                quarter: "Q1",
                product_name: "Clean & Low-Carbon Hydrogen",
                cn_code: "2804 10 00",
                quantity_tonnes: "",
                export_destination: "EU",
                specific_embedded_direct: "",
                specific_embedded_indirect: "",
                captured_co2_tonnes: "",
                ccs_certificate_id: "",
                carbon_price_paid_eur: "",
                carbon_price_legal_ref: "",
                is_complex_good: false,
                precursor_name: "",
                precursor_cn_code: "",
                precursor_ratio: "",
                precursor_see_dir: "",
                precursor_see_indir: "",
                notes: "",
              });
            }}
          >
            {t("Cancel Edit")}
          </Button>
        )}
      </FormActions>

      <RecordTable
        title={
          <span className="flex flex-wrap items-center justify-between gap-3">
            <span className="flex items-center gap-2">
              <Landmark className="size-5 text-brand-600" aria-hidden="true" />
              <span>{t("CBAM Product Export Records (Oil & Gas Scope)")}</span>
              <span className="text-sm font-normal text-text-secondary">
                ({t("Total Records:")} {filteredCbam.length})
              </span>
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleExportCbamExcel}
              disabled={exporting}
              className="inline-flex items-center gap-1.5"
            >
              <FileSpreadsheet className="size-4 text-emerald-600" aria-hidden="true" />
              {exporting ? t("Exporting...") : t("Export Official CBAM Template")}
            </Button>
          </span>
        }
        head={[
          t("Facility"),
          t("Product"),
          t("EU CN Code"),
          t("Period"),
          t("Destination"),
          <span key="qty" className="block text-right">{t("Quantity (t)")}</span>,
          <span key="ccs" className="block text-right">{t("CCS Captured (t)")}</span>,
          <span key="dir" className="block text-right">{t("Direct SEE")}</span>,
          <span key="indir" className="block text-right">{t("Indirect SEE")}</span>,
          <span key="prec" className="block text-right">{t("Precursor SEE")}</span>,
          <span key="tot" className="block text-right">{t("Total Embedded (tCO₂e)")}</span>,
          <span key="tax" className="block text-right">{t("Origin Tax (€/t)")}</span>,
          <span key="act" className="block text-center">{t("Actions")}</span>,
        ]}
        empty={filteredCbam.length === 0 && t("No CBAM product export records found.")}
        footer={
          <PaginationControls
            currentPage={currentPage}
            totalItems={filteredCbam.length}
            itemsPerPage={ITEMS_PER_PAGE}
            onPageChange={setCurrentPage}
          />
        }
      >
        {rows.map((c) => {
          const fid = c.facility_id || c.facilityId;
          const fac = facilities.find((f) => String(f.id) === String(fid));
          const fName = c.facility_name || c.facilityName || fac?.name || (fid ? `Facility #${fid}` : "—");
          const pName = c.product_name || c.productName || "Product";
          const rawRowCn = c.cn_code || c.cnCode || "-";
          const cnCode = rawRowCn === "2709 00" ? "2709 00 00" : rawRowCn;
          const dest = c.export_destination || c.exportDestination || "EU";
          const qTonnes = parseFloat(String(c.quantity_tonnes ?? c.quantityTonnes ?? 0));
          const direct = parseFloat(String(c.specific_embedded_direct ?? c.specificEmbeddedDirect ?? 0));
          const indirect = parseFloat(String(c.specific_embedded_indirect ?? c.specificEmbeddedIndirect ?? 0));
          const ccsCaptured = parseFloat(String(c.captured_co2_tonnes ?? c.capturedCo2Tonnes ?? 0));
          const isComplex = Boolean(c.is_complex_good || c.isComplexGood);
          const precRatio = parseFloat(String(c.precursor_ratio ?? c.precursorRatio ?? 0));
          const precDir = parseFloat(String(c.precursor_see_dir ?? c.precursorSeeDir ?? 0));
          const precIndir = parseFloat(String(c.precursor_see_indir ?? c.precursorSeeIndir ?? 0));
          const precContrib = isComplex ? precRatio * (precDir + precIndir) : 0;
          const totalSee = direct + indirect + precContrib;
          const totalEmbedded = totalSee * qTonnes;
          const originTax = parseFloat(String(c.carbon_price_paid_eur ?? c.carbonPricePaidEur ?? 0));
          const qtr = c.quarter || `Q${Math.floor(((parseInt(String(c.month || 1), 10) - 1) / 3)) + 1}`;

          return (
            <Tr key={c.id}>
              <Td className="max-w-[180px] truncate" title={fName}>
                <strong className="font-semibold text-text">{fName}</strong>
              </Td>
              <Td className="max-w-[200px] truncate font-medium text-text" title={pName}>
                {pName}
              </Td>
              <Td className="whitespace-nowrap">
                <code className="rounded bg-ink-100 px-1.5 py-0.5 font-mono text-xs text-text">
                  {cnCode}
                </code>
              </Td>
              <Td className="whitespace-nowrap text-text-secondary text-xs">
                {c.year} - {qtr} (M{c.month || "1"})
              </Td>
              <Td className="whitespace-nowrap">
                <Badge tone="brand" className="text-xs">
                  {dest}
                </Badge>
              </Td>
              <Td className="text-right font-semibold text-text whitespace-nowrap">
                {formatMetric(qTonnes)}
              </Td>
              <Td className="text-right whitespace-nowrap">
                {ccsCaptured > 0 ? (
                  <Badge tone="success" className="text-xs font-mono">
                    -{formatMetric(ccsCaptured)} t
                  </Badge>
                ) : (
                  <span className="text-text-secondary">—</span>
                )}
              </Td>
              <Td className="text-right font-mono text-xs text-text-secondary whitespace-nowrap">
                {direct.toFixed(4)}
              </Td>
              <Td className="text-right font-mono text-xs text-text-secondary whitespace-nowrap">
                {indirect.toFixed(4)}
              </Td>
              <Td className="text-right font-mono text-xs text-text-secondary whitespace-nowrap">
                {precContrib > 0 ? `+${precContrib.toFixed(4)}` : "—"}
              </Td>
              <Td className="text-right font-bold text-brand-700 font-mono whitespace-nowrap">
                {formatMetric(totalEmbedded, 1)}
              </Td>
              <Td className="text-right font-mono whitespace-nowrap">
                {originTax > 0 ? (
                  <Badge tone="warning" className="text-xs">
                    €{originTax.toFixed(2)}
                  </Badge>
                ) : (
                  <span className="text-text-secondary">—</span>
                )}
              </Td>
              <Td className="text-center whitespace-nowrap">
                <div className="flex items-center justify-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setEditingCbamId(c.id);
                      setIsCustomCn(!CN_OPTIONS.some((o) => o.code === cnCode));
                      setCbamForm({
                        id: c.id,
                        activity: fac?.activity || "",
                        division: fac?.division || "",
                        facility_id: fid ? fid.toString() : "",
                        year: c.year,
                        month: c.month || 1,
                        quarter: qtr,
                        product_name: pName,
                        cn_code: cnCode,
                        quantity_tonnes: qTonnes.toString(),
                        export_destination: dest,
                        specific_embedded_direct: direct ? direct.toString() : "",
                        specific_embedded_indirect: indirect ? indirect.toString() : "",
                        captured_co2_tonnes: ccsCaptured ? ccsCaptured.toString() : "",
                        ccs_certificate_id: c.ccs_certificate_id || c.ccsCertificateId || "",
                        carbon_price_paid_eur: originTax ? originTax.toString() : "",
                        carbon_price_legal_ref: c.carbon_price_legal_ref || c.carbonPriceLegalRef || "",
                        is_complex_good: isComplex,
                        precursor_name: c.precursor_name || c.precursorName || "",
                        precursor_cn_code: c.precursor_cn_code || c.precursorCnCode || "",
                        precursor_ratio: precRatio ? precRatio.toString() : "",
                        precursor_see_dir: precDir ? precDir.toString() : "",
                        precursor_see_indir: precIndir ? precIndir.toString() : "",
                        notes: c.notes || "",
                      });
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                  >
                    {t("Edit")}
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    onClick={() => handleDeleteCbamExport(c.id)}
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

export default CbamTab;
