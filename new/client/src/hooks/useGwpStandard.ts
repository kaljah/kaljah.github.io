import { useState, useEffect } from "react";
import api from "../api";
import { GWP_STANDARDS } from "../constants";

let cachedStandard: "AR4" | "AR5" | "AR6" | null = null;
let pending: Promise<string | null> | null = null;

const normalise = (raw: unknown): "AR4" | "AR5" | "AR6" | null => {
  const str = String(raw || "").toUpperCase();
  if (str.includes("AR4")) return "AR4";
  if (str.includes("AR6")) return "AR6";
  if (str.includes("AR5")) return "AR5";
  return null;
};

export interface GwpValues {
  CO2: number;
  CH4: number;
  N2O: number;
  CH4_20?: number;
  N2O_20?: number;
  [key: string]: number | undefined;
}

export interface UseGwpStandardResult {
  standard: "AR4" | "AR5" | "AR6" | null;
  gwp: GwpValues | null;
  loaded: boolean;
}

export function useGwpStandard(): UseGwpStandardResult {
  const [standard, setStandard] = useState<"AR4" | "AR5" | "AR6" | null>(cachedStandard);

  useEffect(() => {
    if (cachedStandard) return undefined;
    let cancelled = false;
    if (!pending) {
      pending = api
        .get("/auth/settings")
        .then((res: any) => normalise(res?.data?.gwp_standard) || "AR5")
        .catch(() => null)
        .finally(() => {
          pending = null;
        });
    }
    pending?.then((std) => {
      const validStd = std === "AR4" || std === "AR5" || std === "AR6" ? std : null;
      if (validStd) cachedStandard = validStd;
      if (!cancelled) setStandard(validStd);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    standard,
    gwp: standard && GWP_STANDARDS ? ((GWP_STANDARDS as Record<string, GwpValues>)[standard] ?? null) : null,
    loaded: standard !== null,
  };
}

export default useGwpStandard;
