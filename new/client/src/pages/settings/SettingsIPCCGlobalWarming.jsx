import React from "react";
import { CheckCircle2, Layers, Scale } from "lucide-react";
import { GWP_AR4, GWP_AR5, GWP_AR6 } from "../../constants";
import { Badge, RadioCardGroup } from "../../ui";

// Extracted from Settings.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const SettingsIPCCGlobalWarming = ({ GWP_DATA, gwpStandard, isAdmin, setGwpStandard }) => (
<div className="[background:var(--bg-card,_var(--color-white))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [border-radius:var(--radius-lg)]! [padding:32px]! [display:flex]! [flex-direction:column] [gap:28px] [box-shadow:var(--shadow-card,_0_4px_6px_-1px_rgba(0,_0,_0,_0.05))]!">
          <div className="[display:flex]! [flex-direction:column] [gap:6px] [&_h2]:[font-size:var(--text-lg)]! [&_h2]:[font-weight:700]! [&_h2]:[color:var(--text-primary,_var(--color-ink-900))]! [&_h2]:[margin:0]! [&_p]:[font-size:var(--text-base)]! [&_p]:[color:var(--text-secondary,_var(--color-ink-500))]! [&_p]:[margin:0]! [&_p]:[line-height:1.5]!">
            <div className="[display:flex]! [align-items:center] [gap:10px]">
              <Scale size={20} className="[color:var(--color-link)]!" />
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
                  <div className="[font-size:var(--text-sm)]! [color:var(--color-blue-700)]! [margin-bottom:10px]! [font-weight:600]!">{data.status}</div>
                  <div className="[display:grid]! [grid-template-columns:repeat(3,_1fr)] [gap:8px] [background:var(--bg-hover,_var(--color-ink-50))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [border-radius:var(--radius-md)]! [padding:12px_10px]!">
                    <div className="factor-item">
                      <span className="factor-label">CH₄ (100-yr)</span>
                      <span className="factor-val [font-size:var(--text-lg)]! [font-weight:800]! [color:var(--text-primary,_var(--color-ink-900))]!">{data.ch4_100}×</span>
                    </div>
                    <div className="factor-item highlight">
                      <span className="factor-label">CH₄ (20-yr)</span>
                      <span className="factor-val [font-size:var(--text-lg)]! [font-weight:800]! [color:var(--text-primary,_var(--color-ink-900))]!">{data.ch4_20}×</span>
                    </div>
                    <div className="factor-item">
                      <span className="factor-label">N₂O (100-yr)</span>
                      <span className="factor-val [font-size:var(--text-lg)]! [font-weight:800]! [color:var(--text-primary,_var(--color-ink-900))]!">{data.n2o_100}×</span>
                    </div>
                  </div>
                </>
              ),
            }))}
          />

          {/* Live Comparison Table */}
          <div className="[background:var(--bg-hover,_var(--color-ink-50))]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [border-radius:var(--radius-lg)]! [padding:24px]! [display:flex]! [flex-direction:column] [gap:16px]">
            <div className="[display:flex]! [align-items:center] [gap:8px] [&_h3]:[font-size:var(--text-md)]! [&_h3]:[font-weight:700]! [&_h3]:[color:var(--text-primary,_var(--color-ink-900))]! [&_h3]:[margin:0]!">
              <Layers size={18} className="[color:var(--color-link)]!" />
              <h3>Conversion Factor Matrix Comparison</h3>
            </div>
            <div className="[overflow-x:auto]!">
              <table className="[width:100%]! [border-collapse:collapse]! [font-size:var(--text-base)]! [background:var(--bg-card,_var(--color-white))]! [border-radius:var(--radius-md)]! [overflow:hidden]! [border:1px_solid_var(--border-color,_var(--color-ink-200))]! [&_th]:[text-align:left]! [&_th]:[padding:12px_16px]! [&_th]:[background:var(--bg-hover,_var(--color-ink-50))]! [&_th]:[color:var(--text-secondary,_var(--color-ink-500))]! [&_th]:[font-weight:600]! [&_th]:[border-bottom:1px_solid_var(--border-color,_var(--color-ink-200))]! [&_td]:[padding:12px_16px]! [&_td]:[border-bottom:1px_solid_var(--border-color,_var(--color-ink-200))]! [&_td]:[color:var(--text-primary,_var(--color-ink-900))]! [&_tr:last-child_td]:[border-bottom:none]! [&_tr.active-row]:[background:rgba(255,_102,_0,_0.06)]! [&_tr.active-row_td]:[color:var(--color-brand-700)]! [&_tr.active-row_td]:[font-weight:600]!">
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
