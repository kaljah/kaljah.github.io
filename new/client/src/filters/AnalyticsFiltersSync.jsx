import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { findRoute } from "../app/routes.config";
import { FILTER_KEYS, getFilters, setFilters, subscribe } from "./filterStore";

/**
 * Keeps the shared filters and the URL query in sync on routes flagged with filters: true.
 * URL to store on arrival (deep links win); store to URL on every change.
 * The store subscription outlives route changes, so it always reads the latest location and navigate
 * from refs (a stale setSearchParams would navigate back to the route it was created on).
 */
const AnalyticsFiltersSync = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const enabled = Boolean(findRoute(location.pathname)?.filters);

  const locationRef = useRef(location);
  const navigateRef = useRef(navigate);
  locationRef.current = location;
  navigateRef.current = navigate;

  const writeUrl = () => {
    const { pathname, search } = locationRef.current;
    if (!findRoute(pathname)?.filters) return;
    const next = new URLSearchParams(search);
    const f = getFilters();
    for (const k of FILTER_KEYS) {
      if (f[k] === "all") next.delete(k);
      else next.set(k, f[k]);
    }
    const nextSearch = next.toString() ? `?${next.toString()}` : "";
    if (nextSearch !== search) navigateRef.current({ pathname, search: nextSearch }, { replace: true });
  };

  // arriving on a filtered route: adopt filters present in the URL, otherwise publish the stored ones
  useEffect(() => {
    if (!enabled) return;
    const params = new URLSearchParams(locationRef.current.search);
    const fromUrl = {};
    for (const k of FILTER_KEYS) {
      const v = params.get(k);
      if (v) fromUrl[k] = v;
    }
    if (Object.keys(fromUrl).length) setFilters(fromUrl);
    else writeUrl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, location.pathname]);

  useEffect(() => subscribe(writeUrl), []); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
};

export default AnalyticsFiltersSync;
