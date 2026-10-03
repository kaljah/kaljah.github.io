import Scope1ImportWizardScope1Bulk from "./scope1-import/Scope1ImportWizardScope1Bulk";
import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import { Droplets } from "lucide-react";
import { NativeSelect } from "../ui/NativeSelect";
import Papa from "papaparse";
import api from "../api";
import { autoDetectMapping, missingRequiredFields } from "../utils/importMapping";
import { useToast } from "./Toast";
import UploadProgress from "./UploadProgress";
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
    <Droplets strokeWidth="1.75" aria-hidden="true" />
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
  ) };

// ─── Process catalogue (keys are the server's Scope 1 process types) ─────────
const COMP = ["c1","c2","c3","c4","c5","c6","c7","c8","c9","c10","co2_mol","n2_mol"];
const PROCESS_CATALOGUE = [
  { key: "combustion",    label: "Combustion",             IconComp: Icon.Flame,     tier3Extra: ["hhv", ...COMP, "combustion_efficiency", "operating_temperature", "temp_unit", "operating_pressure", "press_unit", "z_factor"] },
  { key: "flaring",       label: "Flaring",                IconComp: Icon.Flame,     tier3Extra: ["flare_type", "control_efficiency", ...COMP] },
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
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "activity",      label: "Activity",       required: false, hint: "e.g. Exploration & Production" },
      { key: "division",      label: "Division",       required: false, hint: "e.g. Production, Association" },
      { key: "field",         label: "Field",          required: false, hint: "e.g. Bir Berkine" },
      { key: "group",         label: "Emission Source",required: false, hint: "Logical grouping for this emission source" },
      { key: "equipment",     label: "Equipment Name", required: false, hint: "Name of the piece of equipment" },
      { key: "equipment_id",  label: "Equipment ID",   required: false, hint: "Unique identifier for the equipment (duplicate check)" },
    ] },
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
    ] },
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
    ] },
  {
    id: "combustion_params",
    label: "Combustion / Flaring Parameters (Tier 3)",
    IconComp: Icon.Flame,
    tier3Only: true,
    fields: [
      { key: "combustion_efficiency", label: "Combustion Efficiency %", required: false, hint: "Defaults to 99.5 % for combustion" },
      { key: "flare_type",           label: "Flare Type",             required: false, hint: "elevated | enclosed_ground | air_assisted | steam_assisted" },
      { key: "control_efficiency",   label: "Flare Control Efficiency %", required: false, hint: "Flare destruction efficiency %" },
      { key: "operating_temperature",label: "Metering Temp",          required: false, hint: "Only for volumes in m3 / cf read at metering conditions" },
      { key: "temp_unit",            label: "Temp Unit",              required: false, hint: "C or F" },
      { key: "operating_pressure",   label: "Metering Pressure",      required: false, hint: "Only for volumes in m3 / cf read at metering conditions" },
      { key: "press_unit",           label: "Press Unit",             required: false, hint: "psig, psia, kPa, barg, bara" },
      { key: "z_factor",             label: "Z Factor",               required: false, hint: "Gas compressibility factor" },
    ] },
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
    ] },
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
    ] },
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
    ] },
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
    ] },
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
    ] },
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
    ] },
  {
    id: "uncertainty",
    label: "Uncertainty Overrides",
    IconComp: Icon.Settings,
    fields: [
      { key: "user_unc_co2", label: "User Uncertainty CO₂ %", required: false, hint: "Override the system uncertainty for CO2" },
      { key: "user_unc_ch4", label: "User Uncertainty CH₄ %", required: false, hint: "Override the system uncertainty for CH4" },
      { key: "user_unc_n2o", label: "User Uncertainty N₂O %", required: false, hint: "Override the system uncertainty for N2O" },
    ] },
];

// ─── Step definitions ────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: "Upload Mode",     IconComp: Icon.Settings  },
  { id: 2, label: "Process Scope",  IconComp: Icon.Layers    },
  { id: 3, label: "Select File",    IconComp: Icon.Upload    },
  { id: 4, label: "Map Columns",    IconComp: Icon.Columns   },
  { id: 5, label: "Submitted for Review",    IconComp: Icon.Processing },
];

// ─── Step Indicator ───────────────────────────────────────────────────────────
function StepBar({ current }) {
  return (
    <div className="[display:flex]! [align-items:center] [padding:16px_24px]! [gap:0] [flex-shrink:0] [border-bottom:1px_solid_var(--color-ink-200)]! [overflow-x:auto]!">
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
      <div className="[display:flex]! [align-items:center] [gap:8px] [margin-bottom:8px]!">
        <div className="s1w-mode-card-icon"><IcoComp /></div>
        <span className="[font-size:var(--text-base)]! [font-weight:700]! [color:var(--color-ink-900)]! [flex:1]">{title}</span>
        {badge && <span className={`s1w-mode-badge s1w-mode-badge--${badge.color}`}>{badge.label}</span>}
        <div className={`s1w-radio ${selected ? "checked" : ""}`} />
      </div>
      <p className="[font-size:var(--text-sm)]! [color:var(--color-ink-500)]! [margin:0]! [line-height:1.5]">{description}</p>
    </button>
  );
}

// ─── Process Tile ─────────────────────────────────────────────────────────────
function ProcessTile({ process, selected, onClick }) {
  const IcoComp = process.IconComp;
  return (
    <button className={`s1w-process-tile ${selected ? "selected" : ""}`} onClick={onClick}>
      <div className="s1w-process-tile-icon"><IcoComp /></div>
      <span className="[font-size:var(--text-sm)]! [font-weight:600]! [color:var(--color-ink-700)]! [line-height:1.3]">{process.label}</span>
      {selected && <div className="s1w-process-tile-check"><Icon.Check /></div>}
    </button>
  );
}

// ─── Mapping Row ──────────────────────────────────────────────────────────────
function MappingRow({ field, headers, value, onChange }) {
  const mapped = !!value;
  return (
    <div className={`s1w-map-row ${!mapped && field.required ? "[background:#fff9f5]!" : ""} ${mapped ? "[background:#f0fdf4]!" : ""}`}>
      <div className="[display:flex]! [flex-direction:column] [gap:2px] [min-width:0]">
        <span className="[font-size:var(--text-sm)]! [font-weight:600]! [color:var(--color-ink-900)]! [display:flex]! [align-items:center] [gap:4px]">
          {field.label}
          {field.required && <span className="[width:6px]! [height:6px]! [border-radius:50%]! [background:var(--color-red-500)]! [flex-shrink:0] [display:inline-block]!" />}
        </span>
        {field.hint && <span className="[font-size:var(--text-xs)]! [color:var(--color-ink-600)]! [line-height:1.3]">{field.hint}</span>}
      </div>
      <div className="s1w-map-select-wrap">
        {headers.length > 0 ? (
          <NativeSelect className={`s1w-map-select ${mapped ? "matched" : ""}`} value={value} onChange={e => onChange(e.target.value)}>
            <option value="">— Not mapped —</option>
            {headers.map(h => <option key={h} value={h}>{h}</option>)}
          </NativeSelect>
        ) : (
          <input className={`s1w-map-input ${mapped ? "matched" : ""}`} placeholder="Column name in your file" value={value} onChange={e => onChange(e.target.value)} />
        )}
      </div>
      <div className="[display:flex]! [justify-content:center]">
        {mapped
          ? <span className="s1w-status-ok"><Icon.Check /></span>
          : <span className="[width:22px]! [height:22px]! [border-radius:50%]! [border:2px_solid_var(--color-ink-200)]! [display:block]!" />}
      </div>
    </div>
  );
}

// ─── Field Group Panel ────────────────────────────────────────────────────────
function FieldGroup({ group, headers, mapping, setMapping, searchQuery, tier, processScope, selectedProcesses }) {
  const [open, setOpen] = useState(true);

  // Filter fields by search
  const visibleFields = useMemo(() => {
    const q = searchQuery.toLowerCase();
    return group.fields.filter(f => {
      if (q && !f.label.toLowerCase().includes(q) && !f.key.toLowerCase().includes(q) && !f.hint.toLowerCase().includes(q)) return false;
      // Hide tier3 groups entirely if tier is 1
      if (group.tier3Only && tier === "1") return false;
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
  }, [group.fields, searchQuery, tier, processScope, selectedProcesses, group.tier3Only]);

  if (visibleFields.length === 0) return null;

  const GroupIcon = group.IconComp;
  const mappedCount = visibleFields.filter(f => mapping[f.key]).length;

  return (
    <div className="s1w-field-group">
      <button className="s1w-group-header" onClick={() => setOpen(v => !v)}>
        <div className="[display:flex]! [align-items:center] [gap:10px]">
          <div className="s1w-group-icon"><GroupIcon /></div>
          <span className="[font-size:var(--text-base)]! [font-weight:700]! [color:var(--color-ink-900)]!">{group.label}</span>
          {group.tier3Only && tier === "auto" && (
            <span className="[padding:2px_8px]! [border-radius:var(--radius-lg)]! [font-size:var(--text-xs)]! [font-weight:700]! [letter-spacing:0.3px] [background:var(--color-green-50)]! [color:#047857]!">Tier 3</span>
          )}
        </div>
        <div className="[display:flex]! [align-items:center] [gap:10px]">
          <span className="[font-size:var(--text-sm)]! [color:var(--text-secondary,_var(--color-ink-500))]! [font-weight:600]!">{mappedCount}/{visibleFields.length} mapped</span>
          <Icon.ChevronDown open={open} />
        </div>
      </button>
      {open && (
        <div className="s1w-group-body">
          <div className="[display:grid]! [grid-template-columns:1fr_1fr_36px] [padding:8px_16px]! [background:var(--color-ink-50)]! [border-bottom:1px_solid_var(--color-ink-100)]! [font-size:var(--text-xs)]! [font-weight:700]! [color:var(--color-ink-600)]! [text-transform:uppercase]! [letter-spacing:0.5px] max-[600px]:[display:none]!">
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
  const [globalFactor, setGlobalFactor] = useState("auto");
  const [searchQuery, setSearchQuery] = useState("");
  const [jobId, setJobId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [overwrite, setOverwrite] = useState(false);  // replace records that already exist

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

  // File processing
  const processFile = useCallback((f) => {
    if (!f) return;
    setParseError("");
    const isExcel = f.name.toLowerCase().endsWith(".xlsx");
    if (isExcel) {
      setFile(f); setHeaders([]); setMapping({}); setStep(4);
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
        setHeaders(hdrs);
        setMapping(autoDetectMapping(hdrs, allFields));
        setFile(f);
        setStep(4);
      },
      error: () => setParseError("Failed to parse file. Please ensure it is a valid CSV.") });
  }, [allFields]);

  const onDrop = (e) => { e.preventDefault(); setIsDragging(false); processFile(e.dataTransfer.files[0]); };
  const onFileChange = (e) => { processFile(e.target.files[0]); e.target.value = ""; };

  // Template download
  const downloadTemplate = async (fmt) => {
    try {
      const processParam = processScope === "specific" && selectedProcesses.length
        ? selectedProcesses.join(",")
        : "all";
      const res = await api.get(
        `/emissions/template/${fmt}?tier=${tier}&process=${processParam}`,
        { responseType: "blob" }
      );
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = fmt === "excel" ? "Scope1_Template.xlsx" : "scope1_template.csv";
      document.body.appendChild(a); a.click(); a.remove();
    } catch { toast.error("Template download failed."); }
  };

  // Submit
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const form = new FormData();
    form.append("file", file);
    form.append("global_factor_type", globalFactor);
    form.append("scope", "1");
    form.append("overwrite_duplicates", overwrite ? "true" : "false");
    form.append("column_mapping", JSON.stringify(mapping));
    try {
      const res = await api.post("/emissions/upload/start", form, {
        headers: { "Content-Type": "multipart/form-data" } });
      setJobId(res.data.job_id);
      setStep(5);
    } catch (err) {
      toast.error("Upload error: " + (err.response?.data?.error || err.message));
    } finally { setIsSubmitting(false); }
  };

  const canGoNext = () => {
    if (step === 2 && processScope === "specific" && selectedProcesses.length === 0) return false;
    return true;
  };

  return (
    <div className="[position:fixed] [inset:0] [background:rgba(10,_15,_30,_0.68)]! [backdrop-filter:blur(6px)] [-webkit-backdrop-filter:blur(6px)]! [display:flex]! [align-items:center] [justify-content:center] [z-index:1000] [padding:16px]! [animation:s1w-fade_0.2s_ease]!" onClick={e => e.target === e.currentTarget && onClose()}>
      <Scope1ImportWizardScope1Bulk
        FIELD_GROUPS={FIELD_GROUPS}
        FieldGroup={FieldGroup}
        Icon={Icon}
        ModeCard={ModeCard}
        PROCESS_CATALOGUE={PROCESS_CATALOGUE}
        ProcessTile={ProcessTile}
        StepBar={StepBar}
        allowedRegions={allowedRegions}
        canGoNext={canGoNext}
        canSubmit={canSubmit}
        downloadTemplate={downloadTemplate}
        file={file}
        fileInputRef={fileInputRef}
        globalFactor={globalFactor}
        handleSubmit={handleSubmit}
        headers={headers}
        isAdmin={isAdmin}
        isDragging={isDragging}
        isSubmitting={isSubmitting}
        jobId={jobId}
        mapping={mapping}
        missingRequired={missingRequired}
        onClose={onClose}
        onDrop={onDrop}
        onFileChange={onFileChange}
        onUploadSuccess={onUploadSuccess}
        overwrite={overwrite}
        parseError={parseError}
        processScope={processScope}
        searchQuery={searchQuery}
        selectedProcesses={selectedProcesses}
        setGlobalFactor={setGlobalFactor}
        setIsDragging={setIsDragging}
        setMapping={setMapping}
        setOverwrite={setOverwrite}
        setProcessScope={setProcessScope}
        setSearchQuery={setSearchQuery}
        setStep={setStep}
        setTier={setTier}
        step={step}
        tier={tier}
        toggleProcess={toggleProcess}
      />
    </div>
  );
}
