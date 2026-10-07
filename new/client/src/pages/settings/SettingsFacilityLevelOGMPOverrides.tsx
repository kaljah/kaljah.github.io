import React from "react";
import { Building2, Save } from "lucide-react";
import { Badge, Button, Input, NativeSelect, controlClass } from "../../ui";
import { SettingsSection } from "./SettingsIPCCGlobalWarming";

const YEARS = Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i);
const COLUMNS = ["Facility Name", "Segment", "Operator Status", "Country", "Base Year", "Target Year", "Threshold (±%)", "Actions"];

export interface FacilityEdit {
  operator_status?: "operated" | "non_operated" | string;
  country?: string;
  ogmp_membership_year?: number | string;
  reconciliation_threshold?: number | string;
  [key: string]: any;
}

export interface FacilityItem {
  id: number | string;
  name: string;
  code?: string;
  segment?: string;
  [key: string]: any;
}

export interface SettingsFacilityLevelOGMPOverridesProps {
  facilities: FacilityItem[];
  facilityEdits: Record<string | number, FacilityEdit>;
  handleFacilityChange: (id: number | string, field: string, value: any) => void;
  handleSaveFacility: (id: number | string) => void;
  isAdmin: boolean;
  user?: { role?: string; [key: string]: any } | null;
}

const SettingsFacilityLevelOGMPOverrides: React.FC<SettingsFacilityLevelOGMPOverridesProps> = ({
  facilities,
  facilityEdits,
  handleFacilityChange,
  handleSaveFacility,
  isAdmin,
  user,
}) => {
  const canSave = user?.role === "admin" || user?.role === "superuser";
  return (
    <SettingsSection
      icon={Building2}
      title="Facility-Level OGMP Overrides"
      intro="Customize operator status (Operated vs Non-Operated), country, base year, and specific reconciliation variance thresholds for each facility."
    >
      <div className="overflow-x-auto rounded-lg border border-border bg-surface">
        <table className="w-full min-w-[960px] border-collapse">
          <thead>
            <tr>
              {COLUMNS.map((c) => (
                <th key={c} scope="col" className="whitespace-nowrap border-b border-border bg-ink-50 px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-text-secondary">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {facilities.map((fac) => {
              const edit = facilityEdits[fac.id] || {};
              const opStatus = edit.operator_status || "operated";
              const baseYear = Number(edit.ogmp_membership_year || 2023);
              const change = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
                handleFacilityChange(fac.id, field, e.target.value);
              const name = fac.name;
              return (
                <tr key={fac.id} className="border-b border-ink-100 last:border-b-0">
                  <td className="px-4 py-3">
                    <strong className="block text-base text-text">{name}</strong>
                    <span className="text-xs text-text-secondary">{fac.code || "FAC-" + fac.id}</span>
                  </td>
                  <td className="px-4 py-3 text-base text-text">{fac.segment || "Upstream"}</td>
                  <td className="px-4 py-3">
                    <NativeSelect aria-label={`Operator status for ${name}`} className={controlClass} value={opStatus} disabled={!isAdmin} onChange={change("operator_status")}>
                      <option value="operated">Operated (3-yr target)</option>
                      <option value="non_operated">Non-Operated (5-yr target)</option>
                    </NativeSelect>
                  </td>
                  <td className="px-4 py-3">
                    <Input aria-label={`Country for ${name}`} className="h-9 min-w-28" value={edit.country || "Algeria"} disabled={!isAdmin} onChange={change("country")} />
                  </td>
                  <td className="px-4 py-3">
                    <NativeSelect aria-label={`Base year for ${name}`} className={controlClass} value={baseYear} disabled={!isAdmin} onChange={change("ogmp_membership_year")}>
                      {YEARS.map((y) => (
                        <option key={y} value={y}>
                          {y}
                        </option>
                      ))}
                    </NativeSelect>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone="info">{baseYear + (opStatus === "operated" ? 3 : 5)}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 font-semibold text-text">
                      ±
                      <Input type="number" min="1" max="100" aria-label={`Threshold for ${name}`} className="h-9 w-16 px-2 text-center" value={edit.reconciliation_threshold || 20.0} disabled={!isAdmin} onChange={change("reconciliation_threshold")} />%
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Button variant="secondary" size="sm" onClick={() => handleSaveFacility(fac.id)} disabled={!canSave} title={canSave ? "Save Facility Settings" : "Administrator privileges required to update facility"}>
                      <Save className="size-3.5" aria-hidden="true" /> Save
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </SettingsSection>
  );
};

export default SettingsFacilityLevelOGMPOverrides;
