import React, { useEffect, useMemo, useState, useRef } from "react";
import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type Row,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ArrowDown, ArrowRight, ArrowUp, Check, ChevronsUpDown, Columns3 } from "lucide-react";
import { Button } from "../Button";
import { EmptyState } from "../EmptyState";
import { Menu, MenuContent, MenuLabel, MenuTrigger } from "../Menu";
import { Skeleton } from "../Skeleton";
import { cn } from "../cn";
import { t } from "../../i18n";

const storageKey = (id: string) => `ct.table.${id}.hidden`;

const readHidden = (tableId?: string, defaultHidden?: string[]): VisibilityState => {
  try {
    const raw = tableId ? localStorage.getItem(storageKey(tableId)) : null;
    if (raw) return JSON.parse(raw);
  } catch {
    // storage unavailable: fall back to defaults
  }
  return Object.fromEntries((defaultHidden ?? []).map((id) => [id, false]));
};

export interface DataTableColumnMeta {
  numeric?: boolean;
  pin?: "left" | "right";
  unit?: string;
  [key: string]: unknown;
}

export interface DataTableProps<TData> {
  tableId?: string;
  data?: TData[];
  columns: ColumnDef<TData, any>[];
  defaultHidden?: string[];
  pageSize?: number;
  density?: "comfortable" | "compact";
  loading?: boolean;
  empty?: React.ReactNode;
  getRowId?: (originalRow: TData, index: number, parent?: Row<TData>) => string;
  onRowClick?: (row: TData) => void;
  caption?: string;
  className?: string;
  showColumnMenu?: boolean;
  showPagination?: boolean;
  pinFirstColumn?: boolean | "mobile-only";
}

/**
 * Data grid on a headless table. Column meta supports numeric, pin (left or right) and unit.
 * Numeric columns are right-aligned with tabular figures. The header is sticky, and the
 * visible-column choice is remembered per tableId.
 */
export function DataTable<TData>({
  tableId,
  data,
  columns,
  defaultHidden,
  pageSize = 25,
  density = "comfortable",
  loading = false,
  empty,
  getRowId,
  onRowClick,
  caption,
  className,
  showColumnMenu = true,
  showPagination = true,
  pinFirstColumn = "mobile-only",
}: DataTableProps<TData>): React.ReactElement {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(() => readHidden(tableId, defaultHidden));
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [canScrollLeft, setCanScrollLeft] = useState(false);

  const checkScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 6);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 6);
  };

  useEffect(() => {
    if (!tableId) return;
    try {
      localStorage.setItem(storageKey(tableId), JSON.stringify(columnVisibility));
    } catch {
      // storage unavailable: the choice is simply not remembered
    }
  }, [tableId, columnVisibility]);

  const tableData = useMemo(() => data ?? [], [data]);
  // eslint-disable-next-line react-hooks/incompatible-library -- TanStack Table is not memoizable by the React Compiler
  const table = useReactTable({
    data: tableData,
    columns,
    getRowId,
    state: { sorting, columnVisibility },
    onSortingChange: setSorting,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  const rows = table.getRowModel().rows;
  const cell = density === "compact" ? "px-3 py-1.5" : "px-3 py-2.5";
  const hideable = table.getAllLeafColumns().filter((c) => c.getCanHide());

  useEffect(() => {
    checkScroll();
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", checkScroll, { passive: true });
    window.addEventListener("resize", checkScroll);
    return () => {
      el.removeEventListener("scroll", checkScroll);
      window.removeEventListener("resize", checkScroll);
    };
  }, [rows, columnVisibility]);

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {showColumnMenu && hideable.length > 1 && (
        <div className="flex justify-end">
          <Menu>
            <MenuTrigger asChild>
              <Button variant="secondary" size="sm">
                <Columns3 className="size-4" aria-hidden="true" />
                {t("Columns")}
              </Button>
            </MenuTrigger>
            <MenuContent>
              <MenuLabel>{t("Show columns")}</MenuLabel>
              {hideable.map((col) => (
                <DropdownMenu.CheckboxItem
                  key={col.id}
                  checked={col.getIsVisible()}
                  onCheckedChange={(v) => col.toggleVisibility(Boolean(v))}
                  onSelect={(e) => e.preventDefault()}
                  className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-1.5 text-base outline-none data-highlighted:bg-ink-100"
                >
                  <span
                    aria-hidden="true"
                    className={cn(
                      "inline-flex size-4 items-center justify-center rounded-sm border text-white",
                      col.getIsVisible() ? "border-primary bg-primary" : "border-ink-300 bg-surface",
                    )}
                  >
                    {col.getIsVisible() && <Check className="size-3" />}
                  </span>
                  {typeof col.columnDef.header === "string" ? col.columnDef.header : col.id}
                </DropdownMenu.CheckboxItem>
              ))}
            </MenuContent>
          </Menu>
        </div>
      )}

      {/* Table Container with relative wrapper for scroll shadow cues */}
      <div className="relative">
        {canScrollRight && (
          <div className="flex items-center justify-end pb-1 pr-1 lg:hidden">
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-text-secondary">
              <span>{t("Swipe table horizontally")}</span>
              <ArrowRight className="size-3 text-brand-600" aria-hidden="true" />
            </span>
          </div>
        )}

        <div
          ref={scrollRef}
          className="relative overflow-x-auto rounded-lg border border-border bg-surface [webkit-overflow-scrolling:touch]"
        >
          {canScrollLeft && (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 left-0 z-25 w-6 bg-gradient-to-r from-ink-900/10 to-transparent max-lg:block hidden"
            />
          )}
          {canScrollRight && (
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-y-0 right-0 z-25 w-6 bg-gradient-to-l from-ink-900/10 to-transparent max-lg:block hidden"
            />
          )}

          <table className="w-full border-separate border-spacing-0 text-base">
            {caption && <caption className="sr-only">{caption}</caption>}
            <thead>
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header, headerIndex) => {
                    const meta = (header.column.columnDef.meta as DataTableColumnMeta) ?? {};
                    const sorted = header.column.getIsSorted();
                    const canSort = header.column.getCanSort();
                    const isFirst = headerIndex === 0;
                    const isPinnedLeft = meta.pin === "left" || (pinFirstColumn === true && isFirst);
                    const isPinnedMobileOnly = pinFirstColumn === "mobile-only" && isFirst && !meta.pin;
                    const isPinnedRight = meta.pin === "right";

                    return (
                      <th
                        key={header.id}
                        scope="col"
                        aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : undefined}
                        className={cn(
                          "sticky top-0 z-(--z-sticky) whitespace-nowrap border-b border-border bg-ink-50 text-xs font-medium uppercase tracking-wide text-text-secondary",
                          cell,
                          meta.numeric ? "text-right" : "text-left",
                          isPinnedLeft && "sticky left-0 z-30 bg-ink-50 shadow-[2px_0_5px_-2px_rgba(0,0,0,0.12)]",
                          isPinnedMobileOnly && "max-lg:sticky max-lg:left-0 max-lg:z-30 max-lg:bg-ink-50 max-lg:shadow-[2px_0_5px_-2px_rgba(0,0,0,0.12)]",
                          isPinnedRight && "sticky right-0 z-30 bg-ink-50 shadow-[-2px_0_5px_-2px_rgba(0,0,0,0.12)]",
                        )}
                      >
                        {header.isPlaceholder ? null : canSort ? (
                          <button
                            type="button"
                            onClick={header.column.getToggleSortingHandler()}
                            className="inline-flex cursor-pointer items-center gap-1 border-0 bg-transparent p-0 font-[inherit] uppercase text-inherit hover:text-text"
                          >
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            {meta.unit && <span className="normal-case">({meta.unit})</span>}
                            {sorted === "asc" ? (
                              <ArrowUp className="size-3" aria-hidden="true" />
                            ) : sorted === "desc" ? (
                              <ArrowDown className="size-3" aria-hidden="true" />
                            ) : (
                              <ChevronsUpDown className="size-3 opacity-40" aria-hidden="true" />
                            )}
                          </button>
                        ) : (
                          <>
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            {meta.unit && <span className="ml-1 normal-case">({meta.unit})</span>}
                          </>
                        )}
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      <td colSpan={table.getVisibleLeafColumns().length || 1} className={cell}>
                        <Skeleton className="h-4 w-full" />
                      </td>
                    </tr>
                  ))
                : rows.map((row) => (
                    <tr
                      role="row"
                      key={row.id}
                      onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                      tabIndex={onRowClick ? 0 : undefined}
                      onKeyDown={
                        onRowClick
                          ? (e) => {
                              if (e.target === e.currentTarget && (e.key === "Enter" || e.key === " ")) {
                                e.preventDefault();
                                onRowClick(row.original);
                              }
                            }
                          : undefined
                      }
                      className={cn("group", onRowClick && "cursor-pointer hover:bg-selected-bg")}
                    >
                      {row.getVisibleCells().map((c, cellIndex) => {
                        const meta = (c.column.columnDef.meta as DataTableColumnMeta) ?? {};
                        const isFirst = cellIndex === 0;
                        const isPinnedLeft = meta.pin === "left" || (pinFirstColumn === true && isFirst);
                        const isPinnedMobileOnly = pinFirstColumn === "mobile-only" && isFirst && !meta.pin;
                        const isPinnedRight = meta.pin === "right";

                        return (
                          <td
                            key={c.id}
                            className={cn(
                              "border-b border-ink-100 text-text transition-colors",
                              cell,
                              meta.numeric && "text-right tabular-nums",
                              isPinnedLeft && "sticky left-0 z-10 bg-surface shadow-[2px_0_5px_-2px_rgba(0,0,0,0.12)] group-hover:bg-selected-bg group-focus:bg-selected-bg",
                              isPinnedMobileOnly && "max-lg:sticky max-lg:left-0 max-lg:z-10 max-lg:bg-surface max-lg:shadow-[2px_0_5px_-2px_rgba(0,0,0,0.12)] group-hover:bg-selected-bg group-focus:bg-selected-bg",
                              isPinnedRight && "sticky right-0 z-10 bg-surface shadow-[-2px_0_5px_-2px_rgba(0,0,0,0.12)] group-hover:bg-selected-bg group-focus:bg-selected-bg",
                            )}
                          >
                            {flexRender(c.column.columnDef.cell, c.getContext())}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
            </tbody>
          </table>
          {!loading &&
            rows.length === 0 &&
            (empty ?? <EmptyState title={t("No records")} description={t("Nothing matches the current filters.")} />)}
        </div>
      </div>

      {showPagination && table.getPageCount() > 1 && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-text-secondary">
          <span>
            {t("Page")}{" "}{table.getState().pagination.pageIndex + 1}{" "}{t("of")}{" "}{table.getPageCount()} ({tableData.length}{" "}{t("rows)")}
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              className="min-h-[36px] min-w-[36px] px-3 touch-manipulation"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              {t("Previous")}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="min-h-[36px] min-w-[36px] px-3 touch-manipulation"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              {t("Next")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
