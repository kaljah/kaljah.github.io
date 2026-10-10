import React from "react";
import { CheckCircle2, Layers, Scale } from "lucide-react";
import { GWP_AR4, GWP_AR5, GWP_AR6 } from "../../constants";
import { Badge, Card, RadioCardGroup } from "../../ui";
import { cn } from "../../ui/cn";
import { t } from "../../i18n";

export interface SettingsSectionProps {
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean | "true" | "false" }>;
  title: string;
  intro: React.ReactNode;
  children?: React.ReactNode;
}

/** Shared frame of the Settings tabs: icon, title and intro paragraph above the content. */
export const SettingsSection: React.FC<SettingsSectionProps> = ({ icon: Icon, title, intro, children }) => (
  <Card className="flex flex-col gap-7 p-8">
    <div className="flex flex-col gap-2">
      <h2 className="m-0 flex items-center gap-2.5 text-lg font-bold text-text">
        <Icon className="size-5 shrink-0 text-brand-500" aria-hidden="true" /> {title}
      </h2>
      <p className="m-0 max-w-3xl text-base leading-normal text-text-secondary">{intro}</p>
    </div>
    {children}
  </Card>
);

interface FactorProps {
  label: string;
  value: number;
  highlight?: boolean;
}

const Factor: React.FC<FactorProps> = ({ label, value, highlight }) => (
  <div className="flex flex-col gap-0.5 text-center">
    <span className="text-xs font-semibold text-text-secondary">{label}</span>
    <span className={cn("text-lg font-extrabold text-text", highlight && "text-brand-700")}>{value}×</span>
  </div>
);

interface MatrixRow {
  name: string;
  context: string;
  plain?: boolean;
  values?: number[];
  key?: "CH4" | "CH4_20" | "N2O";
  active?: string;
}

const ROWS: MatrixRow[] = [
  { name: "Carbon Dioxide (CO₂)", values: [1, 1, 1], context: t("Universal baseline anchor"), plain: true },
  { name: "Methane (CH₄) - 100 Year", key: "CH4", context: t("Corporate GHG Inventory / Scope 1"), active: "AR5" },
  { name: "Methane (CH₄) - 20 Year", key: "CH4_20", context: t("Near-Term Climate Impact / ESG Analytics") },
  { name: "Nitrous Oxide (N₂O) - 100 Year", key: "N2O", context: t("Flaring / Combustion byproducts") },
];

const th = "whitespace-nowrap border-b border-border bg-surface px-3.5 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-text-secondary";
const td = "border-b border-ink-100 px-3.5 py-2.5 text-base text-text";

export interface GwpDataEntry {
  name: string;
  description: string;
  status: string;
  ch4_100: number;
  ch4_20: number;
  n2o_100: number;
}

export interface SettingsIPCCGlobalWarmingProps {
  GWP_DATA: Record<string, GwpDataEntry>;
  gwpStandard: string;
  isAdmin: boolean;
  setGwpStandard: (standard: string) => void;
}

const SettingsIPCCGlobalWarming: React.FC<SettingsIPCCGlobalWarmingProps> = ({
  GWP_DATA,
  gwpStandard,
  isAdmin,
  setGwpStandard,
}) => (
  <SettingsSection
    icon={Scale}
    title={t("IPCC Global Warming Potential (GWP) Standard")}
    intro={t("Select which Intergovernmental Panel on Climate Change (IPCC) assessment report conversion factors are applied to Methane (CH₄) and Nitrous Oxide (N₂O) emissions calculations.")}
  >
    <RadioCardGroup
      label={t("IPCC GWP standard")}
      value={gwpStandard}
      onChange={setGwpStandard}
      disabled={!isAdmin}
      options={Object.entries(GWP_DATA).map(([key, data]) => ({
        value: key,
        id: `gwp-card-${key.toLowerCase()}`,
        title: data.name,
        description: data.description,
        badge: <Badge tone="brand">{key}</Badge>,
        selectedBadge: (
          <Badge tone="success">
            <CheckCircle2 className="size-3" aria-hidden="true" />
            {t("Active standard")}
          </Badge>
        ),
        content: (
          <>
            <p className="m-0 text-sm font-semibold text-info-fg">{data.status}</p>
            <div className="grid grid-cols-3 gap-2 rounded-md border border-border bg-ink-50 px-2.5 py-3">
              <Factor label={t("CH₄ (100-yr)")} value={data.ch4_100} />
              <Factor label={t("CH₄ (20-yr)")} value={data.ch4_20} highlight />
              <Factor label={t("N₂O (100-yr)")} value={data.n2o_100} />
            </div>
          </>
        ),
      }))}
    />

    <div className="flex flex-col gap-4 rounded-lg border border-border bg-ink-50 p-6">
      <h3 className="m-0 flex items-center gap-2 text-md font-bold text-text">
        <Layers className="size-[18px] text-brand-500" aria-hidden="true" />{" "}{t("Conversion Factor Matrix Comparison")}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse overflow-hidden rounded-md bg-surface">
          <thead>
            <tr>
              <th className={th}>{t("Metric / Gas")}</th>
              <th className={th}>{t("AR4 (2007)")}</th>
              <th className={th}>{t("AR5 (2014 - Default)")}</th>
              <th className={th}>{t("AR6 (2021)")}</th>
              <th className={th}>{t("Application Context")}</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => {
              const cells = row.plain && row.values
                ? row.values.map((v) => v.toFixed(1))
                : row.key
                ? [GWP_AR4, GWP_AR5, GWP_AR6].map((set) => set[row.key as keyof typeof GWP_AR4].toFixed(1))
                : [];
              return (
                <tr key={row.name} className={cn(gwpStandard === row.active && "bg-brand-50")}>
                  <td className={td}>
                    <strong>{t(row.name)}</strong>
                  </td>
                  {cells.map((value, i) => (
                    <td key={i} className={td}>
                      {i === 1 && !row.plain ? <strong>{value}×</strong> : row.plain ? value : `${value}×`}
                    </td>
                  ))}
                  <td className={td}>{row.context}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  </SettingsSection>
);

export default SettingsIPCCGlobalWarming;
