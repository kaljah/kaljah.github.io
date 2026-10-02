import React from "react";
import { Button } from "../../ui";
import { AlertCircle, CheckCircle2, ExternalLink, HelpCircle, KeyRound, Radio, Satellite, Save } from "lucide-react";

// Extracted from Settings.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SettingsESACopernicusSentinel5P = ({ authMode, connectionStatus, copernicusClientId, copernicusClientSecret, copernicusEnabled, copernicusPassword, copernicusQaThreshold, copernicusUsername, handleSaveGlobal, handleTestConnection, isAdmin, saving, setAuthMode, setCopernicusClientId, setCopernicusClientSecret, setCopernicusEnabled, setCopernicusPassword, setCopernicusQaThreshold, setCopernicusUsername, setShowGuide, showGuide, testingConnection }) => (
<div className="settings-section-card">
          <div className="section-intro">
            <div className="section-intro-header">
              <Satellite
                size={22}
                className="section-icon"
                style={{ color: "#0284c7" }}
              />
              <h2>
                ESA Copernicus Sentinel-5P (TROPOMI) Satellite Integration
              </h2>
            </div>
            <p>
              Configure access to the **Copernicus Data Space Ecosystem (CDSE)**
              to stream global Level-3 Methane total column mixing ratio (
              <code style={{ color: "#0284c7" }}>
                COPERNICUS/S5P/OFFL/L3_CH4
              </code>
              ) directly into the Emissions Map and OGMP 2.0 top-down
              reconciliation engine.
            </p>
          </div>

          {/* Step-by-step account guide toggle banner */}
          <div className="satellite-guide-banner">
            <div
              className="guide-banner-header"
              onClick={() => setShowGuide(!showGuide)}
            >
              <div className="guide-title">
                <HelpCircle size={18} color="#0284c7" />
                <strong>
                  Need a Copernicus Account? Click here for the Step-by-Step
                  Setup Guide
                </strong>
              </div>
              <button className="guide-toggle-btn" type="button" aria-expanded={showGuide}>
                {showGuide ? "Hide Guide" : "Show Step-by-Step Guide"}
              </button>
            </div>

            {showGuide && (
              <div className="guide-steps-body">
                <div className="guide-step">
                  <div className="step-num">1</div>
                  <div className="step-content">
                    <strong>Visit Copernicus Data Space:</strong> Go to{" "}
                    <a
                      href="https://dataspace.copernicus.eu"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="link-ext"
                    >
                      dataspace.copernicus.eu <ExternalLink size={12} />
                    </a>{" "}
                    and click <strong>"Register"</strong> in the top-right
                    corner.
                  </div>
                </div>
                <div className="guide-step">
                  <div className="step-num">2</div>
                  <div className="step-content">
                    <strong>Create Free Account:</strong> Fill in your name,
                    organization, email, and choose a password. Confirm the
                    activation email sent to your inbox.
                  </div>
                </div>
                <div className="guide-step">
                  <div className="step-num">3</div>
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
                          className="link-ext"
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
                <div className="guide-step">
                  <div className="step-num">4</div>
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
          <div className="satellite-specs-grid">
            <div className="spec-card">
              <div className="spec-label">Satellite Instrument</div>
              <div className="spec-val">Sentinel-5P (TROPOMI)</div>
              <div className="spec-desc">European Space Agency (ESA)</div>
            </div>
            <div className="spec-card">
              <div className="spec-label">Spatial Resolution</div>
              <div className="spec-val">5.5 × 7.0 km</div>
              <div className="spec-desc">Regional & Basin Plume Scale</div>
            </div>
            <div className="spec-card">
              <div className="spec-label">Global Revisit Rate</div>
              <div className="spec-val">~2 Days</div>
              <div className="spec-desc">High-frequency column monitoring</div>
            </div>
            <div className="spec-card">
              <div className="spec-label">Measured Variable</div>
              <div className="spec-val">Total Column CH₄ (ppb)</div>
              <div className="spec-desc">Dry Air Mixing Ratio</div>
            </div>
          </div>

          {/* Credentials Form Section */}
          <div className="satellite-config-form">
            <div className="config-form-header">
              <KeyRound size={18} />
              <h3>Copernicus Data Space Ecosystem (CDSE) Credentials</h3>
            </div>

            <div className="auth-mode-selector">
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
              <div className="form-row-2col">
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
              <div className="form-row-2col">
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
            <div className="form-row-2col mt-[16px]!">
              <div className="form-group">
                <div
                  className="flex! justify-between! items-center! mb-[6px]!"
                >
                  <label className="field-label" style={{ margin: 0 }}>
                    Cloud Quality Filter (QA Value Threshold)
                  </label>
                  <span style={{ fontWeight: 700, color: "#0284c7" }}>
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
                  <span style={{ fontSize: "0.92rem", fontWeight: 600 }}>
                    Enable Live Sentinel-5P Methane Layer on Map
                  </span>
                </label>
              </div>
            </div>

            {/* Connection Test Action & Status Display */}
            <div className="connection-test-row">
              <button
                type="button"
                className="btn-test-connection"
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
                  className={`connection-status-badge ${connectionStatus.success ? "success" : "error"}`}
                >
                  {connectionStatus.success ? (
                    <CheckCircle2 size={16} />
                  ) : (
                    <AlertCircle size={16} />
                  )}
                  <span>{connectionStatus.message}</span>
                  {connectionStatus.expires_in && (
                    <span className="token-expiry">
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
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 24px",
              }}
            >
              <Save size={18} />
              {saving ? "Saving..." : "Save Satellite Settings"}
            </Button>
          </div>
        </div>
);

export default SettingsESACopernicusSentinel5P;
