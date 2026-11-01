import React from "react";
import { Input } from "../../ui";
import { MoreOptions, Section } from "../scope1/ui";
import { t } from "../../i18n";

export interface Scope1OptionsSectionProps {
  gcUncertaintyPct: string | number;
  meterUncertaintyPct: string | number;
  renderSpecificForm: () => React.ReactNode;
  setGcUncertaintyPct: (val: string) => void;
  setMeterUncertaintyPct: (val: string) => void;
  setUserUncertainty: React.Dispatch<
    React.SetStateAction<{
      co2?: string | number;
      ch4?: string | number;
      n2o?: string | number;
      [key: string]: any;
    }>
  >;
  sourceType: string;
  uncertainty: {
    co2?: number | null;
    ch4?: number | null;
    n2o?: number | null;
    [key: string]: any;
  };
  userUncertainty: {
    co2?: string | number;
    ch4?: string | number;
    n2o?: string | number;
    [key: string]: any;
  };
}

// Extracted from Scope1Form.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
export const Scope1OptionsSection: React.FC<Scope1OptionsSectionProps> = ({
  gcUncertaintyPct,
  meterUncertaintyPct,
  renderSpecificForm,
  setGcUncertaintyPct,
  setMeterUncertaintyPct,
  setUserUncertainty,
  sourceType,
  uncertainty,
  userUncertainty,
}) => (
  <Section n={3} title={t("Activity Data")}>
    <div className="s1-inputs">{renderSpecificForm()}</div>
    <MoreOptions label={t("Uncertainty")}>
      <div className="form-grid-3">
        {sourceType === "specific" && (
          <div className="input-group [grid-column:span_3]! [margin-bottom:8px]!">
            <label>{t("Measurement Instrumentation Precision")}</label>
            <div className="flex! gap-[8px]! flex-wrap!">
              <div className="flex-1! p-[8px_12px]! bg-[color:var(--color-legacy-f3f4f6)]! rounded-[6px]! [border:1px_solid_var(--color-legacy-e5e7eb)]! flex! justify-between! items-center!">
                <span className="text-xs font-semibold text-text">
                  {t("Meter Calibration Tolerance")}
                </span>
                <div className="flex! items-center!">
                  <span className="text-sm text-text-secondary mr-1">±</span>
                  <Input
                    type="number"
                    className="w-20 h-9 px-2.5 text-sm font-mono text-right"
                    placeholder="2.0"
                    value={meterUncertaintyPct}
                    onChange={(e) => setMeterUncertaintyPct(e.target.value)}
                    step="0.1"
                  />
                  <span className="text-sm text-text-secondary ml-1">%</span>
                </div>
              </div>
              <div className="flex-1! p-[8px_12px]! bg-[color:var(--color-legacy-f3f4f6)]! rounded-[6px]! [border:1px_solid_var(--color-legacy-e5e7eb)]! flex! justify-between! items-center!">
                <span className="text-xs font-semibold text-text">
                  {t("GC Analytical Precision")}
                </span>
                <div className="flex! items-center!">
                  <span className="text-sm text-text-secondary mr-1">±</span>
                  <Input
                    type="number"
                    className="w-20 h-9 px-2.5 text-sm font-mono text-right"
                    placeholder={t("Opt.")}
                    value={gcUncertaintyPct}
                    onChange={(e) => setGcUncertaintyPct(e.target.value)}
                    step="0.1"
                  />
                  <span className="text-sm text-text-secondary ml-1">%</span>
                </div>
              </div>
              <div className="flex-1!"></div>
            </div>
          </div>
        )}
        <div className="input-group [grid-column:span_3]!">
          <label>{t("Emission Factor / Direct Measurement Uncertainty Override (±%)")}</label>
          <div className="flex! gap-[8px]! flex-wrap!">
            <div className="flex-1! p-[8px_12px]! bg-[color:var(--color-legacy-f3f4f6)]! rounded-[6px]! [border:1px_solid_var(--color-legacy-e5e7eb)]! flex! justify-between! items-center!">
              <span className="text-xs font-semibold text-text">{t("CO₂")}</span>
              {sourceType === "specific" ? (
                <div className="flex! items-center!">
                  <span className="text-sm text-text-secondary mr-1">±</span>
                  <Input
                    type="number"
                    className="w-20 h-9 px-2.5 text-sm font-mono text-right"
                    placeholder="—"
                    value={userUncertainty.co2}
                    onChange={(e) =>
                      setUserUncertainty({
                        ...userUncertainty,
                        co2: e.target.value,
                      })
                    }
                  />
                  <span className="text-sm text-text-secondary ml-1">%</span>
                </div>
              ) : (
                <span
                  className={`[font-size:0.85rem]! [font-weight:700]! ${uncertainty.co2 != null ? "[color:var(--color-green-700)]!" : "[color:var(--color-legacy-9ca3af)]!"}`}
                >
                  {uncertainty.co2 != null ? `±${(uncertainty.co2 * 100).toFixed(0)}%` : "—"}
                </span>
              )}
            </div>
            <div className="flex-1! p-[8px_12px]! bg-[color:var(--color-legacy-f3f4f6)]! rounded-[6px]! [border:1px_solid_var(--color-legacy-e5e7eb)]! flex! justify-between! items-center!">
              <span className="text-xs font-semibold text-text">{t("CH₄")}</span>
              {sourceType === "specific" ? (
                <div className="flex! items-center!">
                  <span className="text-sm text-text-secondary mr-1">±</span>
                  <Input
                    type="number"
                    className="w-20 h-9 px-2.5 text-sm font-mono text-right"
                    placeholder="—"
                    value={userUncertainty.ch4}
                    onChange={(e) =>
                      setUserUncertainty({
                        ...userUncertainty,
                        ch4: e.target.value,
                      })
                    }
                  />
                  <span className="text-sm text-text-secondary ml-1">%</span>
                </div>
              ) : (
                <span
                  className={`[font-size:0.85rem]! [font-weight:700]! ${uncertainty.ch4 != null ? "[color:var(--color-blue-700)]!" : "[color:var(--color-legacy-9ca3af)]!"}`}
                >
                  {uncertainty.ch4 != null ? `±${(uncertainty.ch4 * 100).toFixed(0)}%` : "—"}
                </span>
              )}
            </div>
            <div className="flex-1! p-[8px_12px]! bg-[color:var(--color-legacy-f3f4f6)]! rounded-[6px]! [border:1px_solid_var(--color-legacy-e5e7eb)]! flex! justify-between! items-center!">
              <span className="text-xs font-semibold text-text">N₂O</span>
              {sourceType === "specific" ? (
                <div className="flex! items-center!">
                  <span className="text-sm text-text-secondary mr-1">±</span>
                  <Input
                    type="number"
                    className="w-20 h-9 px-2.5 text-sm font-mono text-right"
                    placeholder="—"
                    value={userUncertainty.n2o}
                    onChange={(e) =>
                      setUserUncertainty({
                        ...userUncertainty,
                        n2o: e.target.value,
                      })
                    }
                  />
                  <span className="text-sm text-text-secondary ml-1">%</span>
                </div>
              ) : (
                <span
                  className={`[font-size:0.85rem]! [font-weight:700]! ${uncertainty.n2o != null ? "[color:var(--color-violet-700)]!" : "[color:var(--color-legacy-9ca3af)]!"}`}
                >
                  {uncertainty.n2o != null ? `±${(uncertainty.n2o * 100).toFixed(0)}%` : "—"}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </MoreOptions>
  </Section>
);

export default Scope1OptionsSection;
