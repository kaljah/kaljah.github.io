import React from "react";
import { CheckCircle2, Layers, Scale } from "lucide-react";
import { GWP_AR4, GWP_AR5, GWP_AR6 } from "../../constants";
import { Badge, RadioCardGroup } from "../../ui";

// Extracted from Settings.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SettingsIPCCGlobalWarming = ({ GWP_DATA, gwpStandard, isAdmin, setGwpStandard }) => (
<div className="settings-section-card">
          <div className="section-intro">
            <div className="section-intro-header">
              <Scale size={20} className="section-icon" />
              <h2>IPCC Global Warming Potential (GWP) Standard</h2>
            </div>
            <p>
              Select which Intergovernmental Panel on Climate Change (IPCC)
              assessment report conversion factors are applied to Methane (CH₄)
              and Nitrous Oxide (N₂O) emissions calculations.
            </p>
          </div>

          <RadioCardGroup
            label="IPCC GWP standard"
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
                  Active standard
                </Badge>
              ),
              content: (
                <>
                  <div className="gwp-status-pill">{data.status}</div>
                  <div className="gwp-factors-box">
                    <div className="factor-item">
                      <span className="factor-label">CH₄ (100-yr)</span>
                      <span className="factor-val">{data.ch4_100}×</span>
                    </div>
                    <div className="factor-item highlight">
                      <span className="factor-label">CH₄ (20-yr)</span>
                      <span className="factor-val">{data.ch4_20}×</span>
                    </div>
                    <div className="factor-item">
                      <span className="factor-label">N₂O (100-yr)</span>
                      <span className="factor-val">{data.n2o_100}×</span>
                    </div>
                  </div>
                </>
              ),
            }))}
          />

          {/* Live Comparison Table */}
          <div className="comparison-container">
            <div className="comparison-header">
              <Layers size={18} className="comparison-icon" />
              <h3>Conversion Factor Matrix Comparison</h3>
            </div>
            <div className="comparison-table-wrapper">
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Metric / Gas</th>
                    <th>AR4 (2007)</th>
                    <th>AR5 (2014 - Default)</th>
                    <th>AR6 (2021)</th>
                    <th>Application Context</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <strong>Carbon Dioxide (CO₂)</strong>
                    </td>
                    <td>1.0</td>
                    <td>1.0</td>
                    <td>1.0</td>
                    <td>Universal baseline anchor</td>
                  </tr>
                  <tr className={gwpStandard === "AR5" ? "active-row" : ""}>
                    <td>
                      <strong>Methane (CH₄) - 100 Year</strong>
                    </td>
                    <td>{GWP_AR4.CH4.toFixed(1)}×</td>
                    <td>
                      <strong>{GWP_AR5.CH4.toFixed(1)}×</strong>
                    </td>
                    <td>{GWP_AR6.CH4.toFixed(1)}×</td>
                    <td>Corporate GHG Inventory / Scope 1</td>
                  </tr>
                  <tr>
                    <td>
                      <strong>Methane (CH₄) - 20 Year</strong>
                    </td>
                    <td>{GWP_AR4.CH4_20.toFixed(1)}×</td>
                    <td>
                      <strong>{GWP_AR5.CH4_20.toFixed(1)}×</strong>
                    </td>
                    <td>{GWP_AR6.CH4_20.toFixed(1)}×</td>
                    <td>Near-Term Climate Impact / ESG Analytics</td>
                  </tr>
                  <tr>
                    <td>
                      <strong>Nitrous Oxide (N₂O) - 100 Year</strong>
                    </td>
                    <td>{GWP_AR4.N2O.toFixed(1)}×</td>
                    <td>
                      <strong>{GWP_AR5.N2O.toFixed(1)}×</strong>
                    </td>
                    <td>{GWP_AR6.N2O.toFixed(1)}×</td>
                    <td>Flaring / Combustion byproducts</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
);

export default SettingsIPCCGlobalWarming;
