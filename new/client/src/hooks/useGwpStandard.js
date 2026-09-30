import { useState, useEffect } from "react";
import api from "../api";
import { GWP_STANDARDS } from "../constants";

/**
 * BUG-082 / BUG-013: expose the organisation's active IPCC GWP standard
 * (from /auth/settings.gwp_standard) together with the values the client
 * constants hold for it, so labels and tooltips never hard-code GWPs.
 *
 * Returns { standard, gwp, loaded } where `gwp` is the constants entry
 * ({ CO2, CH4, N2O, CH4_20, N2O_20 }). Until the settings load, `standard`
 * is null and `gwp` is null, so callers can show a neutral placeholder.
 */
let cachedStandard = null;
let pending = null;

const normalise = (raw) => {
  const str = String(raw || "").toUpperCase();
  if (str.includes("AR4")) return "AR4";
  if (str.includes("AR6")) return "AR6";
  if (str.includes("AR5")) return "AR5";
  return null;
};

export function useGwpStandard() {
  const [standard, setStandard] = useState(cachedStandard);

  useEffect(() => {
    if (cachedStandard) return undefined;
    let cancelled = false;
    if (!pending) {
      pending = api
        .get("/auth/settings")
        .then((res) => normalise(res?.data?.gwp_standard) || "AR5")
        .catch(() => null)
        .finally(() => {
          pending = null;
        });
    }
    pending.then((std) => {
      if (std) cachedStandard = std;
      if (!cancelled) setStandard(std);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    standard,
    gwp: standard ? GWP_STANDARDS[standard] : null,
    loaded: standard !== null,
  };
}

export default useGwpStandard;
