import React, { useState } from "react";
import { Wand2 } from "lucide-react";
import { Button, Input, NativeSelect } from "../../ui";
import type { SavedMapping } from "../../utils/savedMappings";

export interface SavedMappingBarProps {
  applied: SavedMapping | null;
  fitting: SavedMapping[];
  canSave: boolean;
  defaultName: string;
  onApply: (m: SavedMapping | null) => void;
  onSave: (name: string) => Promise<boolean>;
}

/** Saved column mappings: re-apply one to a file with the same columns, or save the current one. */
export const SavedMappingBar: React.FC<SavedMappingBarProps> = ({ applied, fitting, canSave, defaultName, onApply, onSave }) => {
  const [name, setName] = useState<string | null>(null);
  const save = async () => {
    const n = (name || "").trim();
    if (n && (await onSave(n))) setName(null);
  };
  return (
    <div data-testid="saved-mapping-bar" className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-ink-50 px-4 py-2.5 text-sm text-text-secondary">
      <Wand2 className="size-4 shrink-0 text-brand-700" aria-hidden="true" />
      {applied ? (
        <span>
          Using your saved mapping <strong className="text-text">{applied.name}</strong>.{" "}
          <Button variant="link" size="sm" className="h-auto px-0" onClick={() => onApply(null)}>
            Don't use it
          </Button>
        </span>
      ) : fitting.length > 0 ? (
        <label className="flex items-center gap-2">
          Saved mapping for these columns:
          <NativeSelect aria-label="Saved mapping" value="" onChange={(e) => onApply(fitting.find((m) => String(m.id) === e.target.value) || null)}>
            <option value="">Choose…</option>
            {fitting.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </NativeSelect>
        </label>
      ) : (
        <span>Columns matched automatically. Save the mapping to reuse it for the next file with these columns.</span>
      )}
      <span className="ml-auto flex items-center gap-2">
        {name === null ? (
          <Button variant="link" size="sm" className="h-auto px-0" disabled={!canSave} onClick={() => setName(applied?.name || defaultName)}>
            {applied ? "Update saved mapping" : "Save this mapping"}
          </Button>
        ) : (
          <>
            <Input aria-label="Mapping name" maxLength={80} value={name} autoFocus className="h-8 w-48" onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()} />
            <Button size="sm" onClick={save} disabled={!name.trim()}>
              Save
            </Button>
            <Button variant="link" size="sm" className="h-auto px-0" onClick={() => setName(null)}>
              Cancel
            </Button>
          </>
        )}
      </span>
    </div>
  );
};
