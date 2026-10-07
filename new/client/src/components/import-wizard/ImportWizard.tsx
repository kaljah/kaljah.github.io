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
  finalLabel = "Import",
  overwriteLabel = "Overwrite records that already exist (same facility, month and source). Overwritten records go back to Pending review.",
  overwriteHint,
  reviewable = true,
  regionAccess = true,
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
  const stepLabels = [...preSteps.map((p) => p.label), "Select file", "Map columns", finalLabel];
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState<boolean>(false);
  const [parseError, setParseError] = useState<string>("");
  const [headers, setHeaders] = useState<string[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [overwrite, setOverwrite] = useState<boolean>(false); // replace records that already exist
  const [allowedRegions, setAllowedRegions] = useState<string[] | null>(null);
  const [isAdmin, setIsAdmin] = useState<boolean>(false);

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
  }, []);

  const groups = useMemo(() => fieldGroupsFor(mode), [fieldGroupsFor, mode]);
  const allFields = useMemo(() => groups.flatMap((g) => g.fields), [groups]);
  const shownGroups = useMemo(
    () => groups.map((g) => ({ ...g, fields: g.fields.filter((f) => !fieldFilter || fieldFilter(g, f)) })).filter((g) => g.fields.length),
    [groups, fieldFilter],
  );
  const missingRequired = missingRequiredFields(allFields, mapping);
  const canSubmit = missingRequired.length === 0 || headers.length === 0;
  const restricted = regionAccess && !isAdmin && allowedRegions !== null;
  const noRegions = restricted && allowedRegions.length === 0;

  const processFile = useCallback(
    (f: File | null | undefined) => {
      if (!f) return;
      setParseError("");
      if (f.name.toLowerCase().endsWith(".xlsx")) {
        setFile(f);
        setHeaders([]);
        setMapping({});
        setStep(MAP);
        return;
      }
      Papa.parse(f, {
        preview: 5,
        header: true,
        skipEmptyLines: true,
        complete: (results: ParseResult<Record<string, any>>) => {
          if (!results.meta.fields?.length) {
            setParseError("Could not read column headers. Make sure the file has a header row.");
            return;
          }
          const hdrs = results.meta.fields;
          setHeaders(hdrs);
          setMapping(autoDetectMapping(hdrs, allFields));
          setFile(f);
          setStep(MAP);
        },
        error: () => setParseError("Failed to parse file. Please ensure it is a valid CSV."),
      });
    },
    [allFields, MAP],
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

  const handleSubmit = async () => {
    if (!file) return;
    setSubmitting(true);
    const form = new FormData();
    form.append("file", file);
    form.append("scope", scopeFor(mode));
    form.append("overwrite_duplicates", overwrite ? "true" : "false");
    extraForm?.(form);
    form.append("column_mapping", JSON.stringify(mapping));
    try {
      const res = await api.post("/emissions/upload/start", form, { headers: { "Content-Type": "multipart/form-data" } });
      setJobId(res.data.job_id);
      setStep(RUN);
    } catch (err: any) {
      toast.error("Upload error: " + (err.response?.data?.error || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const preStep = step <= offset ? preSteps[step - 1] : null;
  const footer =
    step === RUN ? null : (
      <div className="flex w-full items-center justify-between">
        <Button variant="secondary" onClick={step === 1 ? onClose : () => setStep((s) => s - 1)}>
          {step === 1 ? <X className="size-4" aria-hidden="true" /> : <ArrowLeft className="size-4" aria-hidden="true" />}
          {step === 1 ? "Cancel" : "Back"}
        </Button>
        {step === MAP ? (
          <Button onClick={handleSubmit} loading={submitting} disabled={submitting || (!canSubmit && headers.length > 0) || noRegions}>
            {submitting ? "Starting…" : "Start import"}
          </Button>
        ) : (
          <Button onClick={() => setStep((s) => s + 1)} disabled={step === FILE ? !file : preStep?.canNext === false}>
            Next <ChevronRight className="size-4" aria-hidden="true" />
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
              <div role="radiogroup" aria-label="Import type" className="flex gap-2">
                {modes.map((m) => (
                  <Button key={m.value} role="radio" aria-checked={mode === m.value} variant={mode === m.value ? "primary" : "secondary"} size="sm" onClick={() => setMode(m.value)}>
                    {m.label}
                  </Button>
                ))}
              </div>
            )}
            {restricted && allowedRegions && <RegionAccess regions={allowedRegions} />}
            <FileDrop inputRef={fileInputRef} dragging={dragging} onDragging={setDragging} onDrop={onDrop} onFileChange={onFileChange} error={parseError} />
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
                  <p className="m-0 text-sm text-text-secondary">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                {headers.length > 0 && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-success-bg px-2.5 py-1 text-xs font-semibold text-success-fg">
                    <Wand2 className="size-3.5" aria-hidden="true" /> {Object.keys(mapping).length} auto-detected
                  </span>
                )}
              </div>
            )}
            {headers.length === 0 && (
              <InfoNote>Excel file — processed server-side. Type column names exactly as they appear in your file, or leave blank to skip that field.</InfoNote>
            )}
            {headers.length > 0 && missingRequired.length > 0 && (
              <Banner tone="warning">
                <strong>
                  {missingRequired.length} required field{missingRequired.length > 1 ? "s" : ""} not mapped:
                </strong>{" "}
                {missingRequired.map((f) => f.label).join(", ")}
              </Banner>
            )}

            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
              <Input
                aria-label="Search fields"
                className="pl-9 pr-9"
                placeholder="Search fields by name, key, or description…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <IconButton label="Clear search" className="absolute right-1 top-1/2 size-7 -translate-y-1/2" onClick={() => setSearchQuery("")}>
                  <X className="size-3.5" aria-hidden="true" />
                </IconButton>
              )}
            </div>

            {mappingExtras}

            <label className={cn("flex cursor-pointer flex-wrap items-center gap-2 text-sm font-medium text-text-secondary")}>
              <input type="checkbox" className="size-4 accent-brand-500" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
              <span>
                {overwriteLabel}
                {overwriteHint && <span className="block text-xs font-normal">{overwriteHint}</span>}
              </span>
            </label>

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
