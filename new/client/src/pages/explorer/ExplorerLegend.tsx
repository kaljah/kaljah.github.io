import React from "react";
import { ExternalLink, Satellite, X } from "lucide-react";
import { IconButton } from "../../ui";

const RAMP = "linear-gradient(90deg, #313695 0%, #4575b4 20%, #74add1 40%, #abd9e9 60%, #fee090 75%, #f46d43 90%, #a50026 100%)";

export interface ExplorerLegendProps {
  onClose: () => void;
}

/** Colour ramp for the TROPOMI CH4 column overlay. */
const ExplorerLegend: React.FC<ExplorerLegendProps> = ({ onClose }) => (
  <aside
    role="region"
    aria-label="Spectral Legend"
    className="absolute bottom-5 left-[370px] z-900 w-80 rounded-lg border border-border bg-surface/95 px-3.5 py-3 shadow-md backdrop-blur-lg max-[960px]:bottom-20 max-[960px]:left-5"
  >
    <div className="mb-2 flex items-center justify-between">
      <span className="flex items-center gap-1.5 text-xs font-bold text-text">
        <Satellite className="size-3.5 text-info-fg" aria-hidden="true" /> TROPOMI CH₄ column mole fraction
      </span>
      <IconButton label="Hide legend" className="size-6" onClick={onClose}>
        <X className="size-3" aria-hidden="true" />
      </IconButton>
    </div>
    {/* eslint-disable-next-line no-restricted-syntax -- the ramp is a data-colour gradient */}
    <div className="mb-1.5 h-2 rounded-sm shadow-inner" style={{ background: RAMP }} />
    <div className="mb-1.5 flex justify-between text-xs font-bold text-text-secondary">
      <span>&lt;1,750</span>
      <span>1,800</span>
      <span>1,850</span>
      <span>1,900</span>
      <span>&ge;1,950 ppb</span>
    </div>
    <div className="flex items-center justify-between border-t border-ink-100 pt-1.5 text-xs text-text-secondary">
      <span>SWIR Band 7/8 (2.3 µm) • L3 5.5×7 km</span>
      <a
        href="https://dataspace.copernicus.eu"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 font-semibold text-info-fg no-underline hover:underline"
      >
        CDSE Hub <ExternalLink className="size-2.5" aria-hidden="true" />
      </a>
    </div>
  </aside>
);

export default ExplorerLegend;
