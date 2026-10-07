import React from "react";
import { ExternalLink, HelpCircle, KeyRound, Radio, Satellite, Save } from "lucide-react";
import { Banner, Button, Field, Input, SegmentedControl, Switch } from "../../ui";
import { SettingsSection } from "./SettingsIPCCGlobalWarming";

const SPECS: [string, string, string][] = [
  ["Satellite Instrument", "Sentinel-5P (TROPOMI)", "European Space Agency (ESA)"],
  ["Spatial Resolution", "5.5 × 7.0 km", "Regional & Basin Plume Scale"],
  ["Global Revisit Rate", "~2 Days", "High-frequency column monitoring"],
  ["Measured Variable", "Total Column CH₄ (ppb)", "Dry Air Mixing Ratio"],
];

interface ExtProps {
  href: string;
  children: React.ReactNode;
}

const Ext: React.FC<ExtProps> = ({ href, children }) => (
  <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-info-fg hover:underline">
    {children} <ExternalLink className="size-3" aria-hidden="true" />
  </a>
);

const GUIDE: React.ReactNode[] = [
  <>
    <strong>Visit Copernicus Data Space:</strong> Go to <Ext href="https://dataspace.copernicus.eu">dataspace.copernicus.eu</Ext> and click <strong>"Register"</strong> in the top-right corner.
  </>,
  <>
    <strong>Create Free Account:</strong> Fill in your name, organization, email, and choose a password. Confirm the activation email sent to your inbox.
  </>,
  <>
    <strong>Choose Login Method:</strong>
    <ul className="m-0 mt-1.5 flex list-disc flex-col gap-1 pl-5">
      <li>
        <strong>Direct Login (Recommended):</strong> Use your registered Copernicus Email and Password directly below.
      </li>
      <li>
        <strong>OAuth2 API Keys (Enterprise):</strong> Go to <Ext href="https://identity.dataspace.copernicus.eu">identity.dataspace.copernicus.eu</Ext> &rarr; <em>OAuth Clients / API Keys</em> &rarr; <em>Create New Client</em>.
      </li>
    </ul>
  </>,
  <>
    <strong>Test & Save:</strong> Enter credentials below, click <strong>"Test Connection"</strong> to verify authentication, then click <strong>"Save All Changes"</strong>.
  </>,
];

export interface ConnectionStatus {
  success?: boolean;
  message?: string;
  expires_in?: number;
  [key: string]: any;
}

export interface SettingsESACopernicusSentinel5PProps {
  authMode: string;
  connectionStatus: ConnectionStatus | null;
  copernicusClientId: string;
  copernicusClientSecret: string;
  copernicusEnabled: boolean;
  copernicusPassword: string;
  copernicusQaThreshold: number;
  copernicusUsername: string;
  handleSaveGlobal: () => void;
  handleTestConnection: () => void;
  isAdmin: boolean;
  saving: boolean;
  setAuthMode: (mode: any) => void;
  setCopernicusClientId: (id: string) => void;
  setCopernicusClientSecret: (secret: string) => void;
  setCopernicusEnabled: (enabled: boolean) => void;
  setCopernicusPassword: (password: string) => void;
  setCopernicusQaThreshold: (threshold: number) => void;
  setCopernicusUsername: (username: string) => void;
  setShowGuide: (show: boolean) => void;
  showGuide: boolean;
  testingConnection: boolean;
}

const SettingsESACopernicusSentinel5P: React.FC<SettingsESACopernicusSentinel5PProps> = ({
  authMode,
  connectionStatus,
  copernicusClientId,
  copernicusClientSecret,
  copernicusEnabled,
  copernicusPassword,
  copernicusQaThreshold,
  copernicusUsername,
  handleSaveGlobal,
  handleTestConnection,
  isAdmin,
  saving,
  setAuthMode,
  setCopernicusClientId,
  setCopernicusClientSecret,
  setCopernicusEnabled,
  setCopernicusPassword,
  setCopernicusQaThreshold,
  setCopernicusUsername,
  setShowGuide,
  showGuide,
  testingConnection,
}) => (
  <SettingsSection
    icon={Satellite}
    title="ESA Copernicus Sentinel-5P (TROPOMI) Satellite Integration"
    intro={
      <>
        Configure access to the <strong>Copernicus Data Space Ecosystem (CDSE)</strong> to stream global Level-3 Methane total column mixing ratio (<code className="text-info-fg">COPERNICUS/S5P/OFFL/L3_CH4</code>) directly into the Emissions Map and OGMP 2.0 top-down reconciliation engine.
      </>
    }
  >
    <div className="rounded-md border border-blue-500/25 bg-info-bg/50 px-5 py-4">
      <div className="flex items-center justify-between gap-4">
        <p className="m-0 flex items-center gap-2.5 text-md text-text">
          <HelpCircle className="size-[18px] shrink-0 text-info-fg" aria-hidden="true" />
          <strong>Need a Copernicus Account? Click here for the Step-by-Step Setup Guide</strong>
        </p>
        <Button size="sm" aria-expanded={showGuide} onClick={() => setShowGuide(!showGuide)}>
          {showGuide ? "Hide Guide" : "Show Step-by-Step Guide"}
        </Button>
      </div>
      {showGuide && (
        <ol className="m-0 mt-4 flex list-none flex-col gap-3 border-0 border-t border-dashed border-blue-500/25 p-0 pt-4">
          {GUIDE.map((step, i) => (
            <li key={i} className="flex items-start gap-3.5">
              <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-info-fg text-sm font-bold text-white">{i + 1}</span>
              <div className="text-base leading-normal text-text">{step}</div>
            </li>
          ))}
        </ol>
      )}
    </div>

    <dl className="m-0 grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(200px,1fr))]">
      {SPECS.map(([term, value, note]) => (
        <div key={term} className="flex flex-col gap-1 rounded-md border border-border bg-ink-50 px-4 py-4">
          <dt className="text-sm font-bold uppercase tracking-wide text-text-secondary">{term}</dt>
          <dd className="m-0 text-lg font-bold text-info-fg">{value}</dd>
          <dd className="m-0 text-sm text-text-secondary">{note}</dd>
        </div>
      ))}
    </dl>

    <div className="flex flex-col gap-4 rounded-lg border border-border bg-ink-50 p-6">
      <h3 className="m-0 flex items-center gap-2 text-md font-bold text-text">
        <KeyRound className="size-[18px] text-brand-500" aria-hidden="true" /> Copernicus Data Space Ecosystem (CDSE) Credentials
      </h3>

      <SegmentedControl
        label="Authentication method"
        value={authMode}
        onChange={setAuthMode}
        options={[
          { value: "password", label: "Copernicus Account (Email & Password)" },
          { value: "oauth_client", label: "Dedicated OAuth2 API Keys (Client ID & Secret)" },
        ]}
      />

      {authMode === "password" ? (
        <div className="grid gap-5 md:grid-cols-2">
          <Field label="Copernicus Email / Username" hint="Registered account on dataspace.copernicus.eu">
            <Input type="email" placeholder="user@example.com" value={copernicusUsername} disabled={!isAdmin} onChange={(e) => setCopernicusUsername(e.target.value)} />
          </Field>
          <Field label="Copernicus Password" hint="Encrypted and authenticated directly against Keycloak">
            <Input type="password" placeholder="••••••••••••" value={copernicusPassword} disabled={!isAdmin} onChange={(e) => setCopernicusPassword(e.target.value)} />
          </Field>
        </div>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          <Field label="OAuth2 Client ID">
            <Input placeholder="e.g. 9b1deb4d-3b7d-4bad-9bdd-..." value={copernicusClientId} disabled={!isAdmin} onChange={(e) => setCopernicusClientId(e.target.value)} />
          </Field>
          <Field label="OAuth2 Client Secret">
            <Input type="password" placeholder="••••••••••••" value={copernicusClientSecret} disabled={!isAdmin} onChange={(e) => setCopernicusClientSecret(e.target.value)} />
          </Field>
        </div>
      )}

      <div className="mt-2 grid gap-5 md:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="copernicus-qa-slider" className="text-sm font-medium text-text">
              Cloud Quality Filter (QA Value Threshold)
            </label>
            <span className="font-bold text-info-fg">&ge; {copernicusQaThreshold}</span>
          </div>
          <input
            type="range"
            min="0.3"
            max="0.9"
            step="0.05"
            disabled={!isAdmin}
            value={copernicusQaThreshold}
            onChange={(e) => setCopernicusQaThreshold(Number(e.target.value))}
            className="h-2 w-full cursor-pointer accent-brand-500 disabled:cursor-not-allowed"
            id="copernicus-qa-slider"
          />
          <span className="text-xs text-text-secondary">ESA standard: 0.5 (filters out cloud, snow, and low-confidence pixels)</span>
        </div>

        <div className="flex flex-col justify-center gap-1.5">
          <span className="text-sm font-medium text-text">Satellite Layer Streaming</span>
          <Switch label="Enable Live Sentinel-5P Methane Layer on Map" disabled={!isAdmin} checked={copernicusEnabled} onChange={(e) => setCopernicusEnabled(e.target.checked)} id="copernicus-enabled-checkbox" />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <Button variant="secondary" onClick={handleTestConnection} disabled={!isAdmin || testingConnection} loading={testingConnection} id="test-copernicus-connection-btn">
          <Radio className="size-4" aria-hidden="true" />
          {testingConnection ? "Testing Connection..." : "Test Copernicus Connection"}
        </Button>
        {connectionStatus && (
          <Banner tone={connectionStatus.success ? "success" : "danger"} className="py-2">
            {connectionStatus.message}
            {connectionStatus.expires_in && <span className="ml-2 text-sm opacity-80">(Token TTL: {Math.round(connectionStatus.expires_in / 60)}m)</span>}
          </Banner>
        )}
      </div>
    </div>

    <div className="flex justify-end">
      <Button onClick={handleSaveGlobal} loading={saving} disabled={saving || !isAdmin} title={!isAdmin ? "Administrator privileges required to modify settings" : "Save settings"} id="save-satellite-settings-btn">
        <Save className="size-[18px]" aria-hidden="true" />
        {saving ? "Saving..." : "Save Satellite Settings"}
      </Button>
    </div>
  </SettingsSection>
);

export default SettingsESACopernicusSentinel5P;
