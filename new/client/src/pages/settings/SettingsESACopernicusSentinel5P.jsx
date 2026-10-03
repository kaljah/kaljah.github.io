import React from "react";
import { Button } from "../../ui";
import { AlertCircle, CheckCircle2, ExternalLink, HelpCircle, KeyRound, Radio, Satellite, Save } from "lucide-react";

// Extracted from Settings.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SettingsESACopernicusSentinel5P = ({ authMode, connectionStatus, copernicusClientId, copernicusClientSecret, copernicusEnabled, copernicusPassword, copernicusQaThreshold, copernicusUsername, handleSaveGlobal, handleTestConnection, isAdmin, saving, setAuthMode, setCopernicusClientId, setCopernicusClientSecret, setCopernicusEnabled, setCopernicusPassword, setCopernicusQaThreshold, setCopernicusUsername, setShowGuide, showGuide, testingConnection }) => (
<div className="[background:var(--bg-card,_var(--color-white))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-lg)] [padding:32px] [display:flex] [flex-direction:column] [gap:28px] [box-shadow:var(--shadow-card,_0_4px_6px_-1px_rgba(0,_0,_0,_0.05))]">
          <div className="section-intro">
            <div className="[display:flex] [align-items:center] [gap:10px]">
              <Satellite
                size={22}
                className="section-icon text-[color:#0369a1]!"
               
              />
              <h2>
                ESA Copernicus Sentinel-5P (TROPOMI) Satellite Integration
              </h2>
            </div>
            <p>
              Configure access to the **Copernicus Data Space Ecosystem (CDSE)**
              to stream global Level-3 Methane total column mixing ratio (
              <code className="text-[color:#0369a1]!">
                COPERNICUS/S5P/OFFL/L3_CH4
              </code>
              ) directly into the Emissions Map and OGMP 2.0 top-down
              reconciliation engine.
            </p>
          </div>

          {/* Step-by-step account guide toggle banner */}
          <div className="[background:rgba(2,_132,_199,_0.05)] [border:1px_solid_rgba(2,_132,_199,_0.2)] [&&]:[border-radius:var(--radius-md)] [padding:16px_20px] [margin-bottom:24px] [transition:all_0.2s_ease] hover:[border-color:rgba(2,_132,_199,_0.35)]">
            <div role="presentation"
              className="[display:flex] [justify-content:space-between] [align-items:center] [cursor:pointer] [gap:16px]"
              onClick={() => setShowGuide(!showGuide)}
            >
              <div className="[display:flex] [align-items:center] [gap:10px] [font-size:var(--text-md)] [color:var(--text-primary,_var(--color-ink-900))]">
                <HelpCircle size={18} color="#0284c7" />
                <strong>
                  Need a Copernicus Account? Click here for the Step-by-Step
                  Setup Guide
                </strong>
              </div>
              <button className="[background:var(--color-sky-600)] [color:var(--color-white)] [border:none] [&&]:[border-radius:var(--radius-sm)] [padding:6px_14px] [font-size:var(--text-sm)] [font-weight:600] [cursor:pointer] [transition:background_0.2s_ease] hover:[background:#0369a1]" type="button" aria-expanded={showGuide}>
                {showGuide ? "Hide Guide" : "Show Step-by-Step Guide"}
              </button>
            </div>

            {showGuide && (
              <div className="[margin-top:16px] [padding-top:16px] [border-top:1px_dashed_rgba(2,_132,_199,_0.2)] [display:flex] [flex-direction:column] [gap:12px]">
                <div className="[display:flex] [gap:14px] [align-items:flex-start]">
                  <div className="[background:var(--color-sky-600)] [color:var(--color-white)] [width:24px] [height:24px] [border-radius:50%] [display:flex] [align-items:center] [justify-content:center] [font-size:var(--text-sm)] [font-weight:700] [flex-shrink:0] [margin-top:2px]">1</div>
                  <div className="step-content">
                    <strong>Visit Copernicus Data Space:</strong> Go to{" "}
                    <a
                      href="https://dataspace.copernicus.eu"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="[color:var(--color-blue-700)] [font-weight:600] [text-decoration:none] [display:inline-flex] [align-items:center] [gap:3px] hover:[text-decoration:underline]"
                    >
                      dataspace.copernicus.eu <ExternalLink size={12} />
                    </a>{" "}
                    and click <strong>"Register"</strong> in the top-right
                    corner.
                  </div>
                </div>
                <div className="[display:flex] [gap:14px] [align-items:flex-start]">
                  <div className="[background:var(--color-sky-600)] [color:var(--color-white)] [width:24px] [height:24px] [border-radius:50%] [display:flex] [align-items:center] [justify-content:center] [font-size:var(--text-sm)] [font-weight:700] [flex-shrink:0] [margin-top:2px]">2</div>
                  <div className="step-content">
                    <strong>Create Free Account:</strong> Fill in your name,
                    organization, email, and choose a password. Confirm the
                    activation email sent to your inbox.
                  </div>
                </div>
                <div className="[display:flex] [gap:14px] [align-items:flex-start]">
                  <div className="[background:var(--color-sky-600)] [color:var(--color-white)] [width:24px] [height:24px] [border-radius:50%] [display:flex] [align-items:center] [justify-content:center] [font-size:var(--text-sm)] [font-weight:700] [flex-shrink:0] [margin-top:2px]">3</div>
                  <div className="step-content">
                    <strong>Choose Login Method:</strong>
                    <ul>
                      <li>
                        <strong>Direct Login (Recommended):</strong> Use your
                        registered Copernicus Email and Password directly below.
                      </li>
                      <li>
                        <strong>OAuth2 API Keys (Enterprise):</strong> Go to{" "}
                        <a
                          href="https://identity.dataspace.copernicus.eu"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="[color:var(--color-blue-700)] [font-weight:600] [text-decoration:none] [display:inline-flex] [align-items:center] [gap:3px] hover:[text-decoration:underline]"
                        >
                          identity.dataspace.copernicus.eu{" "}
                          <ExternalLink size={12} />
                        </a>{" "}
                        &rarr; <em>OAuth Clients / API Keys</em> &rarr;{" "}
                        <em>Create New Client</em>.
                      </li>
                    </ul>
                  </div>
                </div>
                <div className="[display:flex] [gap:14px] [align-items:flex-start]">
                  <div className="[background:var(--color-sky-600)] [color:var(--color-white)] [width:24px] [height:24px] [border-radius:50%] [display:flex] [align-items:center] [justify-content:center] [font-size:var(--text-sm)] [font-weight:700] [flex-shrink:0] [margin-top:2px]">4</div>
                  <div className="step-content">
                    <strong>Test & Save:</strong> Enter credentials below, click{" "}
                    <strong>"Test Connection"</strong> to verify authentication,
                    then click <strong>"Save All Changes"</strong>.
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Satellite Specs Overview */}
          <div className="[display:grid] [grid-template-columns:repeat(auto-fit,_minmax(200px,_1fr))] [gap:16px] [margin-bottom:28px]">
            <div className="[background:var(--bg-card-secondary,_var(--color-ink-50))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-md)] [padding:16px_18px] [display:flex] [flex-direction:column] [gap:4px]">
              <div className="[font-size:var(--text-sm)] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary,_var(--color-ink-500))] [font-weight:700]">Satellite Instrument</div>
              <div className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--color-blue-700)]">Sentinel-5P (TROPOMI)</div>
              <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-400))]">European Space Agency (ESA)</div>
            </div>
            <div className="[background:var(--bg-card-secondary,_var(--color-ink-50))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-md)] [padding:16px_18px] [display:flex] [flex-direction:column] [gap:4px]">
              <div className="[font-size:var(--text-sm)] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary,_var(--color-ink-500))] [font-weight:700]">Spatial Resolution</div>
              <div className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--color-blue-700)]">5.5 × 7.0 km</div>
              <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-400))]">Regional & Basin Plume Scale</div>
            </div>
            <div className="[background:var(--bg-card-secondary,_var(--color-ink-50))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-md)] [padding:16px_18px] [display:flex] [flex-direction:column] [gap:4px]">
              <div className="[font-size:var(--text-sm)] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary,_var(--color-ink-500))] [font-weight:700]">Global Revisit Rate</div>
              <div className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--color-blue-700)]">~2 Days</div>
              <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-400))]">High-frequency column monitoring</div>
            </div>
            <div className="[background:var(--bg-card-secondary,_var(--color-ink-50))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-md)] [padding:16px_18px] [display:flex] [flex-direction:column] [gap:4px]">
              <div className="[font-size:var(--text-sm)] [text-transform:uppercase] [letter-spacing:0.05em] [color:var(--text-secondary,_var(--color-ink-500))] [font-weight:700]">Measured Variable</div>
              <div className="[font-size:var(--text-lg)] [font-weight:700] [color:var(--color-blue-700)]">Total Column CH₄ (ppb)</div>
              <div className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-400))]">Dry Air Mixing Ratio</div>
            </div>
          </div>

          {/* Credentials Form Section */}
          <div className="[background:var(--bg-card-secondary,_var(--color-ink-50))] [border:1px_solid_var(--border-color,_var(--color-ink-200))] [&&]:[border-radius:var(--radius-lg)] [padding:24px] [display:flex] [flex-direction:column] [gap:18px]">
            <div className="config-form-header">
              <KeyRound size={18} />
              <h3>Copernicus Data Space Ecosystem (CDSE) Credentials</h3>
            </div>

            <div className="[display:flex] [gap:12px] [flex-wrap:wrap] [margin-bottom:10px]">
              <label
                className={`auth-mode-pill ${authMode === "password" ? "active" : ""}`}
              >
                <input
                  type="radio"
                  name="authMode"
                  value="password"
                  disabled={!isAdmin}
                  checked={authMode === "password"}
                  onChange={() => setAuthMode("password")}
                />
                <span>Copernicus Account (Email &amp; Password)</span>
              </label>
              <label
                className={`auth-mode-pill ${authMode === "oauth_client" ? "active" : ""}`}
              >
                <input
                  type="radio"
                  name="authMode"
                  value="oauth_client"
                  disabled={!isAdmin}
                  checked={authMode === "oauth_client"}
                  onChange={() => setAuthMode("oauth_client")}
                />
                <span>Dedicated OAuth2 API Keys (Client ID &amp; Secret)</span>
              </label>
            </div>

            {authMode === "password" ? (
              <div className="[display:grid] [grid-template-columns:1fr_1fr]! [gap:20px] [@media(max-width:768px)]:[grid-template-columns:1fr]!">
                <div className="form-group">
                  <label className="field-label">
                    Copernicus Email / Username
                  </label>
                  <input
                    type="email"
                    placeholder="user@example.com"
                    value={copernicusUsername}
                    disabled={!isAdmin}
                    onChange={(e) => setCopernicusUsername(e.target.value)}
                    className="form-input"
                    id="copernicus-email-input"
                  />
                  <span className="field-hint">
                    Registered account on dataspace.copernicus.eu
                  </span>
                </div>
                <div className="form-group">
                  <label className="field-label">Copernicus Password</label>
                  <input
                    type="password"
                    placeholder="••••••••••••"
                    value={copernicusPassword}
                    disabled={!isAdmin}
                    onChange={(e) => setCopernicusPassword(e.target.value)}
                    className="form-input"
                    id="copernicus-password-input"
                  />
                  <span className="field-hint">
                    Encrypted and authenticated directly against Keycloak
                  </span>
                </div>
              </div>
            ) : (
              <div className="[display:grid] [grid-template-columns:1fr_1fr]! [gap:20px] [@media(max-width:768px)]:[grid-template-columns:1fr]!">
                <div className="form-group">
                  <label className="field-label">OAuth2 Client ID</label>
                  <input
                    type="text"
                    placeholder="e.g. 9b1deb4d-3b7d-4bad-9bdd-..."
                    value={copernicusClientId}
                    disabled={!isAdmin}
                    onChange={(e) => setCopernicusClientId(e.target.value)}
                    className="form-input"
                    id="copernicus-client-id-input"
                  />
                </div>
                <div className="form-group">
                  <label className="field-label">OAuth2 Client Secret</label>
                  <input
                    type="password"
                    placeholder="••••••••••••"
                    value={copernicusClientSecret}
                    disabled={!isAdmin}
                    onChange={(e) => setCopernicusClientSecret(e.target.value)}
                    className="form-input"
                    id="copernicus-client-secret-input"
                  />
                </div>
              </div>
            )}

            {/* Quality Filtering and Enable Toggle */}
            <div className="[display:grid] [grid-template-columns:1fr_1fr]! [gap:20px] [@media(max-width:768px)]:[grid-template-columns:1fr]! mt-[16px]!">
              <div className="form-group">
                <div
                  className="flex! justify-between! items-center! mb-[6px]!"
                >
                  <label className="field-label m-[0px]!">
                    Cloud Quality Filter (QA Value Threshold)
                  </label>
                  <span className="font-bold! text-[color:#0369a1]!">
                    &ge; {copernicusQaThreshold}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.3"
                  max="0.9"
                  step="0.05"
                  disabled={!isAdmin}
                  value={copernicusQaThreshold}
                  onChange={(e) =>
                    setCopernicusQaThreshold(Number(e.target.value))
                  }
                  className="range-slider"
                  id="copernicus-qa-slider"
                />
                <span className="field-hint">
                  ESA standard: 0.5 (filters out cloud, snow, and low-confidence
                  pixels)
                </span>
              </div>

              <div
                className="form-group flex! flex-col! justify-center!"
               
              >
                <label className="field-label">Satellite Layer Streaming</label>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    cursor: isAdmin ? "pointer" : "default",
                    marginTop: "4px",
                  }}
                >
                  <input
                    type="checkbox"
                    disabled={!isAdmin}
                    checked={copernicusEnabled}
                    onChange={(e) => setCopernicusEnabled(e.target.checked)}
                    style={{
                      width: "18px",
                      height: "18px",
                      accentColor: "#0284c7",
                    }}
                    id="copernicus-enabled-checkbox"
                  />
                  <span className="text-[length:0.92rem]! font-semibold!">
                    Enable Live Sentinel-5P Methane Layer on Map
                  </span>
                </label>
              </div>
            </div>

            {/* Connection Test Action & Status Display */}
            <div className="[display:flex] [align-items:center] [gap:16px] [margin-top:10px] [flex-wrap:wrap]">
              <button
                type="button"
                className="[display:inline-flex] [align-items:center] [gap:8px] [background:var(--color-sky-600)]! [color:var(--color-white)] [padding:10px_20px] [border-radius:var(--radius-md)] [border:none] [font-size:var(--text-base)] [font-weight:600] [cursor:pointer] [transition:background_0.2s_ease] [&:hover:not(:disabled)]:[background:#0369a1]! disabled:[opacity:0.6] disabled:[cursor:not-allowed]"
                onClick={handleTestConnection}
                disabled={!isAdmin || testingConnection}
                id="test-copernicus-connection-btn"
              >
                {testingConnection ? (
                  <>
                    <span className="spinner-small"></span>
                    <span>Testing Connection...</span>
                  </>
                ) : (
                  <>
                    <Radio size={16} />
                    <span>Test Copernicus Connection</span>
                  </>
                )}
              </button>

              {connectionStatus && (
                <div
                  className={`[display:inline-flex] [align-items:center] [gap:8px] [padding:8px_16px] [border-radius:var(--radius-md)] [font-size:var(--text-base)] [font-weight:600] [&.success]:[background:rgba(16,_185,_129,_0.1)] [&.success]:[color:var(--color-green-700)] [&.success]:[border:1px_solid_rgba(16,_185,_129,_0.3)] [&&]:[&.error]:[background:rgba(239,_68,_68,_0.1)] [&&]:[&.error]:[color:var(--color-red-700)] [&&]:[&.error]:[border:1px_solid_rgba(239,_68,_68,_0.3)] ${connectionStatus.success ? "success" : "error"}`}
                >
                  {connectionStatus.success ? (
                    <CheckCircle2 size={16} />
                  ) : (
                    <AlertCircle size={16} />
                  )}
                  <span>{connectionStatus.message}</span>
                  {connectionStatus.expires_in && (
                    <span className="[font-size:var(--text-sm)] [opacity:0.8]">
                      (Token TTL: {Math.round(connectionStatus.expires_in / 60)}
                      m)
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div
            className="mt-[24px]! flex! justify-end!"
          >
            <Button
              type="submit"
              onClick={handleSaveGlobal}
              disabled={saving || !isAdmin}
              title={!isAdmin ? "Administrator privileges required to modify settings" : "Save settings"}
              id="save-satellite-settings-btn"
              className="flex! items-center! gap-[8px]! p-[10px_24px]!"
            >
              <Save size={18} />
              {saving ? "Saving..." : "Save Satellite Settings"}
            </Button>
          </div>
        </div>
);

export default SettingsESACopernicusSentinel5P;
