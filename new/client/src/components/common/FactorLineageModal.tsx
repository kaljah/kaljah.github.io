import React, { useState } from "react";
import Modal from "../Modal";
import { Button, Input, Field, Badge } from "../../ui";
import { BookOpen, AlertTriangle, ShieldCheck, CheckCircle2 } from "lucide-react";

export interface FactorLineageItem {
  id: string;
  factor_key?: string;
  parameter_name: string;
  value: number;
  unit: string;
  basis: string;
  source_document: string;
  edition_year: string;
  table_or_equation_ref: string;
  page_number?: string;
  verbatim_citation: string;
  is_user_overridable: boolean;
  is_silent_default: boolean;
  warning_flag?: string;
}

export interface FactorLineageModalProps {
  isOpen: boolean;
  onClose: () => void;
  factors: FactorLineageItem[];
  title?: string;
  onApplyOverride?: (overrides: Record<string, { value: number; justification: string }>) => void;
}

export const FactorLineageModal: React.FC<FactorLineageModalProps> = ({
  isOpen,
  onClose,
  factors,
  title = "Methodology Factor Provenance & Literature Citation",
  onApplyOverride,
}) => {
  const [overrideValues, setOverrideValues] = useState<Record<string, string>>({});
  const [justifications, setJustifications] = useState<Record<string, string>>({});
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleValueChange = (id: string, val: string) => {
    setOverrideValues((prev) => ({ ...prev, [id]: val }));
    setSavedSuccess(false);
  };

  const handleJustificationChange = (id: string, text: string) => {
    setJustifications((prev) => ({ ...prev, [id]: text }));
    setSavedSuccess(false);
  };

  const handleSave = () => {
    if (!onApplyOverride) return;
    const result: Record<string, { value: number; justification: string }> = {};
    for (const [id, valStr] of Object.entries(overrideValues)) {
      const num = parseFloat(valStr);
      if (!isNaN(num)) {
        result[id] = {
          value: num,
          justification: justifications[id] || "Facility-specific engineering override",
        };
      }
    }
    onApplyOverride(result);
    setSavedSuccess(true);
    setTimeout(() => {
      onClose();
    }, 600);
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} maxWidth="750px">
      <div className="space-y-6 text-sm text-gray-200">
        <div className="bg-blue-950/40 border border-blue-800/40 rounded-lg p-3.5 flex items-start gap-3">
          <BookOpen className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-blue-300">Authoritative Provenance Audit Trail</p>
            <p className="text-xs text-blue-200/80 mt-1">
              In accordance with ISO 14064-1:2018 §9 and GHG Protocol Chapter 11, every default factor
              is linked to verified primary literature citations with exact equation numbers and verbatim quotations.
            </p>
          </div>
        </div>

        {factors.map((factor) => {
          const isCaution =
            factor.warning_flag === "CAUTION_ASSUMPTION" ||
            factor.is_silent_default ||
            factor.warning_flag === "METHODOLOGY_DISCREPANCY";

          return (
            <div
              key={factor.id}
              className={`border rounded-lg p-4 space-y-3 ${
                isCaution ? "bg-amber-950/20 border-amber-500/40" : "bg-gray-900/40 border-gray-800"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-300 border border-gray-700">
                    {factor.id}
                  </span>
                  <span className="font-semibold text-white">{factor.parameter_name}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  {isCaution ? (
                    <Badge tone="warning" className="flex items-center gap-1 text-xs">
                      <AlertTriangle className="w-3 h-3" />
                      Assumption Default
                    </Badge>
                  ) : (
                    <Badge tone="success" className="flex items-center gap-1 text-xs">
                      <ShieldCheck className="w-3 h-3" />
                      Prescribed Default
                    </Badge>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs bg-black/20 p-2.5 rounded border border-gray-800/60">
                <div>
                  <span className="text-gray-400 block">App Value & Unit:</span>
                  <span className="font-mono text-gray-100 font-medium">
                    {factor.value} {factor.unit}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400 block">Physical Basis:</span>
                  <span className="text-gray-200">{factor.basis}</span>
                </div>
                <div>
                  <span className="text-gray-400 block">Reference Citation:</span>
                  <span className="text-gray-200 font-medium">{factor.source_document}</span>
                </div>
                <div className="col-span-2 sm:col-span-3">
                  <span className="text-gray-400 block">Table / Eq Reference:</span>
                  <span className="text-blue-300 font-mono">{factor.table_or_equation_ref}</span>
                </div>
              </div>

              {factor.verbatim_citation && (
                <div className="text-xs border-l-2 border-amber-400/80 pl-3 py-1 bg-amber-500/5 text-amber-200/90 italic">
                  &ldquo;{factor.verbatim_citation}&rdquo;
                </div>
              )}

              {factor.is_user_overridable && (
                <div className="pt-2 border-t border-gray-800/80 mt-2 space-y-2">
                  <p className="text-xs font-semibold text-gray-300">
                    Facility Override (Optional):
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <Field label={`Custom Value (${factor.unit})`}>
                      <Input
                        type="number"
                        step="any"
                        placeholder={`Default: ${factor.value}`}
                        value={overrideValues[factor.id] || ""}
                        onChange={(e) => handleValueChange(factor.id, e.target.value)}
                      />
                    </Field>
                    <Field label="Engineering Justification / Reference">
                      <Input
                        type="text"
                        placeholder="e.g., Demo Operator Co. 2024 facility audit"
                        value={justifications[factor.id] || ""}
                        onChange={(e) => handleJustificationChange(factor.id, e.target.value)}
                      />
                    </Field>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {savedSuccess && (
          <div className="flex items-center gap-2 text-green-400 text-xs font-medium bg-green-950/30 border border-green-800/40 p-2.5 rounded">
            <CheckCircle2 className="w-4 h-4" />
            Overrides applied successfully to session calculation.
          </div>
        )}

        <div className="flex justify-end gap-2.5 pt-2 border-t border-gray-800">
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
          {onApplyOverride && (
            <Button variant="primary" onClick={handleSave}>
              Save & Apply Overrides
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default FactorLineageModal;
