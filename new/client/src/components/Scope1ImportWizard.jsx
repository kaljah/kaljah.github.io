import React, { useState, useRef, useCallback, useMemo, useEffect } from "react";
import Papa from "papaparse";
import api from "../api";
import UploadProgress from "./UploadProgress";
import { PROCESS_TYPES } from "../utils/EmissionFactors";
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

// ─── Process catalogue (maps to backend PROCESS_TYPES) ────────────────────────
const PROCESS_CATALOGUE = [
  { key: "combustion",             label: "Combustion",               IconComp: Icon.Flame,     tier1Fields: ["fuel","quantity","unit"], tier3Extra: ["hhv","c1","c2","c3","c4","c5","c6","c7","c8","c9","c10","co2_mol","n2_mol","combustion_efficiency","operating_temperature","operating_pressure"] },
  { key: "flaring",                label: "Flaring",                  IconComp: Icon.Flame,     tier1Fields: ["fuel","quantity","unit"], tier3Extra: ["flare_type","ch4_content","co2_content","control_efficiency","c1","c2","c3","c4","c5","c6","c7","c8","c9","c10"] },
  { key: "venting",                label: "Venting",                  IconComp: Icon.Wind,      tier1Fields: ["fuel","quantity","unit"], tier3Extra: ["ch4_content","co2_content"] },
  { key: "tank_flashing",          label: "Tank Flashing",            IconComp: Icon.Container, tier1Fields: ["fuel","quantity","unit"], tier3Extra: ["tank_gor","tank_ch4_content","tank_control_eff","tank_api_gravity"] },
  { key: "tank_working_standing",  label: "Tank Working/Standing",    IconComp: Icon.Container, tier1Fields: ["fuel","quantity","unit"], tier3Extra: ["tank_throughput","tank_ch4_content","tank_control_eff","tank_turnovers"] },
  { key: "pneumatic_device",       label: "Pneumatic Devices",        IconComp: Icon.Cpu,       tier1Fields: ["quantity","unit"],       tier3Extra: ["pneu_type","pneu_count","pneu_bleed_rate","pneu_hours","ch4_content"] },
  { key: "pneumatic_pump",         label: "Pneumatic Pumps",          IconComp: Icon.Cpu,       tier1Fields: ["quantity","unit"],       tier3Extra: ["pump_type","pump_count","pump_gas_rate","pump_hours"] },
  { key: "fugitives_equipment",    label: "Fugitive Equipment",       IconComp: Icon.Wind,      tier1Fields: ["quantity","unit"],       tier3Extra: ["fugitive_method","fugitive_ppm","comp_count","operating_hours","ch4_content"] },
  { key: "fugitives_leaks",        label: "Fugitive Leaks",           IconComp: Icon.Droplets,  tier1Fields: ["quantity","unit"],       tier3Extra: ["leak_count","leak_duration","leak_rate","ch4_content"] },
  { key: "completions",            label: "Well Completions",         IconComp: Icon.Layers,    tier1Fields: ["quantity","unit"],       tier3Extra: ["comp_method","comp_rate","comp_duration","ch4_content","comp_flare_eff"] },
  { key: "blowdown",               label: "Blowdowns",                IconComp: Icon.Zap,       tier1Fields: ["quantity","unit"],       tier3Extra: ["blowdown_pressure","blowdown_events","ch4_content","blowdown_temp","z_factor"] },
  { key: "dehydrator",             label: "Dehydrators",              IconComp: Icon.Droplets,  tier1Fields: ["quantity","unit"],       tier3Extra: ["dehy_throughput","dehy_pump_rate","dehy_hours","dehy_press","dehy_temp","dehy_ch4_content","dehy_eff"] },
  { key: "agr",                    label: "AGR / Acid Gas Removal",   IconComp: Icon.Activity,  tier1Fields: ["quantity","unit"],       tier3Extra: ["agr_throughput","agr_co2_in","agr_co2_out","agr_ch4_in","agr_ch4_slip","agr_control_eff"] },
];

// ─── ALL field definitions with grouping + tooltips ────────────────────────
const FIELD_GROUPS = [
  {
    id: "identity",
    label: "Location & Identity",
    IconComp: Icon.Layers,
    fields: [
      { key: "date",          label: "Date",           required: true,  hint: "Format: YYYY-MM-DD or YYYY-MM" },
      { key: "facility_name", label: "Region / Facility", required: true, hint: "Must match an existing region in the system" },
      { key: "activity",      label: "Activity",       required: false, hint: "e.g. Exploration & Production" },
      { key: "division",      label: "Division",       required: false, hint: "e.g. Production, Association" },
      { key: "field",         label: "Field",          required: false, hint: "e.g. Bir Berkine" },
      { key: "group",         label: "Emission Source",required: false, hint: "Logical grouping for this emission source" },
      { key: "equipment",     label: "Equipment Name", required: false, hint: "Name of the piece of equipment" },
      { key: "equipment_id",  label: "Equipment ID",   required: false, hint: "Unique identifier for the equipment" },
    ],
  },
  {
    id: "measurement",
    label: "Measurement",
    IconComp: Icon.Activity,
    fields: [
      { key: "process",       label: "Process Type",  required: true,  hint: "e.g. Combustion, Flaring, Venting" },
      { key: "fuel",          label: "Activity / Fuel", required: true, hint: "Must match an API Compendium fuel name exactly" },
      { key: "quantity",      label: "Quantity",      required: true,  hint: "Numeric activity data value" },
      { key: "unit",          label: "Unit",          required: true,  hint: "e.g. scf, m3, bbl, kg, tonne" },
      { key: "factor_type",   label: "Factor Type",   required: false, hint: "'default' uses API Compendium. 'custom' uses your factors." },
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
      { key: "c1",      label: "C1 (Methane) mol%",  required: false, hint: "Methane mole fraction %" },
      { key: "c2",      label: "C2 (Ethane) mol%",   required: false, hint: "Ethane mole fraction %" },
      { key: "c3",      label: "C3 (Propane) mol%",  required: false, hint: "Propane mole fraction %" },
      { key: "c4",      label: "C4 mol%",            required: false, hint: "Butane mole fraction %" },
      { key: "c5",      label: "C5 mol%",            required: false, hint: "Pentane mole fraction %" },
      { key: "c6",      label: "C6 mol%",            required: false, hint: "Hexane mole fraction %" },
      { key: "c7",      label: "C7 mol%",            required: false, hint: "" },
      { key: "c8",      label: "C8 mol%",            required: false, hint: "" },
      { key: "c9",      label: "C9 mol%",            required: false, hint: "" },
      { key: "c10",     label: "C10+ mol%",          required: false, hint: "" },
      { key: "co2_mol", label: "CO₂ mol%",           required: false, hint: "CO2 mole fraction %" },
      { key: "n2_mol",  label: "N₂ mol%",            required: false, hint: "Nitrogen mole fraction %" },
      { key: "hhv",     label: "HHV",               required: false, hint: "Higher Heating Value (Btu/scf or kJ/m³)" },
    ],
  },
  {
    id: "combustion_params",
    label: "Combustion / Flaring Parameters (Tier 3)",
    IconComp: Icon.Flame,
    tier3Only: true,
    fields: [
      { key: "combustion_efficiency", label: "Combustion Efficiency %", required: false, hint: "Defaults to 98% if not provided" },
      { key: "flare_type",           label: "Flare Type",             required: false, hint: "e.g. steam_assisted, air_assisted, non_assisted" },
      { key: "control_efficiency",   label: "Control Efficiency %",   required: false, hint: "% of emissions captured/destroyed" },
      { key: "ch4_content",          label: "CH4 Content %",          required: false, hint: "Used when full gas composition is not available" },
      { key: "co2_content",          label: "CO2 Content %",          required: false, hint: "Used when full gas composition is not available" },
      { key: "operating_temperature",label: "Operating Temp",         required: false, hint: "Temperature of gas stream" },
      { key: "temp_unit",            label: "Temp Unit",              required: false, hint: "C or F" },
      { key: "operating_pressure",   label: "Operating Pressure",     required: false, hint: "Pressure of gas stream" },
      { key: "press_unit",           label: "Press Unit",             required: false, hint: "kPa, psi, bar" },
      { key: "z_factor",             label: "Z Factor",               required: false, hint: "Gas compressibility factor" },
    ],
  },
  {
    id: "pneumatic_params",
    label: "Pneumatic / Compressor Parameters (Tier 3)",
    IconComp: Icon.Cpu,
    tier3Only: true,
    fields: [
      { key: "pneu_type",       label: "Pneumatic Type",       required: false, hint: "high_bleed, low_bleed, intermittent" },
      { key: "pneu_count",      label: "Pneumatic Count",      required: false, hint: "Number of pneumatic devices" },
      { key: "pneu_bleed_rate", label: "Pneumatic Bleed Rate", required: false, hint: "Gas bleed rate per device" },
      { key: "pneu_hours",      label: "Operating Hours",      required: false, hint: "Annual or period hours of operation" },
      { key: "pump_type",       label: "Pump Type",            required: false, hint: "e.g. reciprocating" },
      { key: "pump_count",      label: "Pump Count",           required: false, hint: "Number of pneumatic pumps" },
      { key: "pump_gas_rate",   label: "Pump Gas Rate",        required: false, hint: "Gas displacement rate per pump" },
      { key: "pump_hours",      label: "Pump Hours",           required: false, hint: "Annual operating hours" },
      { key: "comp_mode",       label: "Compressor Mode",      required: false, hint: "e.g. wet_seal, dry_seal" },
      { key: "comp_hours",      label: "Compressor Hours",     required: false, hint: "Annual operating hours" },
    ],
  },
  {
    id: "tank_params",
    label: "Tank Parameters (Tier 3)",
    IconComp: Icon.Container,
    tier3Only: true,
    fields: [
      { key: "tank_gor",            label: "Tank GOR",             required: false, hint: "Gas-oil ratio for flash calculation" },
      { key: "tank_ch4_content",    label: "Tank CH4 Content %",   required: false, hint: "Methane content of tank vapors" },
      { key: "tank_control_eff",    label: "Tank Control Eff %",   required: false, hint: "Vapor recovery efficiency" },
      { key: "tank_api_gravity",    label: "Tank API Gravity",     required: false, hint: "API gravity of stored crude" },
      { key: "tank_throughput",     label: "Tank Throughput",      required: false, hint: "For working/standing loss calculations" },
      { key: "tank_throughput_unit",label: "Tank Throughput Unit", required: false, hint: "bbl, m3" },
      { key: "tank_turnovers",      label: "Tank Turnovers",       required: false, hint: "Annual turnovers for standing loss" },
    ],
  },
  {
    id: "fugitive_params",
    label: "Fugitive Emission Parameters (Tier 3)",
    IconComp: Icon.Wind,
    tier3Only: true,
    fields: [
      { key: "fugitive_method", label: "Fugitive Method",  required: false, hint: "e.g. EPA_factor, OGI_measurement, direct" },
      { key: "fugitive_ppm",    label: "Fugitive PPM",     required: false, hint: "Measured concentration in PPM" },
      { key: "comp_count",      label: "Component Count",  required: false, hint: "Number of components surveyed" },
      { key: "operating_hours", label: "Operating Hours",  required: false, hint: "Hours of operation for leak calculation" },
      { key: "leak_count",      label: "Leak Count",       required: false, hint: "Number of leaks detected" },
      { key: "leak_duration",   label: "Leak Duration",    required: false, hint: "Duration of each leak event (hours)" },
      { key: "leak_rate",       label: "Leak Rate",        required: false, hint: "Gas leak rate per event" },
    ],
  },
  {
    id: "well_params",
    label: "Well / Completion Parameters (Tier 3)",
    IconComp: Icon.Layers,
    tier3Only: true,
    fields: [
      { key: "comp_method",       label: "Completion Method",  required: false, hint: "e.g. open_vent, flared" },
      { key: "comp_rate",         label: "Completion Rate",    required: false, hint: "Gas flow rate during completion" },
      { key: "comp_duration",     label: "Completion Duration",required: false, hint: "Duration of flowback (hours)" },
      { key: "comp_flare_eff",    label: "Flare Efficiency %", required: false, hint: "% of completion gas flared" },
      { key: "blowdown_pressure", label: "Blowdown Pressure",  required: false, hint: "Pipeline or vessel pressure before blowdown" },
      { key: "blowdown_events",   label: "Blowdown Events",    required: false, hint: "Number of blowdown events" },
      { key: "blowdown_temp",     label: "Blowdown Temp",      required: false, hint: "Gas temperature at blowdown" },
    ],
  },
  {
    id: "dehydrator_agr",
    label: "Dehydrator / AGR Parameters (Tier 3)",
    IconComp: Icon.Droplets,
    tier3Only: true,
    fields: [
      { key: "dehy_throughput",   label: "Dehy Throughput",    required: false, hint: "Gas throughput through dehydrator" },
      { key: "dehy_pump_rate",    label: "Dehy Pump Rate",     required: false, hint: "Glycol circulation rate" },
      { key: "dehy_hours",        label: "Dehy Hours",         required: false, hint: "Annual operating hours" },
      { key: "dehy_press",        label: "Dehy Pressure",      required: false, hint: "Contactor pressure" },
      { key: "dehy_temp",         label: "Dehy Temperature",   required: false, hint: "Contactor temperature" },
      { key: "dehy_ch4_content",  label: "Dehy CH4 Content %", required: false, hint: "CH4 content of gas stream" },
      { key: "dehy_eff",          label: "Dehy Efficiency %",  required: false, hint: "Water removal efficiency" },
      { key: "agr_throughput",    label: "AGR Throughput",     required: false, hint: "Gas throughput through AGR unit" },
      { key: "agr_co2_in",        label: "AGR CO₂ In",        required: false, hint: "Inlet CO2 concentration" },
      { key: "agr_co2_out",       label: "AGR CO₂ Out",       required: false, hint: "Outlet CO2 concentration" },
      { key: "agr_ch4_in",        label: "AGR CH₄ In",        required: false, hint: "Inlet CH4 concentration" },
      { key: "agr_ch4_slip",      label: "AGR CH₄ Slip",      required: false, hint: "Methane lost through solvent" },
      { key: "agr_control_eff",   label: "AGR Control Eff %", required: false, hint: "CO2 capture efficiency" },
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
  { id: 1, label: "Upload Mode",     IconComp: Icon.Settings  },
  { id: 2, label: "Process Scope",  IconComp: Icon.Layers    },
  { id: 3, label: "Select File",    IconComp: Icon.Upload    },
  { id: 4, label: "Map Columns",    IconComp: Icon.Columns   },
  { id: 5, label: "Submitted for Review",    IconComp: Icon.Processing },
];

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

// ─── Auto-detect mapping ───────────────────────────────────────────────────────
function autoDetect(headers, allFields) {
  const mapping = {};
  allFields.forEach(f => {
    const match = headers.find(h => {
      const hl = h.toLowerCase();
      return hl === f.key || hl.includes(f.key.replace(/_/g, " ")) || hl.includes(f.label.toLowerCase()) || f.label.toLowerCase().includes(hl);
    });
    if (match && !mapping[f.key]) mapping[f.key] = match;
  });
  return mapping;
}

// ─── Main Wizard ──────────────────────────────────────────────────────────────
export default function Scope1ImportWizard({ onClose, onUploadSuccess }) {
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
      setIsAdmin(["admin", "it_admin"].includes(role) ||
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
  const requiredFields = FIELD_GROUPS.flatMap(g => g.fields).filter(f => f.required);
  const missingRequired = requiredFields.filter(f => !mapping[f.key]);
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
        setMapping(autoDetect(hdrs, allFields));
        setFile(f);
        setStep(4);
      },
      error: () => setParseError("Failed to parse file. Please ensure it is a valid CSV."),
    });
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
    } catch { alert("Template download failed."); }
  };

  // Submit
  const handleSubmit = async () => {
    setIsSubmitting(true);
    const form = new FormData();
    form.append("file", file);
    form.append("global_factor_type", globalFactor);
    form.append("scope", "1");
    form.append("column_mapping", JSON.stringify(mapping));
    try {
      const res = await api.post("/emissions/upload/start", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setJobId(res.data.job_id);
      setStep(5);
    } catch (err) {
      alert("Upload error: " + (err.response?.data?.error || err.message));
    } finally { setIsSubmitting(false); }
  };

  const canGoNext = () => {
    if (step === 2 && processScope === "specific" && selectedProcesses.length === 0) return false;
    return true;
  };

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
                description="Uses API Compendium default emission factors. Only requires fuel type, quantity, and unit. Fast and simple."
              />
              <ModeCard
                selected={tier === "3"}
                onClick={() => setTier("3")}
                Icon={Icon.Settings}
                title="Tier 3 — Engineering"
                badge={{ label: "Full precision", color: "green" }}
                description="Uses actual gas composition (C1–C10), operating conditions (T/P), and process-specific parameters for maximum accuracy."
              />
              <ModeCard
                selected={tier === "auto"}
                onClick={() => setTier("auto")}
                Icon={Icon.Wand}
                title="Both Tiers — Auto Detect"
                badge={{ label: "Recommended", color: "orange" }}
                description="Mixes Tier 1 and Tier 3 rows in one file. The system detects per-row: if gas composition columns are filled, Tier 3 is used; otherwise Tier 1."
              />
            </div>
            <div className="s1w-info-banner">
              <Icon.Info />
              <span>
                {tier === "1" && "Tier 1 only requires: Region, Date, Process, Fuel, Quantity, Unit."}
                {tier === "3" && "Tier 3 requires all Tier 1 fields plus gas composition and process engineering parameters."}
                {tier === "auto" && "Auto-detect is ideal when you have a mix of sources — some with gas composition data (Tier 3) and some without (Tier 1)."}
              </span>
            </div>
          </div>
        )}

        {/* ── STEP 2: Process Scope ── */}
        {step === 2 && (
          <div className="s1w-body">
            <div className="s1w-section-title"><Icon.Layers /><span>Process Scope</span></div>
            <p className="s1w-section-desc">Does your file contain data for all process types, or a specific process?</p>
            <div className="s1w-scope-cards">
              <ModeCard
                selected={processScope === "all"}
                onClick={() => setProcessScope("all")}
                Icon={Icon.Layers}
                title="All Processes"
                description="Your file contains a Process column that identifies the type (Combustion, Flaring, Venting, etc.) for each row."
              />
              <ModeCard
                selected={processScope === "specific"}
                onClick={() => setProcessScope("specific")}
                Icon={Icon.Activity}
                title="Specific Process(es)"
                description="Your file is dedicated to one or more specific processes. Select which ones apply to filter the column mapping to only the relevant fields."
              />
            </div>
            {processScope === "specific" && (
              <div className="s1w-process-grid-wrap">
                <p className="s1w-process-grid-label">Select which processes are in your file:</p>
                <div className="s1w-process-grid">
                  {PROCESS_CATALOGUE.map(p => (
                    <ProcessTile
                      key={p.key}
                      process={p}
                      selected={selectedProcesses.includes(p.key)}
                      onClick={() => toggleProcess(p.key)}
                    />
                  ))}
                </div>
                {selectedProcesses.length === 0 && (
                  <div className="s1w-warn-inline">
                    <Icon.Warning /> Select at least one process type to continue.
                  </div>
                )}
              </div>
            )}
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
              <p className="s1w-dropzone-sub">Supports .xlsx and .csv — optimised for millions of rows</p>
              {parseError && (
                <div className="s1w-inline-error"><Icon.Warning />{parseError}</div>
              )}
            </div>

            <div className="s1w-template-section">
              <p className="s1w-template-label">Don't have a file? Download a pre-configured template:</p>
              <div className="s1w-template-btns">
                <button className="s1w-template-btn" onClick={() => downloadTemplate("excel")}>
                  <span className="s1w-template-btn-icon"><Icon.FileExcel /></span>
                  <span>
                    <strong>Excel Template</strong>
                    <small>With dropdowns, sample data & engineering sheets</small>
                  </span>
                </button>
                <button className="s1w-template-btn" onClick={() => downloadTemplate("csv")}>
                  <span className="s1w-template-btn-icon"><Icon.File /></span>
                  <span>
                    <strong>CSV Template</strong>
                    <small>Lightweight flat file — best for large datasets</small>
                  </span>
                </button>
              </div>
            </div>

            {/* Config summary pill */}
            <div className="s1w-config-summary">
              <span className={`s1w-config-pill s1w-config-pill--${tier === "1" ? "blue" : tier === "3" ? "green" : "orange"}`}>
                {tier === "1" ? "Tier 1" : tier === "3" ? "Tier 3" : "Auto-detect"}
              </span>
              <span className="s1w-config-pill s1w-config-pill--neutral">
                {processScope === "all"
                  ? "All Processes"
                  : `${selectedProcesses.length} process${selectedProcesses.length !== 1 ? "es" : ""} selected`}
              </span>
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
                  <p className="s1w-file-size">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                {headers.length > 0 && (
                  <div className="s1w-auto-badge"><Icon.Wand /><span>{Object.keys(mapping).length} auto-detected</span></div>
                )}
              </div>
            )}

            {headers.length === 0 && (
              <div className="s1w-info-banner">
                <Icon.Info />
                <span>Excel file — processed server-side. Type column names exactly as they appear in your file, or leave blank to skip that field.</span>
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

            {/* Factor selector */}
            <div className="s1w-factor-row">
              <label className="s1w-factor-label">Default factor when not specified in file:</label>
              <select className="s1w-factor-select" value={globalFactor} onChange={e => setGlobalFactor(e.target.value)}>
                <option value="auto">Auto-detect from file</option>
                <option value="default">Force Standard (API Compendium)</option>
                <option value="custom">Force Custom Factors</option>
              </select>
            </div>

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

        {/* ── Footer ── */}
        {step !== 5 && (
          <div className="s1w-footer">
            <button
              className="s1w-btn-ghost"
              onClick={step === 1 ? onClose : () => setStep(s => s - 1)}
            >
              {step === 1 ? <><Icon.Close /> Cancel</> : <><Icon.ArrowLeft /> Back</>}
            </button>

            <div className="s1w-footer-right">
              {step < 4 && (
                <button
                  className="s1w-btn-primary"
                  onClick={() => setStep(s => s + 1)}
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
                  {isSubmitting ? "Starting…" : "Start Import"}
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
