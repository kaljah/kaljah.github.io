import React, { useMemo, useState } from "react";
import { Check, ChevronDown, CloudUpload, TriangleAlert } from "lucide-react";
import { Badge, Banner } from "../../ui";
import { cn } from "../../ui/cn";
import { activateOnKey } from "../../utils/a11yKeys";
import { t } from "../../i18n";

export const controlClass =
  "h-9 w-full rounded-md border bg-surface px-2.5 text-sm text-text transition-colors hover:border-ink-300 focus:border-brand-500";

export interface MappingField {
  key: string;
  label: string;
  required?: boolean;
  hint?: string;
  [key: string]: any;
}

export interface MappingRowProps {
  field: MappingField;
  headers: string[];
  value: string;
  onChange: (val: string) => void;
}

/** One system field with a dropdown (or free text for Excel files) naming the matching file column. */
export const MappingRow: React.FC<MappingRowProps> = ({ field, headers, value, onChange }) => {
  const mapped = Boolean(value);
  return (
    <div
      className={cn(
        "grid items-center gap-3 border-b border-ink-100 px-4 py-2.5 [grid-template-columns:minmax(0,1.2fr)_minmax(0,1fr)_40px] last:border-b-0",
        mapped ? "bg-success-bg/50" : field.required && "bg-warning-bg/50",
      )}
    >
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="flex items-center gap-1 text-sm font-semibold text-text">
          {field.label}
          {field.required && <span className="size-1.5 shrink-0 rounded-full bg-red-500" role="img" aria-label={t("required")} />}
        </span>
        {field.hint && <span className="text-xs leading-snug text-text-secondary">{field.hint}</span>}
      </div>
      {headers.length > 0 ? (
        <select
          aria-label={t("File column for {{field}}", { field: field.label })}
          className={cn(controlClass, mapped ? "border-green-500" : "border-border")}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">{t("— Not mapped —")}</option>
          {headers.map((h) => (
            <option key={h} value={h}>
              {h}
            </option>
          ))}
        </select>
      ) : (
        <input
          aria-label={t("File column for {{field}}", { field: field.label })}
          className={cn(controlClass, mapped ? "border-green-500" : "border-border")}
          placeholder={t("Column name in your file")}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      <div className="flex justify-center">
        {mapped ? (
          <span className="flex size-5.5 items-center justify-center rounded-full bg-green-500 text-white">
            <Check className="size-3.5" strokeWidth={3} aria-hidden="true" />
            <span className="sr-only">{t("Mapped")}</span>
          </span>
        ) : (
          <span className="size-5.5 rounded-full border-2 border-ink-200" aria-hidden="true" />
        )}
      </div>
    </div>
  );
};

export interface FieldGroupData {
  label: string;
  icon: React.ComponentType<{ className?: string; [key: string]: any }>;
  badge?: string;
  fields: MappingField[];
  [key: string]: any;
}

export interface FieldGroupProps {
  group: FieldGroupData;
  headers: string[];
  mapping: Record<string, string>;
  setMapping: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  searchQuery: string;
}

/** Collapsible group of mapping rows; hidden when the search filters out all of its fields. */
export const FieldGroup: React.FC<FieldGroupProps> = ({ group, headers, mapping, setMapping, searchQuery }) => {
  const [open, setOpen] = useState(true);
  const visible = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return group.fields.filter((f) => !q || f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q) || (f.hint || "").toLowerCase().includes(q));
  }, [group.fields, searchQuery]);
  if (!visible.length) return null;
  const Icon = group.icon;
  const mappedCount = visible.filter((f) => mapping[f.key]).length;
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="flex w-full cursor-pointer items-center justify-between gap-3 border-0 bg-ink-50 px-4 py-2.5 text-left hover:bg-ink-100"
      >
        <span className="flex items-center gap-2.5 text-base font-bold text-text">
          <span className="flex size-6 items-center justify-center rounded-md bg-brand-50 text-brand-700">
            <Icon className="size-3.5" aria-hidden="true" />
          </span>
          {group.label}
          {group.badge && <Badge tone="success">{group.badge}</Badge>}
        </span>
        <span className="flex items-center gap-2.5 text-sm font-semibold text-text-secondary">
          {mappedCount}/{visible.length}{" "}{t("mapped")}
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} aria-hidden="true" />
        </span>
      </button>
      {open && (
        <div className="border-t border-border">
          <div className="grid gap-3 border-b border-border bg-ink-50 px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-text-secondary [grid-template-columns:minmax(0,1.2fr)_minmax(0,1fr)_40px]">
            <span>{t("Field")}</span>
            <span>{t("Your file column")}</span>
            <span className="text-center">{t("Status")}</span>
          </div>
          {visible.map((field) => (
            <MappingRow
              key={field.key}
              field={field}
              headers={headers}
              value={mapping[field.key] || ""}
              onChange={(val) => setMapping((m) => ({ ...m, [field.key]: val }))}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export interface FileDropProps {
  inputRef: React.RefObject<HTMLInputElement | null>;
  dragging: boolean;
  onDragging: (d: boolean) => void;
  onDrop: (e: React.DragEvent) => void;
  onFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  error?: string | null;
}

/** Drag-and-drop target that also opens the file picker. */
export const FileDrop: React.FC<FileDropProps> = ({ inputRef, dragging, onDragging, onDrop, onFileChange, error }) => (
  <div
    role="button"
    tabIndex={0}
    onKeyDown={activateOnKey}
    onClick={() => inputRef.current?.click()}
    onDragOver={(e) => {
      e.preventDefault();
      onDragging(true);
    }}
    onDragLeave={() => onDragging(false)}
    onDrop={onDrop}
    className={cn(
      "flex cursor-pointer flex-col items-center gap-2.5 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors",
      dragging ? "border-brand-500 bg-brand-50" : "border-border bg-ink-50 hover:border-ink-300",
    )}
  >
    <input ref={inputRef as React.RefObject<HTMLInputElement>} type="file" accept=".csv,.xlsx" className="hidden" onChange={onFileChange} />
    <span className="flex size-14 items-center justify-center rounded-xl bg-primary text-on-primary">
      <CloudUpload className="size-7" strokeWidth={1.75} aria-hidden="true" />
    </span>
    <p className="m-0 text-base font-semibold text-text">
      {t("Drag & drop your file here, or")}{" "}<span className="text-brand-700 underline">{t("click to browse")}</span>
    </p>
    <p className="m-0 text-sm text-text-secondary">{t("Supports .xlsx and .csv")}</p>
    {error && (
      <p role="alert" className="m-0 flex items-center gap-1.5 text-sm font-medium text-danger-fg">
        <TriangleAlert className="size-3.5" aria-hidden="true" /> {error}
      </p>
    )}
  </div>
);

export interface RegionAccessProps {
  regions: string[];
  compact?: boolean;
}

/** Which regions the signed-in user may upload for. Shown to non-admin users only. */
export const RegionAccess: React.FC<RegionAccessProps> = ({ regions, compact = false }) => {
  if (!regions.length) {
    return (
      <Banner tone="danger" title={compact ? t("No accessible regions") : undefined}>
        {compact
          ? t("Your account has no assigned regions. All rows will be rejected. Contact an administrator.")
          : t("Your account has no assigned regions. Contact an administrator before uploading.")}
      </Banner>
    );
  }
  return (
    <Banner tone="warning" title={compact ? t("Allowed regions") : t("Your upload is restricted to the following regions")}>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {regions.map((r) => (
          <Badge key={r} tone="brand">
            {r}
          </Badge>
        ))}
      </div>
    </Banner>
  );
};

export const InfoNote: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Banner tone="info">
    {children}
  </Banner>
);
