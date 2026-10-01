import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import Papa from "papaparse";
import api from "../api";
import { autoDetectMapping, missingRequiredFields } from "../utils/importMapping";
import { fittingMappings, withSavedMapping } from "../utils/savedMappings";
import { useToast } from "./Toast";
import UploadProgress from "./UploadProgress";
import SkipGroupList from "./SkipGroupList";
import "./Scope1ImportWizard.css";

// ─── SVG Icon Library ────────────────────────────────────────────────────────
const Icon = {
  Close: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  ),
  Check: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  ChevronRight: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  ),
  ChevronDown: ({ open }) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ transform: open ? "rotate(180deg)" : "rotate(0)", transition: "transform 0.2s" }}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  ArrowLeft: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="19" y1="12" x2="5" y2="12" /><polyline points="12 19 5 12 12 5" />
    </svg>
  ),
  Upload: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </svg>
  ),
  File: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  FileExcel: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="8" y1="13" x2="10" y2="13" /><line x1="14" y1="13" x2="16" y2="13" />
      <line x1="8" y1="17" x2="16" y2="17" />
    </svg>
  ),
  Wand: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 4V2m0 14v-2M8 9H2m14 0h-2M3.5 3.5l1.5 1.5M16.5 16.5l1.5 1.5M16.5 3.5 15 5M3.5 20.5 5 19" />
      <path d="m3 9 9 9 9-9-9-9Z" />
    </svg>
  ),
  Search: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  Warning: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  Info: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  ),
  Flame: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z" />
    </svg>
  ),
  Wind: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2" />
    </svg>
  ),
  Droplets: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M7 16.3c2.2 0 4-1.83 4-4.05 0-1.16-.57-2.26-1.71-3.19S7.29 6.75 7 5.3c-.29 1.45-1.14 2.84-2.29 3.76S3 11.1 3 12.25c0 2.22 1.8 4.05 4 4.05z" />
      <path d="M12.56 6.6A10.97 10.97 0 0 0 14 3.02c.5 2.5 2 4.9 4 6.5s3 3.5 3 5.5a6.98 6.98 0 0 1-11.91 4.97" />
    </svg>
  ),
  Container: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" /><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
    </svg>
  ),
  Cpu: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" />
      <line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" />
      <line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" />
      <line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" />
    </svg>
  ),
  Layers: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  ),
  Zap: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  ),
  Activity: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  Settings: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  Columns: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <line x1="9" y1="3" x2="9" y2="21" /><line x1="15" y1="3" x2="15" y2="21" />
    </svg>
  ),
  Download: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  ),
  Processing: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
};

// ─── Process catalogue (keys are the server's Scope 1 process types) ─────────
const COMP = ["c1","c2","c3","c4","c5","c6","c7","c8","c9","c10","co2_mol","n2_mol"];
const PROCESS_CATALOGUE = [
  { key: "combustion",    label: "Combustion",             IconComp: Icon.Flame,     tier3Extra: ["hhv", ...COMP, "combustion_efficiency", "operating_temperature", "temp_unit", "operating_pressure", "press_unit", "z_factor"] },
  { key: "flaring",       label: "Flaring",                IconComp: Icon.Flame,     tier3Extra: ["flare_type", "combustion_efficiency", "destruction_efficiency", "control_efficiency", ...COMP] },
  { key: "venting",       label: "Venting",                IconComp: Icon.Wind,      tier3Extra: ["vent_method", "disposition", "ch4_content", "co2_content"] },
  { key: "blowdown",      label: "Blowdowns",              IconComp: Icon.Zap,       tier3Extra: ["blowdown_pressure", "blowdown_events", "blowdown_temp", "blowdown_temp_unit", "blowdown_press_unit", "z_factor", "ch4_content", "co2_content"] },
  { key: "tank_flashing", label: "Tank Flashing",          IconComp: Icon.Container, tier3Extra: ["tank_gor", "tank_ch4_content", "tank_control_eff", "tank_api_gravity"] },
  { key: "pneumatic",     label: "Pneumatic Devices",      IconComp: Icon.Cpu,       tier3Extra: ["pneu_count", "pneu_bleed_rate", "pneu_bleed_unit", "pneu_hours", "pneu_ch4_content"] },
  { key: "fugitive",      label: "Equipment Leaks",        IconComp: Icon.Droplets,  tier3Extra: ["fugitive_method", "component_type", "service", "m21_below_count", "m21_above_count"] },
  { key: "completions",   label: "Well Completions",       IconComp: Icon.Layers,    tier3Extra: ["comp_method", "comp_rate", "comp_rate_unit", "comp_duration", "comp_flare_eff", "ch4_content", "co2_content"] },
  { key: "unloading",     label: "Liquids Unloading",      IconComp: Icon.Layers,    tier3Extra: ["unload_depth", "unload_diam", "unload_press", "unload_freq", "unload_flare_eff", "ch4_content", "co2_content"] },
  { key: "drilling",      label: "Drilling",               IconComp: Icon.Layers,    tier3Extra: ["mud_type"] },
  { key: "dehydrator",    label: "Dehydrators",            IconComp: Icon.Droplets,  tier3Extra: ["vent_method", "ch4_content", "co2_content"] },
  { key: "agr",           label: "AGR / Acid Gas Removal", IconComp: Icon.Activity,  tier3Extra: ["agr_co2_in", "agr_co2_out", "agr_ch4_in", "agr_ch4_slip", "agr_control_eff"] },
];

// ─── ALL field definitions with grouping + tooltips ────────────────────────
const FIELD_GROUPS = [
  {
    id: "identity",
    label: "Location & Identity",
    IconComp: Icon.Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM (or map Year and Month)" },
      { key: "facility_name", label: "Facility", required: true, hint: "Facility name exactly as in Manage Data" },
      { key: "activity",      label: "Activity",       required: false, hint: "e.g. Exploration & Production" },
      { key: "division",      label: "Division",       required: false, hint: "e.g. Production, Association" },
      { key: "field",         label: "Field",          required: false, hint: "e.g. Bir Berkine" },
      { key: "group",         label: "Group",          required: false, hint: "Free grouping label stored with the record (e.g. West facility)" },
      { key: "equipment",     label: "Equipment Name", required: false, hint: "Name of the piece of equipment" },
      { key: "equipment_id",  label: "Equipment ID",   required: false, hint: "Unique identifier for the equipment (duplicate check)" },
    ],
  },
  {
    id: "measurement",
    label: "Measurement",
    IconComp: Icon.Activity,
    fields: [
      { key: "process",       label: "Process Type",  required: true,  hint: "e.g. combustion, flaring, venting (keys or the form's names)" },
      { key: "fuel",          label: "Activity / Fuel", required: false, hint: "Emission factor name as listed in the manual form (default and custom rows)" },
      { key: "quantity",      label: "Quantity",      required: true,  hint: "Activity of the month" },
      { key: "unit",          label: "Unit",          required: true,  hint: "e.g. scf, Mscf, m3, bbl, gal, tonne, days, devices" },
      { key: "factor_type",   label: "Factor Type",   required: false, hint: "default (API Compendium) | custom (saved factor) | specific (Tier 3)" },
      { key: "operating_hours", label: "Operating Hours", required: false, hint: "Hours in the month: required for pneumatic controller factors and equipment leaks" },
      { key: "year",          label: "Year",          required: true,  hint: "4-digit year (e.g. 2024) — required unless using a date column" },
      { key: "month",         label: "Month",         required: true,  hint: "1–12 — required unless using a date column (YYYY-MM)" },
    ],
  },
  {
    id: "gas_composition",
    label: "Gas Composition (Tier 3)",
    IconComp: Icon.Settings,
    tier3Only: true,
    fields: [
      { key: "c1",      label: "C1 (Methane) mol%",  required: false, hint: "Methane mole %" },
      { key: "c2",      label: "C2 (Ethane) mol%",   required: false, hint: "Ethane mole %" },
      { key: "c3",      label: "C3 (Propane) mol%",  required: false, hint: "Propane mole %" },
      { key: "c4",      label: "C4 mol%",            required: false, hint: "Butane mole %" },
      { key: "c5",      label: "C5 mol%",            required: false, hint: "Pentane mole %" },
      { key: "c6",      label: "C6 mol%",            required: false, hint: "Hexane mole %" },
      { key: "c7",      label: "C7 mol%",            required: false, hint: "" },
      { key: "c8",      label: "C8 mol%",            required: false, hint: "" },
      { key: "c9",      label: "C9 mol%",            required: false, hint: "" },
      { key: "c10",     label: "C10+ mol%",          required: false, hint: "" },
      { key: "co2_mol", label: "CO₂ mol%",           required: false, hint: "CO2 mole % of the gas" },
      { key: "n2_mol",  label: "N₂ mol%",            required: false, hint: "Nitrogen mole %" },
      { key: "hhv",     label: "HHV",               required: false, hint: "Higher heating value (Btu/scf for gas)" },
      { key: "ch4_content", label: "CH4 Content %",  required: false, hint: "CH4 mole % when the full composition is not given" },
      { key: "co2_content", label: "CO2 Content %",  required: false, hint: "CO2 mole % when the full composition is not given" },
    ],
  },
  {
    id: "combustion_params",
    label: "Combustion / Flaring Parameters (Tier 3)",
    IconComp: Icon.Flame,
    tier3Only: true,
    fields: [
      { key: "combustion_efficiency", label: "Combustion Efficiency %", required: false, hint: "Combustion: required at Tier 3. Flaring: % carbon to CO2, blank = 98" },
      { key: "flare_type",           label: "Flare Type",             required: false, hint: "elevated | enclosed_ground | air_assisted | steam_assisted" },
      { key: "destruction_efficiency", label: "Flare Destruction Efficiency %", required: false, hint: "Flaring: % of CH4 destroyed. Blank = 98 (99.5 enclosed)" },
      { key: "control_efficiency",   label: "Flare Control Efficiency %", required: false, hint: "One flare efficiency for both carbon conversion and CH4 destruction" },
      { key: "operating_temperature",label: "Metering Temp",          required: false, hint: "Only for volumes in m3 / cf read at metering conditions" },
      { key: "temp_unit",            label: "Temp Unit",              required: false, hint: "C or F" },
      { key: "operating_pressure",   label: "Metering Pressure",      required: false, hint: "Only for volumes in m3 / cf read at metering conditions" },
      { key: "press_unit",           label: "Press Unit",             required: false, hint: "psig, psia, kPa, barg, bara" },
      { key: "z_factor",             label: "Z Factor",               required: false, hint: "Gas compressibility factor" },
    ],
  },
  {
    id: "vent_params",
    label: "Venting / Dehydrator / Blowdown (Tier 3)",
    IconComp: Icon.Wind,
    tier3Only: true,
    fields: [
      { key: "vent_method",         label: "Vent Method",          required: false, hint: "volume: the quantity is the measured gas volume (scf, Mcf, MMscf, m3)" },
      { key: "disposition",         label: "Disposition",          required: false, hint: "vented (default) or flared" },
      { key: "blowdown_pressure",   label: "Blowdown Pressure",    required: false, hint: "Vessel pressure before blowdown" },
      { key: "blowdown_events",     label: "Blowdown Events",      required: false, hint: "Events in the month" },
      { key: "blowdown_temp",       label: "Blowdown Temp",        required: false, hint: "Gas temperature in the vessel" },
      { key: "blowdown_temp_unit",  label: "Blowdown Temp Unit",   required: false, hint: "F | C | K" },
      { key: "blowdown_press_unit", label: "Blowdown Press Unit",  required: false, hint: "psig | psia | kPa" },
    ],
  },
  {
    id: "pneumatic_params",
    label: "Pneumatic Parameters (Tier 3)",
    IconComp: Icon.Cpu,
    tier3Only: true,
    fields: [
      { key: "pneu_count",       label: "Pneumatic Count",      required: false, hint: "Number of devices" },
      { key: "pneu_bleed_rate",  label: "Bleed Rate",           required: false, hint: "Measured bleed rate per device" },
      { key: "pneu_bleed_unit",  label: "Bleed Rate Unit",      required: false, hint: "scf or m3 (per hour)" },
      { key: "pneu_hours",       label: "Pneumatic Hours",      required: false, hint: "Operating hours in the month" },
      { key: "pneu_ch4_content", label: "Supply Gas CH4 %",     required: false, hint: "CH4 mole % of the supply gas" },
    ],
  },
  {
    id: "tank_params",
    label: "Tank Parameters (Tier 3)",
    IconComp: Icon.Container,
    tier3Only: true,
    fields: [
      { key: "tank_gor",            label: "Tank GOR",             required: false, hint: "Flash gas-to-oil ratio (scf/bbl)" },
      { key: "tank_ch4_content",    label: "Tank CH4 Content %",   required: false, hint: "CH4 mole % of the flash gas" },
      { key: "tank_control_eff",    label: "Tank Control Eff %",   required: false, hint: "Vapour control efficiency" },
      { key: "tank_api_gravity",    label: "Tank API Gravity",     required: false, hint: "API gravity of the stored liquid" },
    ],
  },
  {
    id: "fugitive_params",
    label: "Equipment Leak Parameters (Tier 3)",
    IconComp: Icon.Wind,
    tier3Only: true,
    fields: [
      { key: "fugitive_method", label: "Leak Method",       required: false, hint: "screening | correlation | ogi | measurement" },
      { key: "component_type",  label: "Component Type",    required: false, hint: "valve | connector | flange | open_ended_line | pump_seal | other" },
      { key: "service",         label: "Service",           required: false, hint: "gas | light_oil | heavy_oil | water_oil" },
      { key: "m21_below_count", label: "Screened < 10,000 ppmv", required: false, hint: "Components screened below 10,000 ppmv" },
      { key: "m21_above_count", label: "Screened ≥ 10,000 ppmv", required: false, hint: "Components screened at or above 10,000 ppmv" },
    ],
  },
  {
    id: "well_params",
    label: "Well / Drilling Parameters (Tier 3)",
    IconComp: Icon.Layers,
    tier3Only: true,
    fields: [
      { key: "mud_type",          label: "Mud Type",           required: false, hint: "water_based | oil_based | synthetic (quantity in drilling days)" },
      { key: "comp_method",       label: "Completion Method",  required: false, hint: "metered_volume | rate_duration | gor_liquid" },
      { key: "comp_rate",         label: "Flowback Rate",      required: false, hint: "Gas rate during flowback" },
      { key: "comp_rate_unit",    label: "Flowback Rate Unit", required: false, hint: "Mcf/hr (default) | Mcf/day | scf/hr | m3/hr" },
      { key: "comp_duration",     label: "Flowback Duration",  required: false, hint: "Hours" },
      { key: "comp_flare_eff",    label: "Completion Flare %", required: false, hint: "% of flowback gas flared" },
      { key: "unload_depth",      label: "Well Depth (ft)",    required: false, hint: "Liquids unloading" },
      { key: "unload_diam",       label: "Casing Diameter (in)", required: false, hint: "Liquids unloading" },
      { key: "unload_press",      label: "Shut-in Pressure (psig)", required: false, hint: "Liquids unloading" },
      { key: "unload_freq",       label: "Unloading Events",   required: false, hint: "Events in the month" },
      { key: "unload_flare_eff",  label: "Unloading Flare %",  required: false, hint: "% of unloading gas flared" },
    ],
  },
  {
    id: "dehydrator_agr",
    label: "AGR Parameters (Tier 3)",
    IconComp: Icon.Droplets,
    tier3Only: true,
    fields: [
      { key: "agr_co2_in",        label: "AGR CO₂ In %",       required: false, hint: "CO2 mole % in the feed" },
      { key: "agr_co2_out",       label: "AGR CO₂ Out %",      required: false, hint: "CO2 mole % in the sweet gas" },
      { key: "agr_ch4_in",        label: "AGR CH₄ In %",       required: false, hint: "CH4 mole % in the feed" },
      { key: "agr_ch4_slip",      label: "AGR CH₄ Slip",       required: false, hint: "Fraction of inlet CH4 (e.g. 0.001)" },
      { key: "agr_control_eff",   label: "AGR Control Eff %",  required: false, hint: "Acid gas destruction efficiency" },
    ],
  },
  {
    id: "uncertainty",
    label: "Uncertainty Overrides",
    IconComp: Icon.Settings,
    fields: [
      { key: "user_unc_co2", label: "User Uncertainty CO₂ %", required: false, hint: "Override the system uncertainty for CO2" },
      { key: "user_unc_ch4", label: "User Uncertainty CH₄ %", required: false, hint: "Override the system uncertainty for CH4" },
      { key: "user_unc_n2o", label: "User Uncertainty N₂O %", required: false, hint: "Override the system uncertainty for N2O" },
    ],
  },
];

// ─── Step definitions ────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: "Calculation",   IconComp: Icon.Settings  },
  { id: 3, label: "Choose File",   IconComp: Icon.Upload    },
  { id: 4, label: "Check & Map",   IconComp: Icon.Columns   },
  { id: 5, label: "Import",        IconComp: Icon.Processing },
];
// the tier chosen in step 1 is the one the server applies (it used to be a second, independent
// "Default factor" select in the mapping step: choosing Tier 3 in step 1 still imported per row)
const TIER_TO_FACTOR = { "1": "default", "2": "custom", "3": "specific", auto: "auto" };
const TIER_LABEL = { "1": "Tier 1 for every row", "2": "Tier 2 for every row", "3": "Tier 3 for every row",
  auto: "Tier per row (factor_type column)" };

// ─── Step Indicator ───────────────────────────────────────────────────────────
function StepBar({ current }) {
  return (
    <div className="s1w-stepbar">
      {STEPS.map((s, i) => {
        const done   = s.id < current;
        const active = s.id === current;
        const SIcon  = s.IconComp;
        return (
          <React.Fragment key={s.id}>
            <div className={`s1w-step ${active ? "active" : ""} ${done ? "done" : ""}`}>
              <div className="s1w-step-circle">
                {done ? <Icon.Check /> : <SIcon />}
              </div>
              <span className="s1w-step-label">{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`s1w-step-line ${done ? "done" : ""}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Tier Mode Card ───────────────────────────────────────────────────────────
// eslint-disable-next-line no-unused-vars -- IcoComp is rendered as <IcoComp />
function ModeCard({ selected, onClick, Icon: IcoComp, title, badge, description }) {
  return (
    <button className={`s1w-mode-card ${selected ? "selected" : ""}`} onClick={onClick}>
      <div className="s1w-mode-card-header">
        <div className="s1w-mode-card-icon"><IcoComp /></div>
        <span className="s1w-mode-card-title">{title}</span>
        {badge && <span className={`s1w-mode-badge s1w-mode-badge--${badge.color}`}>{badge.label}</span>}
        <div className={`s1w-radio ${selected ? "checked" : ""}`} />
      </div>
      <p className="s1w-mode-card-desc">{description}</p>
    </button>
  );
}

// ─── Process Tile ─────────────────────────────────────────────────────────────
function ProcessTile({ process, selected, onClick }) {
  const IcoComp = process.IconComp;
  return (
    <button className={`s1w-process-tile ${selected ? "selected" : ""}`} onClick={onClick}>
      <div className="s1w-process-tile-icon"><IcoComp /></div>
      <span className="s1w-process-tile-label">{process.label}</span>
      {selected && <div className="s1w-process-tile-check"><Icon.Check /></div>}
    </button>
  );
}

// ─── Mapping Row ──────────────────────────────────────────────────────────────
function MappingRow({ field, headers, value, onChange }) {
  const mapped = !!value;
  return (
    <div className={`s1w-map-row ${!mapped && field.required ? "s1w-map-row--missing" : ""} ${mapped ? "s1w-map-row--mapped" : ""}`}>
      <div className="s1w-map-field">
        <span className="s1w-map-field-label">
          {field.label}
          {field.required && <span className="s1w-required-dot" />}
        </span>
        {field.hint && <span className="s1w-map-field-hint">{field.hint}</span>}
      </div>
      <div className="s1w-map-select-wrap">
        {headers.length > 0 ? (
          <select className={`s1w-map-select ${mapped ? "matched" : ""}`} value={value} onChange={e => onChange(e.target.value)}>
            <option value="">— Not mapped —</option>
            {headers.map(h => <option key={h} value={h}>{h}</option>)}
          </select>
        ) : (
          <input className={`s1w-map-input ${mapped ? "matched" : ""}`} placeholder="Column name in your file" value={value} onChange={e => onChange(e.target.value)} />
        )}
      </div>
      <div className="s1w-map-status">
        {mapped
          ? <span className="s1w-status-ok"><Icon.Check /></span>
          : <span className="s1w-status-empty" />}
      </div>
    </div>
  );
}

// ─── Field Group Panel ────────────────────────────────────────────────────────
function FieldGroup({ group, headers, mapping, setMapping, searchQuery, tier, processScope, selectedProcesses, showAll, essentialKeys }) {
  const [open, setOpen] = useState(true);

  // Filter fields by search
  const visibleFields = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return group.fields.filter(f => {
      if (q && !f.label.toLowerCase().includes(q) && !f.key.toLowerCase().includes(q) && !f.hint.toLowerCase().includes(q)) return false;
      // default view: only the fields that matter for this file (mapped, or required and missing)
      if (!q && !showAll && !essentialKeys.has(f.key)) return false;
      // Hide tier3 groups entirely if tier is 1
      if (group.tier3Only && (tier === "1" || tier === "2")) return false;
      // For specific process scope, hide tier3 params that don't belong to any selected process
      if (group.tier3Only && processScope === "specific") {
        const relevantKeys = new Set(
          selectedProcesses.flatMap(pk => {
            const proc = PROCESS_CATALOGUE.find(p => p.key === pk);
            return proc ? proc.tier3Extra : [];
          })
        );
        if (!relevantKeys.has(f.key)) return false;
      }
      return true;
    });
  }, [group.fields, searchQuery, tier, processScope, selectedProcesses, group.tier3Only, showAll, essentialKeys]);

  if (visibleFields.length === 0) return null;

  const GroupIcon = group.IconComp;
  const mappedCount = visibleFields.filter(f => mapping[f.key]).length;

  return (
    <div className="s1w-field-group">
      <button className="s1w-group-header" onClick={() => setOpen(v => !v)}>
        <div className="s1w-group-header-left">
          <div className="s1w-group-icon"><GroupIcon /></div>
          <span className="s1w-group-label">{group.label}</span>
          {group.tier3Only && tier === "auto" && (
            <span className="s1w-group-badge s1w-group-badge--tier3">Tier 3</span>
          )}
        </div>
        <div className="s1w-group-header-right">
          <span className="s1w-group-count">{mappedCount}/{visibleFields.length} mapped</span>
          <Icon.ChevronDown open={open} />
        </div>
      </button>
      {open && (
        <div className="s1w-group-body">
          <div className="s1w-group-table-header">
            <span>Field</span>
            <span>Your CSV Column</span>
            <span>Status</span>
          </div>
          {visibleFields.map(field => (
            <MappingRow
              key={field.key}
              field={field}
              headers={headers}
              value={mapping[field.key] || ""}
              onChange={val => setMapping(m => ({ ...m, [field.key]: val }))}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── File check summary ───────────────────────────────────────────────────────
const fmt = (n) => Number(n || 0).toLocaleString("en-US");

function FileCheckPanel({ check, onRecheck, canRun }) {
  if (check.loading) {
    return (
      <div className="s1w-check s1w-check--loading" role="status">
        <span className="s1w-spinner" /> Checking your file… a sample of rows spread over the file is calculated exactly as
        the import would; nothing is saved.
      </div>
    );
  }
  if (check.error) {
    return (
      <div className="s1w-check s1w-check--error" role="alert">
        <strong>The file could not be checked:</strong> {check.error}{" "}
        <button className="s1w-link-btn" onClick={onRecheck}>Check again</button>
      </div>
    );
  }
  if (!check.data) {
    return canRun ? (
      <div className="s1w-check">
        <button className="s1w-link-btn" onClick={onRecheck}>Check the file</button> before importing (nothing is saved).
      </div>
    ) : (
      <div className="s1w-check">Map the required fields below; the file is then checked before anything is saved.</div>
    );
  }
  const p = check.data.preview;
  const groups = check.data.skipped_groups || [];
  const scale = p.checked ? p.rows / p.checked : 1;
  const unknownFac = (p.facilities || []).filter(f => !f.known);
  const unknownProc = (p.processes || []).filter(x => !x.known && !x.scope2);
  const scope2Proc = (p.processes || []).filter(x => x.scope2);
  return (
    <div className="s1w-check">
      {check.stale && (
        <div className="s1w-check-stale">
          Options or mapping changed since this check. <button className="s1w-link-btn" onClick={onRecheck}>Check again</button>
        </div>
      )}
      <div className="s1w-check-title">File check</div>
      <div className="s1w-check-facts">
        {fmt(p.rows)} rows
        {p.period?.from && <> · {p.period.from} to {p.period.to} ({p.period.months} month{p.period.months !== 1 ? "s" : ""})</>}
        {" "}· {fmt((p.facilities || []).length)} facilit{(p.facilities || []).length !== 1 ? "ies" : "y"}
        {" "}· {fmt((p.processes || []).length)} process type{(p.processes || []).length !== 1 ? "s" : ""}
      </div>
      <div className="s1w-check-totals">
        <div className="s1w-check-total s1w-check-total--ok">
          <span>{p.is_estimate ? "≈ " : ""}{fmt(p.estimated_ok)}</span> rows will be imported
        </div>
        <div className={`s1w-check-total ${p.estimated_skipped ? "s1w-check-total--warn" : ""}`}>
          <span>{p.is_estimate ? "≈ " : ""}{fmt(p.estimated_skipped)}</span> rows will be skipped
        </div>
      </div>
      {p.is_estimate && (
        <div className="s1w-check-note">Estimated from {fmt(p.checked)} rows spread over the file; the import checks every row.</div>
      )}
      {unknownFac.length > 0 && (
        <div className="s1w-check-warn">
          <strong>{fmt(p.unknown_facility_rows)} rows name a facility that is not in the platform or not in your regions:</strong>{" "}
          {unknownFac.slice(0, 5).map(f => `${f.name} (${fmt(f.rows)})`).join(", ")}{unknownFac.length > 5 ? " …" : ""}
        </div>
      )}
      {unknownProc.length > 0 && (
        <div className="s1w-check-warn">
          <strong>{fmt(p.unknown_process_rows)} rows have a process type that is not recognised:</strong>{" "}
          {unknownProc.slice(0, 5).map(x => `${x.name} (${fmt(x.rows)})`).join(", ")}{unknownProc.length > 5 ? " …" : ""}
        </div>
      )}
      {scope2Proc.length > 0 && (
        <div className="s1w-check-warn">
          <strong>{fmt(p.scope2_rows)} rows are Scope 2 (purchased energy):</strong>{" "}
          {scope2Proc.slice(0, 5).map(x => `${x.name} (${fmt(x.rows)})`).join(", ")}. Import them with the Scope 2 template.
        </div>
      )}
      {p.example_rows > 0 && (
        <div className="s1w-check-warn">
          <strong>{fmt(p.example_rows)} example rows from the template</strong> (dated EXAMPLE) will not be imported.
          Delete them, or replace EXAMPLE with the real month to keep a row.
        </div>
      )}
      {p.period?.unreadable_rows > 0 && (
        <div className="s1w-check-warn"><strong>{fmt(p.period.unreadable_rows)} rows have a missing or unreadable date.</strong></div>
      )}
      {groups.length > 0 && (
        <>
          <div className="s1w-check-subtitle">Why rows would be skipped{p.is_estimate ? " (scaled from the sample)" : ""}</div>
          <SkipGroupList groups={groups} scale={scale} approx={p.is_estimate} limit={6} />
        </>
      )}
      {p.columns && (
        <div className="s1w-check-note">
          {p.columns.matched.length} of {p.columns.total} columns are matched to fields.
          {p.columns.by_name.length > 0 && <> The other {p.columns.by_name.length} are read by their name when a calculation
          needs them (for example c1, gor, hhv) and ignored otherwise.</>}
        </div>
      )}
    </div>
  );
}

// ─── Auto-detect mapping ───────────────────────────────────────────────────────
// ─── Main Wizard ──────────────────────────────────────────────────────────────
export default function Scope1ImportWizard({ onClose, onUploadSuccess }) {
  const toast = useToast();
  const fileInputRef = useRef(null);

  const [step, setStep] = useState(1);
  const [tier, setTier] = useState("auto");         // "1" | "3" | "auto"
  const [processScope, setProcessScope] = useState("all");  // "all" | "specific"
  const [selectedProcesses, setSelectedProcesses] = useState([]);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [parseError, setParseError] = useState("");
  const [headers, setHeaders] = useState([]);
  const [mapping, setMapping] = useState({});
  const globalFactor = TIER_TO_FACTOR[tier] || "auto";
  const [showAllFields, setShowAllFields] = useState(false);
  const [maxBytes, setMaxBytes] = useState(null);       // server upload limit, checked when a file is picked
  const [check, setCheck] = useState({ loading: false, data: null, error: "", stale: false });
  const [searchQuery, setSearchQuery] = useState("");
  const [jobId, setJobId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // a refused upload (e.g. over the server's size limit) stays visible in the wizard; the toast lasts 3 s
  const [submitError, setSubmitError] = useState("");
  const [overwrite, setOverwrite] = useState(false);  // replace records that already exist
  const [savedMappings, setSavedMappings] = useState([]);   // the user's saved column mappings (Scope 1)
  const [appliedSaved, setAppliedSaved] = useState(null);   // the saved mapping the file opened with
  const [saveName, setSaveName] = useState(null);           // null = save form closed
  const [optionalCols, setOptionalCols] = useState(false);  // template: include the optional columns

  // ── Access Control: fetch allowed regions on mount ─────────────────────────
  const [allowedRegions, setAllowedRegions] = useState(null);  // null = loading, [] = restricted with no regions
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    api.get("/facilities/").then(res => {
      const regions = res.data.map(f => f.name);
      // If user gets all facilities back (admin), flag as admin; else show their list
      setAllowedRegions(regions);
      // Detect admin: if role is surfaced in a /me endpoint, use that;
      // we use a heuristic: if the API returned more than 0 regions, it worked.
      // The actual all-or-restricted logic lives server-side.
    }).catch(() => setAllowedRegions([]));

    // Also check user role from /api/auth/me or similar
    api.get("/auth/me").then(res => {
      const role = res.data?.role;
      setIsAdmin(role === "admin" ||
        (role === "superuser" && res.data?.location === "all"));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    api.get("/emissions/upload/mappings", { params: { scope: "1" } })
      .then(res => setSavedMappings(Array.isArray(res.data) ? res.data : []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api.get("/emissions/upload/limits").then(res => setMaxBytes(res.data?.max_bytes || null)).catch(() => {});
  }, []);

  // Toggle process selection
  const toggleProcess = (key) => {
    setSelectedProcesses(prev =>
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  // All fields flattened (for auto-detect)
  const allFields = useMemo(() =>
    FIELD_GROUPS.flatMap(g => g.fields),
  []);

  // Required fields check
  const missingRequired = missingRequiredFields(FIELD_GROUPS.flatMap(g => g.fields), mapping);
  const canSubmit = missingRequired.length === 0 || headers.length === 0;
  const essentialKeys = useMemo(() => new Set([
    "fuel",   // optional only for Tier 3 methods: always offered in the short list
    ...Object.keys(mapping).filter(k => mapping[k]),
    ...missingRequired.map(f => f.key),
  ]), [mapping, missingRequired]);
  const matchedColumns = useMemo(() => new Set(Object.values(mapping).filter(Boolean)), [mapping]);

  // File processing
  const processFile = useCallback((f) => {
    if (!f) return;
    setParseError("");
    setSubmitError("");
    setCheck({ loading: false, data: null, error: "", stale: false });
    if (maxBytes && f.size > maxBytes) {
      // refused before uploading anything (it used to fail only after the upload, with a 3 s toast)
      setParseError(`This file is ${(f.size / 1048576).toFixed(1)} MB; the upload limit is ${(maxBytes / 1048576).toFixed(0)} MB. Split it into smaller files.`);
      return;
    }
    const isExcel = f.name.toLowerCase().endsWith(".xlsx");
    if (isExcel) {
      // the column names of an Excel file come back with the first check (the browser does not read .xlsx)
      setFile(f); setHeaders([]); setMapping({}); setAppliedSaved(null); setStep(4);
      return;
    }
    Papa.parse(f, {
      preview: 5, header: true, skipEmptyLines: true,
      complete: (results) => {
        if (!results.meta.fields?.length) {
          setParseError("Could not read column headers. Make sure the file has a header row.");
          return;
        }
        const hdrs = results.meta.fields;
        const { mapping: m, applied } = withSavedMapping(autoDetectMapping(hdrs, allFields), savedMappings, hdrs);
        setHeaders(hdrs);
        setMapping(m);
        setAppliedSaved(applied);
        setFile(f);
        setStep(4);
      },
      error: () => setParseError("Failed to parse file. Please ensure it is a valid CSV."),
    });
  }, [allFields, maxBytes, savedMappings]);

  const onDrop = (e) => { e.preventDefault(); setIsDragging(false); processFile(e.dataTransfer.files[0]); };
  const onFileChange = (e) => { processFile(e.target.files[0]); e.target.value = ""; };

  // Template download
  const downloadTemplate = async (fmt) => {
    try {
      const processParam = selectedProcesses.length ? selectedProcesses.join(",") : "all";
      const res = await api.get(
        `/emissions/template/${fmt}?tier=${tier}&process=${processParam}${optionalCols ? "&optional=1" : ""}`,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      const stem = `scope1_template_${tier === "auto" ? "per_row" : `tier${tier}`}`;
      a.download = fmt === "excel" ? `${stem}.xlsx` : `${stem}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
    } catch { toast.error("Template download failed."); }
  };

  // Check file: the server calculates a sample spread over the file and counts every row; nothing is saved
  const runCheck = useCallback(async () => {
    if (!file) return;
    setCheck({ loading: true, data: null, error: "", stale: false });
    const form = new FormData();
    form.append("file", file);
    form.append("global_factor_type", globalFactor);
    form.append("scope", "1");
    form.append("overwrite_duplicates", overwrite ? "true" : "false");
    form.append("column_mapping", JSON.stringify(mapping));
    form.append("sample_rows", "2000");
    try {
      const res = await api.post("/emissions/upload/check", form, { headers: { "Content-Type": "multipart/form-data" } });
      setCheck({ loading: false, data: res.data, error: "", stale: false });
      const xlHeaders = res.data?.preview?.columns?.headers;
      if (headers.length === 0 && Array.isArray(xlHeaders) && xlHeaders.length) {
        // Excel: show the mapping now that the column names are known; a saved mapping that fits is applied
        // and the file checked again with it
        const { mapping: m, applied } = withSavedMapping(autoDetectMapping(xlHeaders, allFields), savedMappings, xlHeaders);
        skipStaleRef.current = !applied;
        setHeaders(xlHeaders);
        setMapping(m);
        setAppliedSaved(applied);
        if (applied) setRecheck(true);
      }
    } catch (err) {
      setCheck({ loading: false, data: null, error: err.response?.data?.error || err.message, stale: false });
    }
  }, [file, globalFactor, overwrite, mapping, headers.length, allFields, savedMappings]);

  // first check when the mapping step opens; later changes only mark the result out of date
  const checkedFileRef = useRef(null);
  useEffect(() => {
    if (step === 4 && file && checkedFileRef.current !== file && (headers.length === 0 || canSubmit)) {
      checkedFileRef.current = file;
      runCheck();
    }
  }, [step, file, headers.length, canSubmit, runCheck]);
  const firstRender = useRef(true);
  const skipStaleRef = useRef(false);   // the mapping set from the check's own column names
  useEffect(() => {
    if (firstRender.current) { firstRender.current = false; return; }
    if (skipStaleRef.current) { skipStaleRef.current = false; return; }
    setCheck(c => (c.data || c.error ? { ...c, stale: true } : c));
  }, [mapping, tier, overwrite]);
  const [recheck, setRecheck] = useState(false);
  useEffect(() => {
    if (recheck) { setRecheck(false); runCheck(); }
  }, [recheck, runCheck]);

  // ── Saved mappings ──
  const fitting = useMemo(() => fittingMappings(savedMappings, headers), [savedMappings, headers]);
  const applySaved = (m) => {
    setMapping(m ? { ...autoDetectMapping(headers, allFields), ...m.mapping } : autoDetectMapping(headers, allFields));
    setAppliedSaved(m);
  };
  const saveMapping = async () => {
    const name = (saveName || "").trim();
    if (!name) return;
    try {
      const res = await api.post("/emissions/upload/mappings", { scope: "1", name, headers, mapping });
      setSavedMappings(list => [res.data, ...list.filter(x => x.id !== res.data.id)]);
      setAppliedSaved(res.data);
      setSaveName(null);
      toast.success(`Mapping "${name}" saved: it will be applied to files with these columns.`);
    } catch (err) {
      toast.error(err.response?.data?.error || "The mapping could not be saved.");
    }
  };

  // Submit
  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError("");
    const form = new FormData();
    form.append("file", file);
    form.append("global_factor_type", globalFactor);
    form.append("scope", "1");
    form.append("overwrite_duplicates", overwrite ? "true" : "false");
    form.append("column_mapping", JSON.stringify(mapping));
    try {
      const res = await api.post("/emissions/upload/start", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setJobId(res.data.job_id);
      if (appliedSaved) api.post(`/emissions/upload/mappings/${appliedSaved.id}/used`).catch(() => {});
      setStep(5);
    } catch (err) {
      const msg = err.response?.data?.error
        || (err.response?.status === 413 ? "The file is larger than the server's upload limit; split it into smaller files." : err.message);
      setSubmitError(msg);
      toast.error("Upload error: " + msg);
    } finally { setIsSubmitting(false); }
  };

  const canGoNext = () => true;

  return (
    <div className="s1w-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="s1w-modal">
        {/* Header */}
        <div className="s1w-header">
          <div className="s1w-header-left">
            <div className="s1w-header-icon"><Icon.Activity /></div>
            <div>
              <h2 className="s1w-title">Scope 1 Bulk Import</h2>
              <p className="s1w-subtitle">Upload emissions data from CSV or Excel</p>
            </div>
          </div>
          <button className="s1w-close" onClick={onClose}><Icon.Close /></button>
        </div>

        {/* Step bar */}
        <StepBar current={step} />

        {/* ── STEP 1: Upload Mode ── */}
        {step === 1 && (
          <div className="s1w-body">
            <div className="s1w-section-title">
              <Icon.Settings />
              <span>Select Calculation Tier</span>
            </div>
            <p className="s1w-section-desc">
              Choose how emissions will be calculated for each row in your file.
            </p>
            <div className="s1w-mode-grid">
              <ModeCard
                selected={tier === "1"}
                onClick={() => setTier("1")}
                Icon={Icon.Zap}
                title="Tier 1 — Standard"
                badge={{ label: "Minimum fields", color: "blue" }}
                description="Every row uses the API Compendium default factors (the file's factor_type column is ignored). Needs fuel, quantity and unit."
              />
              <ModeCard
                selected={tier === "2"}
                onClick={() => setTier("2")}
                Icon={Icon.Layers}
                title="Tier 2 — Custom / Site Factors"
                badge={{ label: "Site data", color: "blue" }}
                description="Every row uses your saved custom factors (Manage Data › Custom Factors), or a catalog fuel with your measured HHV / density."
              />
              <ModeCard
                selected={tier === "3"}
                onClick={() => setTier("3")}
                Icon={Icon.Settings}
                title="Tier 3 — Engineering"
                badge={{ label: "Full precision", color: "green" }}
                description="Every row is calculated from site data: gas composition (C1–C10), operating conditions and process parameters."
              />
              <ModeCard
                selected={tier === "auto"}
                onClick={() => setTier("auto")}
                Icon={Icon.Wand}
                title="Per row — mixed tiers"
                badge={{ label: "Recommended", color: "orange" }}
                description="Mixes Tier 1, 2 and 3 rows in one file. Each row's factor_type column (default / custom / specific) selects its tier."
              />
            </div>
            <div className="s1w-info-banner">
              <Icon.Info />
              <span>
                {tier === "1" && "Tier 1 only requires: Region, Date, Process, Fuel, Quantity, Unit."}
                {tier === "2" && "Tier 2 requires the Tier 1 fields with factor_type custom and either a saved custom factor name in Fuel, or a catalog fuel with hhv (and hhv_unit) / density."}
                {tier === "3" && "Tier 3 requires all Tier 1 fields plus gas composition and process engineering parameters."}
                {tier === "auto" && "Auto-detect is ideal for a mix of sources: each row's factor_type column selects Tier 1, 2 or 3."}
              </span>
            </div>
          </div>
        )}

        {/* ── STEP 3: File Upload ── */}
        {step === 3 && (
          <div className="s1w-body">
            <div className="s1w-section-title"><Icon.Upload /><span>Select File</span></div>

            {/* ── Region access banner ── */}
            {!isAdmin && allowedRegions !== null && (
              <div className="s1w-access-banner">
                <div className="s1w-access-banner-header">
                  <Icon.Info />
                  <strong>Your upload is restricted to the following regions:</strong>
                </div>
                {allowedRegions.length > 0 ? (
                  <div className="s1w-access-region-list">
                    {allowedRegions.map(r => (
                      <span key={r} className="s1w-access-region-pill">{r}</span>
                    ))}
                  </div>
                ) : (
                  <p className="s1w-access-no-regions">
                    Your account has no assigned regions. Contact an administrator before uploading.
                  </p>
                )}
              </div>
            )}
            <div
              className={`s1w-dropzone ${isDragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={onDrop}
            >
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx" style={{ display: "none" }} onChange={onFileChange} />
              <div className="s1w-dropzone-icon"><Icon.Upload /></div>
              <p className="s1w-dropzone-text">Drag & drop your file here, or <span>click to browse</span></p>
              <p className="s1w-dropzone-sub">.xlsx or .csv{maxBytes ? ` · up to ${(maxBytes / 1048576).toFixed(0)} MB` : ""} · the file is checked before anything is saved</p>
              {parseError && (
                <div className="s1w-inline-error"><Icon.Warning />{parseError}</div>
              )}
            </div>

            <div className="s1w-template-section">
              <p className="s1w-template-label">Don't have a file? Download a template made for {TIER_LABEL[tier]}:</p>
              {(tier === "3" || tier === "auto") && (
                <div className="s1w-template-procs">
                  <span className="s1w-template-sub">Add the Tier 3 input columns for{selectedProcesses.length ? "" : " every process"}:</span>
                  <div className="s1w-template-chips">
                    {PROCESS_CATALOGUE.map(p => (
                      <button key={p.key} type="button"
                        className={`s1w-chip ${selectedProcesses.includes(p.key) ? "s1w-chip--on" : ""}`}
                        aria-pressed={selectedProcesses.includes(p.key)} onClick={() => toggleProcess(p.key)}>
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <label className="s1w-template-opt">
                <input type="checkbox" checked={optionalCols} onChange={e => setOptionalCols(e.target.checked)} />
                <span>Include optional columns (activity, division, field, metering conditions, uncertainty)</span>
              </label>
              <div className="s1w-template-btns">
                <button className="s1w-template-btn s1w-template-btn--primary" onClick={() => downloadTemplate("excel")}>
                  <span className="s1w-template-btn-icon"><Icon.FileExcel /></span>
                  <span>
                    <strong>Excel template <em className="s1w-reco">Recommended</em></strong>
                    <small>Dropdowns for your facilities, processes, and the fuels and units of each process; examples and a reference sheet</small>
                  </span>
                </button>
                <button className="s1w-template-btn" onClick={() => downloadTemplate("csv")}>
                  <span className="s1w-template-btn-icon"><Icon.File /></span>
                  <span>
                    <strong>CSV template</strong>
                    <small>Same columns, for exports from other systems. Example rows dated EXAMPLE are never imported.</small>
                  </span>
                </button>
              </div>
              <p className="s1w-template-note">Have an export from another system? Upload it as it is: you match its columns once and can save that mapping for the next file.</p>
            </div>

            {/* Config summary pill */}
            <div className="s1w-config-summary">
              <span className={`s1w-config-pill s1w-config-pill--${tier === "1" ? "blue" : tier === "3" ? "green" : "orange"}`}>
                {TIER_LABEL[tier]}
              </span>
              {maxBytes && <span className="s1w-config-pill s1w-config-pill--neutral">Up to {(maxBytes / 1048576).toFixed(0)} MB per file · no row limit</span>}
            </div>
          </div>
        )}

        {/* ── STEP 4: Column Mapping ── */}
        {step === 4 && (
          <div className="s1w-body">
            {/* ── Region access banner ── */}
            {!isAdmin && allowedRegions !== null && allowedRegions.length > 0 && (
              <div className="s1w-access-banner s1w-access-banner--compact">
                <Icon.Info />
                <span>
                  <strong>Allowed regions:</strong>{" "}
                  {allowedRegions.join(" · ")}
                </span>
              </div>
            )}
            {!isAdmin && allowedRegions !== null && allowedRegions.length === 0 && (
              <div className="s1w-warn-banner">
                <Icon.Warning />
                <span><strong>No accessible regions.</strong> Your account has no assigned regions. All rows will be rejected. Contact an administrator.</span>
              </div>
            )}
            {file && (
              <div className="s1w-file-badge">
                <div className="s1w-file-badge-icon"><Icon.File /></div>
                <div className="s1w-file-badge-info">
                  <p className="s1w-file-name">{file.name}</p>
                  <p className="s1w-file-size">{file.size >= 1048576 ? `${(file.size / 1048576).toFixed(1)} MB` : `${(file.size / 1024).toFixed(1)} KB`}</p>
                </div>
                {headers.length > 0 && (
                  <div className="s1w-auto-badge"><Icon.Wand /><span>{headers.filter(h => matchedColumns.has(h)).length} of {headers.length} columns matched to fields</span></div>
                )}
              </div>
            )}

            {headers.length === 0 && (
              <div className="s1w-info-banner">
                <Icon.Info />
                <span>Excel file: reading its columns with the check below. The column mapping appears when the check is done.</span>
              </div>
            )}

            {headers.length > 0 && (
              <div className="s1w-saved-map" data-testid="saved-mapping-bar">
                <Icon.Wand />
                {appliedSaved ? (
                  <span>Using your saved mapping <strong>{appliedSaved.name}</strong>.{" "}
                    <button className="s1w-link-btn" onClick={() => applySaved(null)}>Don't use it</button>
                  </span>
                ) : fitting.length > 0 ? (
                  <span>
                    <label htmlFor="s1w-saved-select">Saved mapping for these columns: </label>
                    <select id="s1w-saved-select" className="s1w-saved-select" value=""
                      onChange={e => applySaved(fitting.find(m => String(m.id) === e.target.value) || null)}>
                      <option value="">Choose…</option>
                      {fitting.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                    </select>
                  </span>
                ) : (
                  <span>Columns matched automatically. Save the mapping to reuse it for the next file with these columns.</span>
                )}
                {saveName === null ? (
                  <button className="s1w-link-btn s1w-saved-save" disabled={matchedColumns.size === 0}
                    onClick={() => setSaveName(appliedSaved?.name || (file?.name || "").replace(/\.[^.]+$/, "").slice(0, 80))}>
                    {appliedSaved ? "Update saved mapping" : "Save this mapping"}
                  </button>
                ) : (
                  <span className="s1w-saved-form">
                    <input className="s1w-saved-input" aria-label="Mapping name" maxLength={80} value={saveName}
                      onChange={e => setSaveName(e.target.value)} onKeyDown={e => e.key === "Enter" && saveMapping()} autoFocus />
                    <button className="s1w-btn-small" onClick={saveMapping} disabled={!saveName.trim()}>Save</button>
                    <button className="s1w-link-btn" onClick={() => setSaveName(null)}>Cancel</button>
                  </span>
                )}
              </div>
            )}

            {headers.length > 0 && missingRequired.length > 0 && (
              <div className="s1w-warn-banner">
                <Icon.Warning />
                <span><strong>{missingRequired.length} required field{missingRequired.length > 1 ? "s" : ""} not mapped:</strong> {missingRequired.map(f => f.label).join(", ")}</span>
              </div>
            )}

            {/* Search bar */}
            <div className="s1w-search-bar">
              <div className="s1w-search-icon"><Icon.Search /></div>
              <input
                className="s1w-search-input"
                type="text"
                placeholder="Search fields by name, key, or description…"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="s1w-search-clear" onClick={() => setSearchQuery("")}><Icon.Close /></button>
              )}
            </div>

            {/* Calculation chosen in step 1 (one place to choose it) */}
            <div className="s1w-factor-row">
              <span className="s1w-factor-label">Calculation: <strong>{TIER_LABEL[tier]}</strong></span>
              <button className="s1w-link-btn" onClick={() => setStep(1)}>Change</button>
            </div>

            <FileCheckPanel check={check} onRecheck={runCheck} canRun={headers.length === 0 || canSubmit} />

            <label className="s1w-overwrite-row">
              <input type="checkbox" checked={overwrite} onChange={e => setOverwrite(e.target.checked)} />
              <span className="s1w-factor-label">
                <strong>Replace existing records.</strong> A row for the same facility, month, process, fuel and equipment as a
                record already in the platform replaces it, and that record goes back to Pending review. Unticked, such rows
                are skipped and listed as duplicates.
              </span>
            </label>

            <div className="s1w-factor-row" style={{ justifyContent: "space-between" }}>
              <span className="s1w-factor-label">
                {showAllFields ? "All fields are shown." : "Showing the fields matched to your file and any required field still missing."}
              </span>
              <button className="s1w-link-btn" onClick={() => setShowAllFields(v => !v)}>
                {showAllFields ? "Show only my file's fields" : "Show all fields"}
              </button>
            </div>

            {showAllFields && (tier === "3" || tier === "auto") && (
              <details className="s1w-process-filter">
                <summary>Only show Tier 3 fields for some processes</summary>
                <div className="s1w-process-grid">
                  {PROCESS_CATALOGUE.map(p => (
                    <ProcessTile
                      key={p.key}
                      process={p}
                      selected={selectedProcesses.includes(p.key)}
                      onClick={() => { toggleProcess(p.key); setProcessScope("specific"); }}
                    />
                  ))}
                </div>
                {selectedProcesses.length > 0 && (
                  <button className="s1w-link-btn" onClick={() => { setSelectedProcesses([]); setProcessScope("all"); }}>Show all processes</button>
                )}
              </details>
            )}

            {/* Field groups */}
            <div className="s1w-field-groups">
              {FIELD_GROUPS.map(group => (
                <FieldGroup
                  key={group.id}
                  group={group}
                  headers={headers}
                  mapping={mapping}
                  setMapping={setMapping}
                  searchQuery={searchQuery}
                  tier={tier}
                  processScope={processScope}
                  selectedProcesses={selectedProcesses}
                  showAll={showAllFields}
                  essentialKeys={essentialKeys}
                />
              ))}
            </div>
          </div>
        )}

        {/* ── STEP 5: Processing ── */}
        {step === 5 && jobId && (
          <div className="s1w-body s1w-body--progress">
            <UploadProgress
              jobId={jobId}
              onComplete={() => { if (onUploadSuccess) onUploadSuccess(); onClose(); }}
              onCancel={onClose}
            />
          </div>
        )}

        {step === 4 && submitError && (
          <div className="s1w-submit-error" role="alert"
               style={{ margin: "0 24px 8px", padding: "10px 14px", borderRadius: 8, background: "#fef2f2",
                        border: "1px solid #fecaca", color: "#991b1b", fontSize: "0.85rem" }}>
            Upload refused: {submitError}
          </div>
        )}

        {/* ── Footer ── */}
        {step !== 5 && (
          <div className="s1w-footer">
            <button
              className="s1w-btn-ghost"
              onClick={step === 1 ? onClose : () => setStep(s => (s === 3 ? 1 : s - 1))}
            >
              {step === 1 ? <><Icon.Close /> Cancel</> : <><Icon.ArrowLeft /> Back</>}
            </button>

            <div className="s1w-footer-right">
              {step < 4 && (
                <button
                  className="s1w-btn-primary"
                  onClick={() => setStep(s => (s === 1 ? 3 : s + 1))}
                  disabled={!canGoNext()}
                >
                  Next <Icon.ChevronRight />
                </button>
              )}
              {step === 4 && (
                <button
                  className="s1w-btn-primary"
                  onClick={handleSubmit}
                  disabled={isSubmitting || (!canSubmit && headers.length > 0) || (!isAdmin && allowedRegions !== null && allowedRegions.length === 0)}
                >
                  {isSubmitting ? <span className="s1w-spinner" /> : <Icon.Processing />}
                  {isSubmitting ? "Starting…" : check.data?.preview
                    ? `Import ${check.data.preview.is_estimate ? "about " : ""}${check.data.preview.estimated_ok.toLocaleString("en-US")} rows`
                    : "Start Import"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
