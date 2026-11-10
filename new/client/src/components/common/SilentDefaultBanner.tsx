import React from "react";
import { AlertTriangle, BookOpen } from "lucide-react";
import { Button } from "../../ui";

export interface SilentDefaultBannerProps {
  parameterName: string;
  defaultValue: string | number;
  defaultUnit?: string;
  sourceCitation: string;
  factorId?: string;
  onInspect: () => void;
  className?: string;
  isSilentDefault?: boolean;
}

export const SilentDefaultBanner: React.FC<SilentDefaultBannerProps> = ({
  parameterName,
  defaultValue,
  defaultUnit = "",
  sourceCitation,
  factorId,
  onInspect,
  className = "",
  isSilentDefault = true,
}) => {
  if (!isSilentDefault) return null;

  return (
    <div
      role="alert"
      className={`border border-amber-500/40 bg-amber-950/20 rounded-lg p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs ${className}`}
    >
      <div className="flex items-start gap-2.5">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-amber-300">
            Silent Default Applied ({factorId || "EST-DEF"}):
          </span>{" "}
          <span className="text-amber-200/90">
            Relying on unmetered assumption for <strong>{parameterName}</strong> ({defaultValue} {defaultUnit}).
            Citation: <em>{sourceCitation}</em>.
          </span>
        </div>
      </div>
      <Button
        variant="secondary"
        size="sm"
        onClick={onInspect}
        className="shrink-0 flex items-center gap-1.5 border-amber-500/30 text-amber-200 hover:bg-amber-500/10 text-xs py-1 px-2.5 h-auto"
      >
        <BookOpen className="w-3.5 h-3.5" />
        Inspect Provenance & Override
      </Button>
    </div>
  );
};

export default SilentDefaultBanner;
