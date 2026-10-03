import React from "react";
import { NativeSelect } from "../../ui/NativeSelect";
import { RotateCcw, Search, X } from "lucide-react";

// Extracted from AuditTrail.jsx; markup and behavior are unchanged. State and handlers stay in the parent.
const AuditTrailFiltersBarCard = ({ auditLogs, availableFilters, customEndDate, customStartDate, filterAction, filterEntity, filterUser, hasActiveFilters, resetFilters, searchQuery, setCustomEndDate, setCustomStartDate, setFilterAction, setFilterEntity, setFilterUser, setPage, setSearchQuery, setTimeframe, timeframe, totalRecords }) => (
<div className="[background:var(--bg-card,_rgba(255,_255,_255,_0.85))] [backdrop-filter:blur(14px)] [border:1px_solid_var(--border-color,_rgba(226,_232,_240,_0.85))] [border-radius:var(--radius-lg)] [padding:18px_22px] [margin-bottom:28px] [box-shadow:var(--shadow-card)]">
          <div className="filter-search-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by user, description, record ID, IP address, or entity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="audit-search-input"
            />
            {searchQuery && (
              <button
                className="search-clear-btn"
                onClick={() => setSearchQuery("")}
                title="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </div>

          <div className="filter-dropdowns-row">
            {/* User Filter */}
            <div className="filter-control">
              <label>User</label>
              <NativeSelect
                value={filterUser}
                onChange={(e) => {
                  setFilterUser(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Users</option>
                {availableFilters.users.map((u) => (
                  <option key={u} value={u}>
                    {u}
                  </option>
                ))}
              </NativeSelect>
            </div>

            {/* Action Filter */}
            <div className="filter-control">
              <label>Action</label>
              <NativeSelect
                value={filterAction}
                onChange={(e) => {
                  setFilterAction(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Actions</option>
                {availableFilters.actions.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
              </NativeSelect>
            </div>

            {/* Entity Filter */}
            <div className="filter-control">
              <label>Entity</label>
              <NativeSelect
                value={filterEntity}
                onChange={(e) => {
                  setFilterEntity(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Entities</option>
                {availableFilters.entities.map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
              </NativeSelect>
            </div>

            {/* Timeframe Preset */}
            <div className="filter-control">
              <label>Timeframe</label>
              <NativeSelect
                value={timeframe}
                onChange={(e) => {
                  setTimeframe(e.target.value);
                  setPage(1);
                }}
              >
                <option value="all">All Time</option>
                <option value="today">Today</option>
                <option value="7days">Last 7 Days</option>
                <option value="30days">Last 30 Days</option>
                <option value="custom">Custom Range</option>
              </NativeSelect>
            </div>

            {/* Custom Date Pickers */}
            {timeframe === "custom" && (
              <div className="[display:flex] [align-items:center] [gap:8px]">
                <input
                  type="date"
                  value={customStartDate}
                  onChange={(e) => {
                    setCustomStartDate(e.target.value);
                    setPage(1);
                  }}
                  className="date-input"
                  title="Start Date"
                />
                <span className="[font-size:var(--text-sm)] [color:var(--text-secondary,_var(--color-ink-500))]">to</span>
                <input
                  type="date"
                  value={customEndDate}
                  onChange={(e) => {
                    setCustomEndDate(e.target.value);
                    setPage(1);
                  }}
                  className="date-input"
                  title="End Date"
                />
              </div>
            )}

            {/* Reset Filters Button */}
            {hasActiveFilters && (
              <button className="btn-reset-filters" onClick={resetFilters} title="Reset all filters">
                <RotateCcw size={13} />
                <span>Reset</span>
              </button>
            )}

            <div className="filter-result-count">
              Showing <strong>{auditLogs.length}</strong> of <strong>{totalRecords}</strong> records
            </div>
          </div>
        </div>
);

export default AuditTrailFiltersBarCard;
