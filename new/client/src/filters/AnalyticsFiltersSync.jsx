import { useEffect, useRef } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { findRoute } from "../app/routes.config";
import { FILTER_KEYS, getFilters, setFilters, subscribe } from "./filterStore";

/**
 * Keeps the shared filters and the URL query in sync on routes flagged with filters: true.
 * URL to store on arrival (deep links win); store to URL on every change.
 */
const AnalyticsFiltersSync = () => {
  const { pathname } = useLocation();
  const [params, setParams] = useSearchParams();
  const enabled = Boolean(findRoute(pathname)?.filters);
  const paramsRef = useRef(params);
  paramsRef.current = params;

  // arriving on a filtered route: adopt filters present in the URL
  useEffect(() => {
    if (!enabled) return;
    const fromUrl = {};
    for (const k of FILTER_KEYS) {
      const v = paramsRef.current.get(k);
      if (v) fromUrl[k] = v;
    }
    if (Object.keys(fromUrl).length) setFilters(fromUrl);
    else writeUrl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, pathname]);

  function writeUrl() {
    const next = new URLSearchParams(paramsRef.current);
    const f = getFilters();
    for (const k of FILTER_KEYS) f[k] === "all" ? next.delete(k) : next.set(k, f[k]);
    if (next.toString() !== paramsRef.current.toString()) setParams(next, { replace: true });
  }

  useEffect(() => {
    if (!enabled) return undefined;
    return subscribe(writeUrl);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return null;
};

export default AnalyticsFiltersSync;
