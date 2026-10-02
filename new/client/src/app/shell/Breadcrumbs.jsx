import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { useLayout } from "../../context/LayoutContext";
import { findRoute } from "../routes.config";

/** Group / Page [/ sub-stage], generated from the route config. */
const Breadcrumbs = () => {
  const { pathname } = useLocation();
  const { breadcrumbExtra } = useLayout();
  const route = findRoute(pathname);
  if (!route) return null;

  const crumbs = [];
  if (route.group) crumbs.push({ label: route.group });
  crumbs.push({ label: route.title, to: breadcrumbExtra ? route.path : undefined });
  if (breadcrumbExtra) crumbs.push({ label: breadcrumbExtra });

  return (
    <nav aria-label="Breadcrumb" className="min-w-0">
      <ol className="m-0 flex list-none items-center gap-1.5 whitespace-nowrap p-0 text-base">
        {crumbs.map((c, i) => {
          const last = i === crumbs.length - 1;
          return (
            <li key={c.label} className="flex items-center gap-1.5">
              {i > 0 && <ChevronRight className="size-3.5 text-ink-400" aria-hidden="true" />}
              {c.to ? (
                <Link to={c.to} className="text-text-secondary no-underline hover:text-text">
                  {c.label}
                </Link>
              ) : (
                <span
                  aria-current={last ? "page" : undefined}
                  className={last ? "font-semibold text-text" : "text-text-secondary"}
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
