import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Papa from "papaparse";
import { ArrowLeft, ChevronRight, Search, TriangleAlert, Wand2, File as FileIcon, X } from "lucide-react";
import { Banner, Button, Dialog, IconButton, Input, Stepper } from "../../ui";
import { cn } from "../../ui/cn";
import api from "../../api";
import { autoDetectMapping, missingRequiredFields } from "../../utils/importMapping";
import { useToast } from "../Toast";
import UploadProgress from "../UploadProgress";
import { FieldGroup, FileDrop, InfoNote, RegionAccess } from "./mapping";

const STEPS = ["Select file", "Map columns", "Import"];

/**
 * Bulk import wizard for CSV/Excel files: pick a file, map its columns to system fields, then start the server-side job.
 * `modes` (optional) lets one wizard serve several column layouts; `fieldGroupsFor(mode)` and `scopeFor(mode)` pick them.
 */
const ImportWizard = ({ title, subtitle, modes, fieldGroupsFor, scopeFor, onClose, onUploadSuccess }) => {
  const toast = useToast();
  const fileInputRef = useRef(null);
  const [mode, setMode] = useState(modes?.[0]?.value);
  const [step, setStep] = useState(1);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [parseError, setParseError] = useState("");
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({});
  const [searchQuery, setSearchQuery] = useState("");
  const [jobId, setJobId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [overwrite, setOverwrite] = useState(false); // replace records that already exist
  const [allowedRegions, setAllowedRegions] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    api
      .get("/facilities/")
      .then((res) => setAllowedRegions(res.data.map((f) => f.name)))
      .catch(() => setAllowedRegions([]));
    api
      .get("/auth/me")
      .then((res) => {
        const role = res.data?.role;
        setIsAdmin(role === "admin" || (role === "superuser" && res.data?.location === "all"));
      })
      .catch(() => {});
  }, []);

  const groups = useMemo(() => fieldGroupsFor(mode), [fieldGroupsFor, mode]);
  const allFields = useMemo(() => groups.flatMap((g) => g.fields), [groups]);
  const missingRequired = missingRequiredFields(allFields, mapping);
  const canSubmit = missingRequired.length === 0 || headers.length === 0;
  const restricted = !isAdmin && allowedRegions !== null;
  const noRegions = restricted && allowedRegions.length === 0;

  const processFile = useCallback(
    (f) => {
      if (!f) return;
      setParseError("");
      if (f.name.toLowerCase().endsWith(".xlsx")) {
        setFile(f);
        setHeaders([]);
        setMapping({});
        setStep(2);
        return;
      }
      Papa.parse(f, {
        preview: 5,
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          if (!results.meta.fields?.length) {
            setParseError("Could not read column headers. Make sure the file has a header row.");
            return;
          }
          const hdrs = results.meta.fields;
          setHeaders(hdrs);
          setMapping(autoDetectMapping(hdrs, allFields));
          setFile(f);
          setStep(2);
        },
        error: () => setParseError("Failed to parse file. Please ensure it is a valid CSV."),
      });
    },
    [allFields],
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    processFile(e.dataTransfer.files[0]);
  };
  const onFileChange = (e) => {
    processFile(e.target.files[0]);
    e.target.value = "";
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    const form = new FormData();
    form.append("file", file);
    form.append("scope", scopeFor(mode));
    form.append("overwrite_duplicates", overwrite ? "true" : "false");
    form.append("column_mapping", JSON.stringify(mapping));
    try {
      const res = await api.post("/emissions/upload/start", form, { headers: { "Content-Type": "multipart/form-data" } });
      setJobId(res.data.job_id);
      setStep(3);
    } catch (err) {
      toast.error("Upload error: " + (err.response?.data?.error || err.message));
    } finally {
      setSubmitting(false);
    }
  };

  const footer =
    step === 3 ? null : (
      <div className="flex w-full items-center justify-between">
        <Button variant="secondary" onClick={step === 1 ? onClose : () => setStep((s) => s - 1)}>
          {step === 1 ? <X className="size-4" aria-hidden="true" /> : <ArrowLeft className="size-4" aria-hidden="true" />}
          {step === 1 ? "Cancel" : "Back"}
        </Button>
        {step === 1 ? (
          <Button onClick={() => setStep(2)} disabled={!file}>
            Next <ChevronRight className="size-4" aria-hidden="true" />
          </Button>
        ) : (
          <Button onClick={handleSubmit} loading={submitting} disabled={submitting || (!canSubmit && headers.length > 0) || noRegions}>
            {submitting ? "Starting…" : "Start import"}
          </Button>
        )}
      </div>
    );

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()} title={title} description={subtitle} maxWidth="52rem" dismissible={step !== 3} footer={footer}>
      <div className="flex flex-col gap-4">
        <Stepper steps={STEPS} current={step - 1} />

        {step === 1 && (
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
            {restricted && <RegionAccess regions={allowedRegions} />}
            <FileDrop inputRef={fileInputRef} dragging={dragging} onDragging={setDragging} onDrop={onDrop} onFileChange={onFileChange} error={parseError} />
          </>
        )}

        {step === 2 && (
          <>
            {restricted && <RegionAccess regions={allowedRegions} compact />}
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
                <span className="flex items-start gap-2">
                  <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                  <span>
                    <strong>
                      {missingRequired.length} required field{missingRequired.length > 1 ? "s" : ""} not mapped:
                    </strong>{" "}
                    {missingRequired.map((f) => f.label).join(", ")}
                  </span>
                </span>
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

            <label className={cn("flex cursor-pointer flex-wrap items-center gap-2 text-sm font-medium text-text-secondary")}>
              <input type="checkbox" className="size-4 accent-brand-500" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
              Overwrite records that already exist (same facility, month and source). Overwritten records go back to Pending review.
            </label>

            <div className="flex flex-col gap-2.5">
              {groups.map((group) => (
                <FieldGroup key={group.id} group={group} headers={headers} mapping={mapping} setMapping={setMapping} searchQuery={searchQuery} />
              ))}
            </div>
          </>
        )}

        {step === 3 && jobId && (
          <UploadProgress
            jobId={jobId}
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
