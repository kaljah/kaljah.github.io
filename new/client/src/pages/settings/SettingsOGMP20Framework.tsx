import React from "react";
import { Activity, Save, ShieldCheck, Target } from "lucide-react";
import { Button, Field, Input } from "../../ui";
import { SettingsSection } from "./SettingsIPCCGlobalWarming";

const YEARS = Array.from({ length: new Date().getFullYear() - 2020 }, (_, i) => 2021 + i);

interface PanelProps {
  title: string;
  hint: string;
  children?: React.ReactNode;
}

const Panel: React.FC<PanelProps> = ({ title, hint, children }) => (
  <div className="flex flex-col gap-3.5 rounded-lg border border-border bg-ink-50 p-6">
    <h3 className="m-0 text-md font-bold text-text">{title}</h3>
    <p className="m-0 text-base leading-snug text-text-secondary">{hint}</p>
    {children}
  </div>
);

export interface SettingsOGMP20FrameworkProps {
  defaultBaseYear: number;
  globalThreshold: number;
  handleSaveGlobal: () => void;
  isAdmin: boolean;
  midstreamTarget: number;
  saving: boolean;
  setDefaultBaseYear: (year: number) => void;
  setGlobalThreshold: (threshold: number) => void;
  setMidstreamTarget: (target: number) => void;
  setUpstreamTarget: (target: number) => void;
  upstreamTarget: number;
}

const SettingsOGMP20Framework: React.FC<SettingsOGMP20FrameworkProps> = ({
  defaultBaseYear,
  globalThreshold,
  handleSaveGlobal,
  isAdmin,
  midstreamTarget,
  saving,
  setDefaultBaseYear,
  setGlobalThreshold,
  setMidstreamTarget,
  setUpstreamTarget,
  upstreamTarget,
}) => (
  <SettingsSection
    icon={Target}
    title="OGMP 2.0 Framework & Threshold Configuration"
    intro="Establish global compliance benchmarks, default asset membership years, and acceptable reconciliation tolerances."
  >
    <div className="grid gap-6 [grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr))]">
      <Panel title="Default OGMP 2.0 Membership Baseline Year" hint="The year from which the Gold Standard milestone clock begins (Year 0).">
        <div role="group" aria-label="Baseline year" className="flex flex-wrap gap-2 py-1">
          {YEARS.map((yr) => (
            <Button key={yr} size="sm" variant={defaultBaseYear === yr ? "primary" : "secondary"} aria-pressed={defaultBaseYear === yr} disabled={!isAdmin} onClick={() => setDefaultBaseYear(yr)}>
              {yr}
            </Button>
          ))}
        </div>
        <div className="rounded-md border border-border bg-surface px-4 py-3 text-base text-text-secondary">
          <p className="m-0 mb-1.5 flex items-center gap-1.5 font-bold text-text">
            <ShieldCheck className="size-4" aria-hidden="true" /> Gold Standard Deadlines:
          </p>
          <ul className="m-0 ml-[18px] list-disc p-0">
            <li>
              Operated Assets (3 Years): <strong>{defaultBaseYear + 3}</strong>
            </li>
            <li>
              Non-Operated Assets (5 Years): <strong>{defaultBaseYear + 5}</strong>
            </li>
          </ul>
        </div>
      </Panel>

      <Panel title="Global Reconciliation Variance Threshold (±%)" hint="Maximum tolerable difference between Bottom-Up (L1-L4) inventory and Top-Down (L4/L5) site measurements.">
        <div className="flex items-center gap-4 py-2">
          <input
            type="range"
            aria-label="Reconciliation threshold"
            min="5"
            max="50"
            step="1"
            disabled={!isAdmin}
            value={globalThreshold}
            onChange={(e) => setGlobalThreshold(Number(e.target.value))}
            className="h-2 flex-1 cursor-pointer accent-brand-500 disabled:cursor-not-allowed"
            id="global-threshold-slider"
          />
          <span className="min-w-20 rounded-md border border-brand-100 bg-brand-50 px-3.5 py-1.5 text-center text-lg font-extrabold text-brand-700">±{globalThreshold}%</span>
        </div>
        <p className="m-0 text-sm text-text-secondary">
          OGMP 2.0 recommended default is <strong>±20.0%</strong>. Facilities exceeding this threshold will be flagged for investigation.
        </p>
      </Panel>
    </div>

    <div className="flex flex-col gap-4 rounded-lg border border-border bg-ink-50 p-6">
      <h3 className="m-0 flex items-center gap-2 text-md font-bold text-text">
        <Activity className="size-[18px] text-brand-500" aria-hidden="true" /> OGMP 2.0 Methane Intensity Targets
      </h3>
      <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))]">
        {[
          { label: "Upstream Exploration & Production", value: upstreamTarget, set: setUpstreamTarget, hint: "Methane loss volume as % of total marketable natural gas volume. (Default: 0.20%)", id: "upstream-target-input", tone: "border-l-blue-500" },
          { label: "Midstream Processing & LNG", value: midstreamTarget, set: setMidstreamTarget, hint: "Methane loss volume as % of total throughput volume. (Default: 0.05%)", id: "midstream-target-input", tone: "border-l-green-500" },
        ].map((t) => (
          <div key={t.id} className={`rounded-md border border-border border-l-4 bg-surface p-4 ${t.tone}`}>
            <Field label={t.label} hint={t.hint}>
              <div className="flex items-center gap-2">
                <Input type="number" step="0.01" min="0.01" max="5.0" disabled={!isAdmin} value={t.value} onChange={(e) => t.set(Number(e.target.value))} className="w-24 text-md font-bold" />
                <span className="text-md font-bold text-text">%</span>
              </div>
            </Field>
          </div>
        ))}
      </div>
    </div>

    <div className="flex justify-end">
      <Button onClick={handleSaveGlobal} loading={saving} disabled={saving || !isAdmin} title={!isAdmin ? "Administrator privileges required to modify settings" : "Save changes"} id="save-ogmp-settings-btn">
        <Save className="size-[18px]" aria-hidden="true" />
        {saving ? "Saving Changes..." : "Save OGMP & Target Settings"}
      </Button>
    </div>
  </SettingsSection>
);

export default SettingsOGMP20Framework;
