import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { useLayout } from "../../context/LayoutContext";
import { findRoute } from "../routes.config";

interface Crumb {
  label: React.ReactNode;
  to?: string;
}

/** Group / Page [/ sub-stage], generated from the route config. */
const Breadcrumbs: React.FC = () => {
  const { pathname } = useLocation();
  const { breadcrumbExtra } = useLayout();
  const route = findRoute(pathname);
  if (!route) return null;

  const crumbs: Crumb[] = [];
  if (route.group) crumbs.push({ label: route.group });
  crumbs.push({ label: route.title, to: breadcrumbExtra ? route.path : undefined });
  if (breadcrumbExtra) crumbs.push({ label: breadcrumbExtra });

  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="m-0 flex min-w-0 list-none items-center gap-1.5 overflow-hidden whitespace-nowrap p-0 text-base">
        {crumbs.map((c, i) => {
          const last = i === crumbs.length - 1;
          const key = typeof c.label === "string" ? c.label : String(i);
          return (
            <li key={key} className={last ? "flex min-w-0 items-center gap-1.5" : "hidden items-center gap-1.5 sm:flex"}>
              {i > 0 && <ChevronRight className="hidden size-3.5 shrink-0 text-ink-400 sm:block" aria-hidden="true" />}
              {c.to ? (
                <Link to={c.to} className="text-text-secondary no-underline hover:text-text">
                  {c.label}
                </Link>
              ) : (
                <span
                  aria-current={last ? "page" : undefined}
                  className={last ? "truncate font-semibold text-text" : "text-text-secondary"}
                >
                  {c.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
};

export default Breadcrumbs;
