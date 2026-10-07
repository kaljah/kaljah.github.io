import React from "react";
import { RotateCcw, Search, X } from "lucide-react";
import { Button, Card, Field, IconButton, Input, NativeSelect } from "../../ui";
import { controlClass } from "../../components/import-wizard/mapping";

const TIMEFRAMES = [
  ["all", "All Time"],
  ["today", "Today"],
  ["7days", "Last 7 Days"],
  ["30days", "Last 30 Days"],
  ["custom", "Custom Range"],
] as const;

export interface AuditTrailFiltersBarCardProps {
  auditLogs: any[];
  availableFilters: {
    users: string[];
    actions: string[];
    entities: string[];
  };
  customEndDate: string;
  customStartDate: string;
  filterAction: string;
  filterEntity: string;
  filterUser: string;
  hasActiveFilters: boolean;
  resetFilters: () => void;
  searchQuery: string;
  setCustomEndDate: (val: string) => void;
  setCustomStartDate: (val: string) => void;
  setFilterAction: (val: string) => void;
  setFilterEntity: (val: string) => void;
  setFilterUser: (val: string) => void;
  setPage: (val: number) => void;
  setSearchQuery: (val: string) => void;
  setTimeframe: (val: string) => void;
  timeframe: string;
  totalRecords: number;
}

/** Search box plus user / action / entity / timeframe filters. Every change returns to page 1. */
const AuditTrailFiltersBarCard: React.FC<AuditTrailFiltersBarCardProps> = ({
  auditLogs,
  availableFilters,
  customEndDate,
  customStartDate,
  filterAction,
  filterEntity,
  filterUser,
  hasActiveFilters,
  resetFilters,
  searchQuery,
  setCustomEndDate,
  setCustomStartDate,
  setFilterAction,
  setFilterEntity,
  setFilterUser,
  setPage,
  setSearchQuery,
  setTimeframe,
  timeframe,
  totalRecords,
}) => {
  const select = (label: string, value: string, set: (val: string) => void, all: string, items: string[]) => (
    <Field label={label} className="min-w-[150px] flex-1">
      <NativeSelect
        className={controlClass}
        value={value}
        onChange={(e) => {
          set(e.target.value);
          setPage(1);
        }}
      >
        <option value="all">{all}</option>
        {items.map((v) => (
          <option key={v} value={v}>
            {v}
          </option>
        ))}
      </NativeSelect>
    </Field>
  );
  const date = (label: string, value: string, set: (val: string) => void) => (
    <Input
      type="date"
      aria-label={label}
      title={label}
      value={value}
      className="w-auto"
      onChange={(e) => {
        set(e.target.value);
        setPage(1);
      }}
    />
  );

  return (
    <Card className="mb-7 flex flex-col gap-4">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-text-secondary" aria-hidden="true" />
        <Input
          aria-label="Search audit log"
          className="px-10"
          placeholder="Search by user, description, record ID, IP address, or entity..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <IconButton label="Clear search" className="absolute right-1 top-1/2 size-7 -translate-y-1/2" onClick={() => setSearchQuery("")}>
            <X className="size-3.5" aria-hidden="true" />
          </IconButton>
        )}
      </div>

      <div className="flex flex-wrap items-end gap-3.5">
        {select("User", filterUser, setFilterUser, "All Users", availableFilters.users)}
        {select("Action", filterAction, setFilterAction, "All Actions", availableFilters.actions)}
        {select("Entity", filterEntity, setFilterEntity, "All Entities", availableFilters.entities)}
        <Field label="Timeframe" className="min-w-[150px] flex-1">
          <NativeSelect
            className={controlClass}
            value={timeframe}
            onChange={(e) => {
              setTimeframe(e.target.value);
              setPage(1);
            }}
          >
            {TIMEFRAMES.map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </NativeSelect>
        </Field>

        {timeframe === "custom" && (
          <div className="flex items-center gap-2 pb-1">
            {date("Start date", customStartDate, setCustomStartDate)}
            <span className="text-sm text-text-secondary">to</span>
            {date("End date", customEndDate, setCustomEndDate)}
          </div>
        )}

        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={resetFilters} title="Reset all filters">
            <RotateCcw className="size-3.5" aria-hidden="true" /> Reset
          </Button>
        )}

        <p className="m-0 ml-auto pb-2 text-sm text-text-secondary">
          Showing <strong>{auditLogs.length}</strong> of <strong>{totalRecords}</strong> records
        </p>
      </div>
    </Card>
  );
};

export default AuditTrailFiltersBarCard;
