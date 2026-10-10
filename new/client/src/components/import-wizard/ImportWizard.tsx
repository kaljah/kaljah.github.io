import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Papa, { ParseResult } from "papaparse";
import { ArrowLeft, ChevronRight, Search, Wand2, File as FileIcon, X } from "lucide-react";
import { Banner, Button, Dialog, IconButton, Input, Stepper } from "../../ui";
import { cn } from "../../ui/cn";
import api from "../../api";
import { autoDetectMapping, missingRequiredFields } from "../../utils/importMapping";
import { useToast } from "../Toast";
import UploadProgress from "../UploadProgress";
import { FieldGroup, FieldGroupData, FileDrop, InfoNote, RegionAccess } from "./mapping";
import { fittingMappings, withSavedMapping, type SavedMapping } from "../../utils/savedMappings";
import { EMPTY_CHECK, FileCheckPanel, type FileCheckState } from "./FileCheck";
import { SavedMappingBar } from "./SavedMappingBar";
import { t } from "../../i18n";

const DECIMAL_MARKS: { value: "comma" | "point"; label: string; example: string }[] = [
  { value: "comma", label: t("Decimal comma"), example: "1 234,5" },
  { value: "point", label: t("Decimal point"), example: "1,234.5" },
];

export interface ImportWizardMode {
  value: string;
  label: string;
}

export interface ImportWizardPreStep {
  label: string;
  content: React.ReactNode;
  canNext?: boolean;
}

export interface ImportWizardProps {
  title: string;
  subtitle?: string;
  modes?: ImportWizardMode[];
  fieldGroupsFor: (mode?: string) => FieldGroupData[];
  scopeFor: (mode?: string) => string;
  preSteps?: ImportWizardPreStep[];
  fieldFilter?: (group: FieldGroupData, field: any) => boolean;
  fileExtras?: React.ReactNode;
  mappingExtras?: React.ReactNode;
  extraForm?: (form: FormData) => void;
  finalLabel?: string;
  overwriteLabel?: string;
  overwriteHint?: string;
  reviewable?: boolean;
  regionAccess?: boolean;
  /** check the file before importing (POST /emissions/upload/check: a sample is calculated, nothing saved) */
  checkBeforeImport?: boolean;
  /** changes when an option outside the wizard that the upload sends (extraForm) changes: a check becomes out of date */
  optionsKey?: string;
  /** keys always offered in the short field list (besides the mapped and the missing required fields) */
  alwaysShownKeys?: string[];
  onClose: () => void;
  onUploadSuccess?: () => void;
}

/**
 * Bulk import wizard for CSV/Excel files: pick a file, map its columns to system fields, then start the server-side job.
 * `modes` (optional) lets one wizard serve several column layouts; `fieldGroupsFor(mode)` and `scopeFor(mode)` pick them.
 * `preSteps` ({ label, content, canNext }) add choices before the file step; `fieldFilter` hides fields that do not apply to
 * those choices; `fileExtras` / `mappingExtras` add content to the file and mapping steps; `extraForm` adds upload fields.
 */
export const ImportWizard: React.FC<ImportWizardProps> = ({
  title,
  subtitle,
  modes,
  fieldGroupsFor,
  scopeFor,
  preSteps = [],
  fieldFilter,
  fileExtras,
  mappingExtras,
  extraForm,
  finalLabel = t("Import"),
  overwriteLabel = t("Overwrite records that already exist (same facility, month and source). Overwritten records go back to Pending review."),
  overwriteHint,
  reviewable = true,
  regionAccess = true,
  checkBeforeImport = false,
  optionsKey = "",
  alwaysShownKeys = [],
  onClose,
  onUploadSuccess,
}) => {
  const toast = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<string | undefined>(modes?.[0]?.value);
  const offset = preSteps.length;
  const FILE = offset + 1;
  const MAP = offset + 2;
  const RUN = offset + 3;
  const [step, setStep] = useState<number>(1);
  const stepLabels = [...preSteps.map((p) => p.label), t("Select file"), t("Map columns"), finalLabel];
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState<boolean>(false);
  const [parseError, setParseError] = useState<string>("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [overwrite, setOverwrite] = useState<boolean>(false); // replace records that already exist
  // How the file writes decimals: chosen per file, never guessed ("1,000" is 1000 in English, 1 in French)
  const [decimalMark, setDecimalMark] = useState<"comma" | "point" | null>(null);
  const [allowedRegions, setAllowedRegions] = useState<string[] | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);
  const [maxBytes, setMaxBytes] = useState<number | null>(null); // server upload limit, checked when a file is picked
  const [savedMappings, setSavedMappings] = useState<SavedMapping[]>([]);
  const [appliedSaved, setAppliedSaved] = useState<SavedMapping | null>(null);
  const [showAllFields, setShowAllFields] = useState<boolean>(false);
  const [check, setCheck] = useState<FileCheckState>(EMPTY_CHECK);
  const scope = scopeFor(mode);

  useEffect(() => {
    api
      .get("/facilities/")
      .then((res) => setAllowedRegions((res.data || []).map((f: any) => f.name)))
      .catch(() => setAllowedRegions([]));
    api
      .get("/auth/me")
      .then((res) => {
        const role = res.data?.role;
        setIsAdmin(role === "admin");
      })
      .catch(() => {});
    api
      .get("/emissions/upload/limits")
      .then((res) => setMaxBytes(res.data?.max_bytes || null))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api
      .get("/emissions/upload/mappings", { params: { scope } })
      .then((res) => setSavedMappings(Array.isArray(res.data) ? res.data : []))
      .catch(() => setSavedMappings([]));
  }, [scope]);

  const groups = useMemo(() => fieldGroupsFor(mode), [fieldGroupsFor, mode]);
  const allFields = useMemo(() => groups.flatMap((g) => g.fields), [groups]);
  const missingRequired = missingRequiredFields(allFields, mapping);
  const canSubmit = missingRequired.length === 0 || headers.length === 0;
  // short list by default: the fields mapped to the file's columns, required fields still missing, and alwaysShownKeys
  const shortList = useMemo(
    () => new Set([...alwaysShownKeys, ...Object.keys(mapping).filter((k) => mapping[k]), ...missingRequired.map((f) => f.key)]),
    [alwaysShownKeys, mapping, missingRequired],
  );
  const compact = headers.length > 0 && !showAllFields && !searchQuery;
  const matchedColumns = useMemo(() => new Set(Object.values(mapping).filter(Boolean)), [mapping]);
  const fitting = useMemo(() => fittingMappings(savedMappings, headers), [savedMappings, headers]);
  const shownGroups = useMemo(
    () =>
      groups
        .map((g) => ({ ...g, fields: g.fields.filter((f) => (!fieldFilter || fieldFilter(g, f)) && (!compact || shortList.has(f.key))) }))
        .filter((g) => g.fields.length),
    [groups, fieldFilter, compact, shortList],
  );
  const restricted = regionAccess && !isAdmin && allowedRegions !== null;
  const noRegions = restricted && allowedRegions.length === 0;

  const processFile = useCallback(
    (f: File | null | undefined) => {
      if (!f) return;
      if (!decimalMark) {
        setParseError(t("Choose how decimals are written in the file first."));
        return;
      }
      setParseError("");
      setCheck(EMPTY_CHECK);
      if (maxBytes && f.size > maxBytes) {
        // refused when picked, not after the upload
        setParseError(t("This file is {{size}} MB; the upload limit is {{limit}} MB. Split it into smaller files.", { size: (f.size / 1048576).toFixed(1), limit: (maxBytes / 1048576).toFixed(0) }));
        return;
      }
      if (f.name.toLowerCase().endsWith(".xlsx")) {
        setFile(f);
        setHeaders([]);
        setMapping({});
        setAppliedSaved(null);
        setStep(MAP);
        return;
      }
      Papa.parse(f, {
        preview: 5,
        header: true,
        skipEmptyLines: true,
        complete: (results: ParseResult<Record<string, any>>) => {
          if (!results.meta.fields?.length) {
            setParseError(t("Could not read column headers. Make sure the file has a header row."));
            return;
          }
          const hdrs = results.meta.fields;
          const { mapping: m, applied } = withSavedMapping(autoDetectMapping(hdrs, allFields), savedMappings, hdrs);
          setHeaders(hdrs);
          setMapping(m);
          setAppliedSaved(applied);
          setFile(f);
          setStep(MAP);
        },
        error: () => setParseError(t("Failed to parse file. Please ensure it is a valid CSV.")),
      });
    },
    [allFields, MAP, maxBytes, savedMappings, decimalMark],
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    processFile(e.dataTransfer.files[0]);
  };
  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    processFile(e.target.files?.[0]);
    e.target.value = "";
  };

  const uploadForm = (f: File) => {
    const form = new FormData();
    form.append("file", f);
    form.append("scope", scope);
    form.append("overwrite_duplicates", overwrite ? "true" : "false");
    if (decimalMark) form.append("decimal_mark", decimalMark);
    extraForm?.(form);
    form.append("column_mapping", JSON.stringify(mapping));
    return form;
  };

  // Check the file: the server calculates a sample spread over the file and counts every row; nothing is saved
  const skipStaleRef = useRef(false); // the mapping was just set from the check's own column names
  const [recheck, setRecheck] = useState(false);
  const runCheck = useCallback(async () => {
    if (!file) return;
    setCheck({ ...EMPTY_CHECK, loading: true });
    const form = uploadForm(file);
    form.append("sample_rows", "2000");
    try {
      const res = await api.post("/emissions/upload/check", form, { headers: { "Content-Type": "multipart/form-data" } });
      setCheck({ ...EMPTY_CHECK, data: res.data });
      const xlHeaders = res.data?.preview?.columns?.headers;
      if (headers.length === 0 && Array.isArray(xlHeaders) && xlHeaders.length) {
        // Excel: the mapping can be shown now that the column names are known; a saved mapping that fits is
        // applied and the file checked again with it
        const { mapping: m, applied } = withSavedMapping(autoDetectMapping(xlHeaders, allFields), savedMappings, xlHeaders);
        skipStaleRef.current = !applied;
        setHeaders(xlHeaders);
        setMapping(m);
        setAppliedSaved(applied);
        if (applied) setRecheck(true);
      }
    } catch (err: any) {
      setCheck({ ...EMPTY_CHECK, error: err.response?.data?.error || err.message });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file, scope, overwrite, decimalMark, mapping, headers.length, allFields, savedMappings, extraForm]);

  // first check when the mapping step opens; later changes only mark the result out of date
  const checkedFileRef = useRef<File | null>(null);
  useEffect(() => {
    if (checkBeforeImport && step === MAP && file && checkedFileRef.current !== file && (headers.length === 0 || canSubmit)) {
      checkedFileRef.current = file;
      runCheck();
    }
  }, [checkBeforeImport, step, MAP, file, headers.length, canSubmit, runCheck]);
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    if (skipStaleRef.current) {
      skipStaleRef.current = false;
      return;
    }
    setCheck((c) => (c.data || c.error ? { ...c, stale: true } : c));
  }, [mapping, overwrite, decimalMark, optionsKey]);
  useEffect(() => {
    if (recheck) {
      setRecheck(false);
      runCheck();
    }
  }, [recheck, runCheck]);

  const applySaved = (m: SavedMapping | null) => {
    const auto = autoDetectMapping(headers, allFields);
    setMapping(m ? { ...auto, ...m.mapping } : auto);
    setAppliedSaved(m);
  };
  const saveMapping = async (name: string) => {
    try {
      const res = await api.post("/emissions/upload/mappings", { scope, name, headers, mapping });
      setSavedMappings((list) => [res.data, ...list.filter((x) => x.id !== res.data.id)]);
      setAppliedSaved(res.data);
      toast.success(t("Mapping \"{{name}}\" saved: it will be applied to files with these columns.", { name }));
      return true;
    } catch (err: any) {
      toast.error(err.response?.data?.error || t("The mapping could not be saved."));
      return false;
    }
  };

  const handleSubmit = async () => {
    if (!file) return;
    setSubmitting(true);
    try {
      const res = await api.post("/emissions/upload/start", uploadForm(file), { headers: { "Content-Type": "multipart/form-data" } });
      setJobId(res.data.job_id);
      if (appliedSaved) api.post(`/emissions/upload/mappings/${appliedSaved.id}/used`).catch(() => {});
      setStep(RUN);
    } catch (err: any) {
      const msg =
        err.response?.data?.error ||
        (err.response?.status === 413 ? t("The file is larger than the server's upload limit; split it into smaller files.") : err.message);
      toast.error(t("Upload error: {{message}}", { message: msg }));
    } finally {
      setSubmitting(false);
    }
  };
  const preview = check.data?.preview;
  const startLabel = submitting
    ? t("Starting…")
    : preview
      ? preview.is_estimate
        ? t("Import about {{count}} rows", { count: preview.estimated_ok.toLocaleString("en-US") })
        : t("Import {{count}} rows", { count: preview.estimated_ok.toLocaleString("en-US") })
      : t("Start import");

  const preStep = step <= offset ? preSteps[step - 1] : null;
  const footer =
    step === RUN ? null : (
      <div className="flex w-full items-center justify-between">
        <Button variant="secondary" onClick={step === 1 ? onClose : () => setStep((s) => s - 1)}>
          {step === 1 ? <X className="size-4" aria-hidden="true" /> : <ArrowLeft className="size-4" aria-hidden="true" />}
          {step === 1 ? t("Cancel") : t("Back")}
        </Button>
        {step === MAP ? (
          <Button
            onClick={handleSubmit}
            loading={submitting}
            disabled={submitting || (!canSubmit && headers.length > 0) || noRegions || (!!preview && !check.stale && !preview.is_estimate && preview.estimated_ok === 0)}
          >
            {startLabel}
          </Button>
        ) : (
          <Button onClick={() => setStep((s) => s + 1)} disabled={step === FILE ? !file : preStep?.canNext === false}>
            {t("Next")}{" "}<ChevronRight className="size-4" aria-hidden="true" />
          </Button>
        )}
      </div>
    );

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} title={title} description={subtitle} maxWidth="52rem" dismissible={step !== RUN} footer={footer}>
      <div className="flex flex-col gap-4">
        <Stepper steps={stepLabels} current={step - 1} />

        {preStep && preStep.content}

        {step === FILE && (
          <>
            {modes && (
              <div role="radiogroup" aria-label={t("Import type")} className="flex gap-2">
                {modes.map((m) => (
                  <Button key={m.value} role="radio" aria-checked={mode === m.value} variant={mode === m.value ? "primary" : "secondary"} size="sm" onClick={() => setMode(m.value)}>
                    {m.label}
                  </Button>
                ))}
              </div>
            )}
            {restricted && allowedRegions && <RegionAccess regions={allowedRegions} />}
            <div className="flex flex-col gap-2">
              <p id="decimal-mark-label" className="m-0 text-sm font-semibold text-text">
                {t("How are decimals written in this file?")}
              </p>
              <div role="radiogroup" aria-labelledby="decimal-mark-label" className="flex flex-wrap gap-2">
                {DECIMAL_MARKS.map((d) => (
                  <Button
                    key={d.value}
                    role="radio"
                    aria-checked={decimalMark === d.value}
                    variant={decimalMark === d.value ? "primary" : "secondary"}
                    size="sm"
                    onClick={() => {
                      setDecimalMark(d.value);
                      setParseError("");
                    }}
                  >
                    {d.label} <span className="font-mono">{d.example}</span>
                  </Button>
                ))}
              </div>
              <p className="m-0 text-xs text-text-secondary">
                {t("Applies to CSV files and numbers typed as text in Excel. A number that does not match is reported, not guessed.")}
              </p>
            </div>
            <FileDrop inputRef={fileInputRef} dragging={dragging} onDragging={setDragging} onDrop={onDrop} onFileChange={onFileChange} error={parseError} />
            {maxBytes && <p className="m-0 text-xs text-text-secondary">{t("Up to")}{" "}{(maxBytes / 1048576).toFixed(0)}{" "}{t("MB per file · no row limit")}</p>}
            {fileExtras}
          </>
        )}

        {step === MAP && (
          <>
            {restricted && allowedRegions && <RegionAccess regions={allowedRegions} compact />}
            {file && (
              <div className="flex items-center gap-3 rounded-md border border-border bg-ink-50 px-4 py-3">
                <span className="flex size-9 items-center justify-center rounded-md bg-brand-50 text-brand-700">
                  <FileIcon className="size-[18px]" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="m-0 truncate text-base font-semibold text-text">{file.name}</p>
                  <p className="m-0 text-sm text-text-secondary">
                    {(file.size / 1024).toFixed(1)} KB
                    {decimalMark && ` · ${DECIMAL_MARKS.find((d) => d.value === decimalMark)?.label.toLowerCase()} (${DECIMAL_MARKS.find((d) => d.value === decimalMark)?.example})`}
                  </p>
                </div>
                {headers.length > 0 && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-success-bg px-2.5 py-1 text-xs font-semibold text-success-fg">
                    <Wand2 className="size-3.5" aria-hidden="true" /> {headers.filter((h) => matchedColumns.has(h)).length}{" "}{t("of")}{" "}{headers.length}{" "}{t("columns matched")}
                  </span>
                )}
              </div>
            )}
            {headers.length === 0 && (
              <InfoNote>
                {checkBeforeImport
                  ? t("Excel file: reading its columns with the check below. The column mapping appears when the check is done.")
                  : t("Excel file — processed server-side. Type column names exactly as they appear in your file, or leave blank to skip that field.")}
              </InfoNote>
            )}
            {headers.length > 0 && (
              <SavedMappingBar
                applied={appliedSaved}
                fitting={fitting}
                canSave={matchedColumns.size > 0}
                defaultName={(file?.name || "").replace(/\.[^.]+$/, "").slice(0, 80)}
                onApply={applySaved}
                onSave={saveMapping}
              />
            )}
            {headers.length > 0 && missingRequired.length > 0 && (
              <Banner tone="warning">
                <strong>
                  {missingRequired.length}{" "}{t("required field")}{missingRequired.length > 1 ? "s" : ""}{" "}{t("not mapped:")}
                </strong>{" "}
                {missingRequired.map((f) => f.label).join(", ")}
              </Banner>
            )}

            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
              <Input
                aria-label={t("Search fields")}
                className="pl-9 pr-9"
                placeholder={t("Search fields by name, key, or description…")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <IconButton label={t("Clear search")} className="absolute right-1 top-1/2 size-7 -translate-y-1/2" onClick={() => setSearchQuery("")}>
                  <X className="size-3.5" aria-hidden="true" />
                </IconButton>
              )}
            </div>

            {mappingExtras}

            {checkBeforeImport && <FileCheckPanel
                check={check}
                onRecheck={runCheck}
                canRun={headers.length === 0 || canSubmit}
                mappedHere={headers.length ? headers.filter((h) => matchedColumns.has(h)).length : undefined}
              />}

            <label className={cn("flex cursor-pointer items-start gap-2 text-sm font-medium text-text-secondary")}>
              <input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-brand-500" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
              <span className="min-w-0 flex-1">
                {overwriteLabel}
                {overwriteHint && <span className="block text-xs font-normal">{overwriteHint}</span>}
              </span>
            </label>

            {headers.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-text-secondary">
                <span>{showAllFields ? t("All fields are shown.") : t("Showing the fields matched to your file and any required field still missing.")}</span>
                <Button variant="link" size="sm" className="h-auto px-0" onClick={() => setShowAllFields((v) => !v)}>
                  {showAllFields ? t("Show only my file's fields") : t("Show all fields")}
                </Button>
              </div>
            )}

            <div className="flex flex-col gap-2.5">
              {shownGroups.map((group) => (
                <FieldGroup key={group.label} group={group} headers={headers} mapping={mapping} setMapping={setMapping} searchQuery={searchQuery} />
              ))}
            </div>
          </>
        )}

        {step === RUN && jobId && (
          <UploadProgress
            jobId={jobId}
            reviewable={reviewable}
            onComplete={() => {
              if (onUploadSuccess) onUploadSuccess();
              onClose();
            }}
            onCancel={onClose}
          />
        )}
      </div>
    </Dialog>
  );
};

export default ImportWizard;
