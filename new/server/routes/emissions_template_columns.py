"""Column definitions for the Scope 1 CSV import template.

Format of each entry: (header_label, internal_key, tier, description).
Moved out of routes/emissions_template_csv.py unchanged (hardening plan, task 5.3); the route
copies this list before filtering it, so the constant itself is never modified.
"""

TEMPLATE_COLUMNS = [
    # ── REQUIRED CORE FIELDS ─────────────────────────────────────────
    (
        "[Required] date",
        "date",
        "Core",
        "Date as YYYY-MM (e.g. 2024-03). Required.",
    ),
    (
        "[Required] facility_name",
        "facility_name",
        "Core",
        "Exact facility/region name from Manage Data → Regions. Required.",
    ),
    (
        "[Required] process_type",
        "process_type",
        "Core",
        "combustion | mobile | flaring | venting | blowdown | associated_gas_venting | pneumatic | tank_flashing | tank_working | tank_breathing | drilling | completions | workovers | well_testing | unloading | agr | dehydrator | fugitive | loading | separation | stoichiometry | chemical_production (the form's process names are accepted too). Purchased steam / heat / electricity go in the Scope 2 import.",
    ),
    (
        "[Required] fuel",
        "fuel",
        "Core",
        "Emission factor name exactly as in the factor list of the manual form (e.g. Natural Gas, Diesel (No. 2 Fuel Oil), Associated Gas (Flaring), Production high-bleed controller (API study)); for factor type custom, the saved custom factor name. Required for default and custom.",
    ),
    (
        "[Required] quantity",
        "quantity",
        "Core",
        "Activity of the month (volume, mass, energy, count, drilling days...). Required, except for Tier 3 methods that derive it (e.g. completions rate x duration).",
    ),
    (
        "[Required] unit",
        "unit",
        "Core",
        "Unit of quantity: m3 | scf | mscf | mmscf | bbl | gal | l | kg | tonne | lb | kWh. Required.",
    ),
    (
        "[Required] factor_type",
        "factor_type",
        "Core",
        "default = API standard factors (Tier 1) | custom = user-saved factor | specific = engineering/Tier 3 calculation",
    ),
    # ── OPTIONAL METADATA ─────────────────────────────────────────────
    (
        "[Optional] activity",
        "activity",
        "Meta",
        "Activity label (e.g. Exploration & Production). Defaults to facility activity if blank.",
    ),
    (
        "[Optional] region",
        "region",
        "Meta",
        "Region label. Defaults to facility region if blank.",
    ),
    (
        "[Optional] division",
        "division",
        "Meta",
        "Division label. Defaults to facility division if blank.",
    ),
    (
        "[Optional] field",
        "field",
        "Meta",
        "Field/sub-unit name. Defaults to facility field if blank.",
    ),
    (
        "[Optional] group",
        "group",
        "Meta",
        "Emission source group (e.g. Compressor Station A). For reporting grouping only.",
    ),
    (
        "[Optional] equipment",
        "equipment",
        "Meta",
        "Equipment tag/ID (e.g. EQ-001). Used for duplicate detection.",
    ),
    (
        "[Optional] equipment_name",
        "equipment_name",
        "Meta",
        "Human-readable equipment name (e.g. Caterpillar G3516).",
    ),
    # ── TIER 1 COMBUSTION ─────────────────────────────────────────────
    (
        "[T1/T3] hhv",
        "hhv",
        "T1",
        "Higher Heating Value in Btu/scf (gas) or Btu/gal (liquid). Defaults from API catalog if blank. e.g. 1020 for Natural Gas.",
    ),
    (
        "[T1] ef_unit",
        "ef_unit",
        "T1",
        "Emission factor unit override. Usually kg/MMBtu or kg/m3. Leave blank to use catalog default.",
    ),
    (
        "[T1] combustion_efficiency",
        "combustion_efficiency",
        "T1",
        "Combustion efficiency 0-1 or 0-100%. Default 0.995 (99.5%). Required for Tier 3 combustion.",
    ),
    (
        "[T1] fuel_type",
        "fuel_type",
        "T1",
        "Broad fuel category: gases | liquids | solids. Needed for unit normalization.",
    ),
    # ── T1/T3 TEMPERATURE & PRESSURE NORMALIZATION (all gas processes) ─
    (
        "[T1/T3] operating_temperature",
        "operating_temperature",
        "T1",
        "Gas temperature at metering conditions. Only used when the quantity is a volume in m3 or cf read at those conditions (scf / Sm3 are already standard).",
    ),
    (
        "[T1/T3] temp_unit",
        "temp_unit",
        "T1",
        "Temperature unit: C | F | K. Default C.",
    ),
    (
        "[T1/T3] operating_pressure",
        "operating_pressure",
        "T1",
        "Gas pressure at metering conditions (gauge or absolute per press_unit). Only used for volumes in m3 or cf at those conditions.",
    ),
    (
        "[T1/T3] press_unit",
        "press_unit",
        "T1",
        "Pressure unit: psig | psia | kPa | barg | bara. Default psig.",
    ),
    (
        "[T1/T3] z_factor",
        "z_factor",
        "T1",
        "Gas compressibility factor Z. Default 1.0 (ideal gas). Use 0.85–0.99 for real gas conditions.",
    ),
    # ── TIER 3 GAS COMPOSITION (combustion, flaring, completions, blowdown, agr) ──
    (
        "[T3] c1",
        "c1",
        "T3-GasComp",
        "Methane (CH4) mole fraction 0–100 mol%. Required for Tier 3 combustion/flaring.",
    ),
    ("[T3] c2", "c2", "T3-GasComp", "Ethane (C2H6) mole fraction 0–100 mol%."),
    ("[T3] c3", "c3", "T3-GasComp", "Propane (C3H8) mole fraction 0–100 mol%."),
    ("[T3] c4", "c4", "T3-GasComp", "Butane (C4H10) mole fraction 0–100 mol%."),
    ("[T3] c5", "c5", "T3-GasComp", "Pentane (C5H12) mole fraction 0–100 mol%."),
    ("[T3] c6", "c6", "T3-GasComp", "Hexane (C6H14) mole fraction 0–100 mol%."),
    ("[T3] c7", "c7", "T3-GasComp", "Heptane (C7H16) mole fraction 0–100 mol%."),
    ("[T3] c8", "c8", "T3-GasComp", "Octane (C8H18) mole fraction 0–100 mol%."),
    ("[T3] c9", "c9", "T3-GasComp", "Nonane (C9H20) mole fraction 0–100 mol%."),
    ("[T3] c10", "c10", "T3-GasComp", "Decane+ (C10+) mole fraction 0–100 mol%."),
    (
        "[T3] n2_mol",
        "n2_mol",
        "T3-GasComp",
        "Nitrogen (N2) mole fraction 0–100 mol%.",
    ),
    (
        "[T3] co2_mol",
        "co2_mol",
        "T3-GasComp",
        "CO2 mole fraction in gas stream 0–100 mol% (distinct from emitted CO2).",
    ),
    # ── T3 FLARING ────────────────────────────────────────────────────
    (
        "[T3-Flare] flare_type",
        "flare_type",
        "T3",
        "Flare design type: elevated | enclosed_ground | offshore_boom | air_assisted | steam_assisted. Default elevated.",
    ),
    (
        "[T3-Flare] ch4_content",
        "ch4_content",
        "T3",
        "Gas stream CH4 content % (0–100). Alias for c1 for flaring/completions/unloading.",
    ),
    (
        "[T3-Flare] co2_content",
        "co2_content",
        "T3",
        "Gas stream CO2 content % (0–100). Used by completions, blowdown, unloading.",
    ),
    (
        "[T3-Flare] control_efficiency",
        "control_efficiency",
        "T3",
        "Flare/control device destruction efficiency 0–100%. Used by flaring, completions, blowdown, unloading, tanks.",
    ),
    # ── T3 DRILLING / MUD DEGASSING ───────────────────────────────────
    (
        "[T3-Drill] mud_type",
        "mud_type",
        "T3",
        "Drilling mud type: water_based | oil_based | synthetic. The quantity is drilling days (unit: days).",
    ),
    # ── T3 WELL COMPLETIONS / WORKOVERS ───────────────────────────────
    (
        "[T3-Comp] comp_method",
        "comp_method",
        "T3-Completion",
        "Completions calculation method: metered_volume (default) | rate_duration | gor_liquid.",
    ),
    (
        "[T3-Comp] comp_rate",
        "comp_rate",
        "T3-Completion",
        "Flowback gas rate, in comp_rate_unit. Required when comp_method=rate_duration.",
    ),
    (
        "[T3-Comp] comp_rate_unit",
        "comp_rate_unit",
        "T3-Completion",
        "Unit of the flowback rate: Mcf/hr (default) | Mcf/day | scf/hr | m3/hr.",
    ),
    (
        "[T3-Comp] comp_duration",
        "comp_duration",
        "T3-Completion",
        "Flowback duration (hours). Required when comp_method=rate_duration.",
    ),
    (
        "[T3-Comp] comp_liquid_bbl",
        "comp_liquid_bbl",
        "T3-Completion",
        "Liquid flowback volume (bbl). Required when comp_method=gor_liquid.",
    ),
    (
        "[T3-Comp] comp_gor",
        "comp_gor",
        "T3-Completion",
        "Gas-Oil Ratio scf/bbl. Required when comp_method=gor_liquid.",
    ),
    (
        "[T3-Comp] comp_flare_eff",
        "comp_flare_eff",
        "T3-Completion",
        "Completions flare/combustion control efficiency 0–100%.",
    ),
    (
        "[T3-Comp] comp_choke_size",
        "comp_choke_size",
        "T3-Completion",
        "Choke size in inches (optional, for engineering documentation).",
    ),
    (
        "[T3-Comp] comp_whp",
        "comp_whp",
        "T3-Completion",
        "Wellhead pressure (psia) during completions (optional).",
    ),
    # ── T3 LIQUIDS UNLOADING ──────────────────────────────────────────
    (
        "[T3-Unload] unload_depth",
        "unload_depth",
        "T3",
        "Well depth (ft). REQUIRED for liquids unloading Tier 3.",
    ),
    (
        "[T3-Unload] unload_diam",
        "unload_diam",
        "T3",
        "Casing inner diameter (inches). REQUIRED for liquids unloading Tier 3.",
    ),
    (
        "[T3-Unload] unload_press",
        "unload_press",
        "T3",
        "Shut-in surface pressure (psig). REQUIRED for liquids unloading Tier 3.",
    ),
    (
        "[T3-Unload] unload_freq",
        "unload_freq",
        "T3",
        "Number of unloading events per year. REQUIRED for liquids unloading Tier 3. (quantity can be used if blank)",
    ),
    (
        "[T3-Unload] unload_flare_eff",
        "unload_flare_eff",
        "T3",
        "Unloading vented gas flare efficiency 0–100%.",
    ),
    (
        "[T3-Unload] unload_temp",
        "unload_temp",
        "T3",
        "Well temperature at unloading conditions. Default 60°F.",
    ),
    # ── T3 VENTING / BLOWDOWN ─────────────────────────────────────────
    (
        "[T3-BDN] blowdown_pressure",
        "blowdown_pressure",
        "T3",
        "Vessel/pipeline pressure before blowdown (psig). REQUIRED for blowdown Tier 3.",
    ),
    (
        "[T3-BDN] blowdown_events",
        "blowdown_events",
        "T3",
        "Number of blowdown events per year. REQUIRED for blowdown Tier 3.",
    ),
    (
        "[T3-BDN] blowdown_unit",
        "blowdown_unit",
        "T3",
        "Unit for blowdown volume: m3 | scf | bbl. Defaults to quantity unit if blank.",
    ),
    (
        "[T3-BDN] blowdown_temp",
        "blowdown_temp",
        "T3",
        "Gas temperature in vessel before blowdown. Default 60°F.",
    ),
    (
        "[T3-BDN] blowdown_temp_unit",
        "blowdown_temp_unit",
        "T3",
        "Temperature unit for blowdown: F | C | K. Default F.",
    ),
    (
        "[T3-BDN] blowdown_press_unit",
        "blowdown_press_unit",
        "T3",
        "Pressure unit for blowdown: psig | psia | kPa. Default psig.",
    ),
    # ── T3 STORAGE TANKS ──────────────────────────────────────────────
    (
        "[T3-Tank] tank_gor",
        "tank_gor",
        "T3",
        "Tank flash gas-to-oil ratio (scf/bbl). REQUIRED for storage tank Tier 3.",
    ),
    (
        "[T3-Tank] tank_ch4_content",
        "tank_ch4_content",
        "T3",
        "Tank flash gas CH4 content % (0–100). REQUIRED for storage tank Tier 3.",
    ),
    (
        "[T3-Tank] tank_control_eff",
        "tank_control_eff",
        "T3",
        "Tank vapor control efficiency 0–100%.",
    ),
    (
        "[T3-Tank] tank_unit",
        "tank_unit",
        "T3",
        "Unit of liquid throughput: bbl | m3 | gal | l. Default bbl.",
    ),
    (
        "[T3-Tank] tank_api_gravity",
        "tank_api_gravity",
        "T3",
        "Crude API gravity (degrees). Optional, used for documentation.",
    ),
    # ── T3 PNEUMATIC DEVICES ──────────────────────────────────────────
    (
        "[T3-Pneu] pneu_count",
        "pneu_count",
        "T3",
        "Number of pneumatic devices (controllers/pumps). REQUIRED for pneumatic Tier 3.",
    ),
    (
        "[T3-Pneu] pneu_bleed_rate",
        "pneu_bleed_rate",
        "T3",
        "Measured bleed rate per device (scf/hr or m3/hr). REQUIRED for pneumatic Tier 3.",
    ),
    (
        "[T3-Pneu] pneu_bleed_unit",
        "pneu_bleed_unit",
        "T3",
        "Unit of bleed rate: scf | m3. Default scf.",
    ),
    (
        "[T3-Pneu] pneu_hours",
        "pneu_hours",
        "T3",
        "Operating hours per device in the month (e.g. 744 for a 31-day month). REQUIRED for pneumatic Tier 3.",
    ),
    (
        "[T3-Pneu] pneu_ch4_content",
        "pneu_ch4_content",
        "T3",
        "Supply gas CH4 content % (0–100). Default 85%.",
    ),
    # ── T3 ACID GAS REMOVAL (AGR / Amine / Selexol) ──────────────────
    (
        "[T3-AGR] agr_co2_in",
        "agr_co2_in",
        "T3",
        "Inlet CO2 mole % in raw gas. REQUIRED for AGR Tier 3.",
    ),
    (
        "[T3-AGR] agr_co2_out",
        "agr_co2_out",
        "T3",
        "Outlet CO2 mole % after sweetening. REQUIRED for AGR Tier 3.",
    ),
    (
        "[T3-AGR] agr_unit",
        "agr_unit",
        "T3",
        "Unit for AGR gas throughput: mmscf | m3 | scf. Default mmscf.",
    ),
    (
        "[T3-AGR] agr_ch4_in",
        "agr_ch4_in",
        "T3",
        "Inlet CH4 mole fraction or % (0–1 or 0–100). Default 0.85.",
    ),
    (
        "[T3-AGR] agr_ch4_slip",
        "agr_ch4_slip",
        "T3",
        "CH4 slip as a fraction of inlet CH4 (0–1, e.g. 0.001 = 0.1 %).",
    ),
    (
        "[T3-AGR] agr_control_eff",
        "agr_control_eff",
        "T3",
        "Acid gas control/destruction efficiency 0–100%. Default 0.",
    ),
    # ── T3 DEHYDRATOR ─────────────────────────────────────────────────
    (
        "[T3-Dehy] dehy_pump_rate",
        "dehy_pump_rate",
        "T3",
        "TEG/glycol circulation rate (gal/hr or liters/hr). Required when no throughput.",
    ),
    (
        "[T3-Dehy] dehy_pump_unit",
        "dehy_pump_unit",
        "T3",
        "Unit for pump rate: gph | lph. Default gph.",
    ),
    (
        "[T3-Dehy] dehy_hours",
        "dehy_hours",
        "T3",
        "Dehydrator annual operating hours. Default 8760.",
    ),
    (
        "[T3-Dehy] dehy_press",
        "dehy_press",
        "T3",
        "Contactor pressure (psig). Default 800.",
    ),
    (
        "[T3-Dehy] dehy_press_unit",
        "dehy_press_unit",
        "T3",
        "Pressure unit for dehydrator: psig | kPa. Default psig.",
    ),
    (
        "[T3-Dehy] dehy_temp",
        "dehy_temp",
        "T3",
        "Contactor temperature (°F). Default 100.",
    ),
    (
        "[T3-Dehy] dehy_temp_unit",
        "dehy_temp_unit",
        "T3",
        "Temperature unit for dehydrator: F | C. Default F.",
    ),
    (
        "[T3-Dehy] dehy_has_flash",
        "dehy_has_flash",
        "T3",
        "Has flash tank? true | false. Default true.",
    ),
    (
        "[T3-Dehy] dehy_flash_eff",
        "dehy_flash_eff",
        "T3",
        "Flash tank vapor recovery efficiency 0–100%. Default 0.",
    ),
    (
        "[T3-Dehy] dehy_still_type",
        "dehy_still_type",
        "T3",
        "Still column type: none | condenser | fired_reboiler. Default none.",
    ),
    (
        "[T3-Dehy] dehy_ch4_content",
        "dehy_ch4_content",
        "T3",
        "Feed gas CH4 content % (0–100). Default 85%.",
    ),
    (
        "[T3-Dehy] dehy_eff",
        "dehy_eff",
        "T3",
        "Overall glycol dehydrator emission control efficiency 0–100%. Default 0.",
    ),
    # ── ACTIVITY FACTORS (Compendium Section 6 tables) ─────────────────
    (
        "[T1] operating_hours",
        "operating_hours",
        "T1",
        "Operating hours in the month (e.g. 744) for per-hour methods: pneumatic controller / pump factors and equipment leaks. Required for those.",
    ),
    (
        "[T1] activity_days",
        "activity_days",
        "T1",
        "Operating days in the month for factors per unit-day (e.g. AGR vent per unit). Required for those factors.",
    ),
    # ── T3 MEASURED VENT VOLUME ───────────────────────────────────────
    (
        "[T3-Vent] vent_method",
        "vent_method",
        "T3",
        "Measured gas method: volume (quantity = measured gas volume in scf / Mcf / MMscf / m3). Uses ch4_content and co2_content (mol %).",
    ),
    (
        "[T3-Vent] disposition",
        "disposition",
        "T3",
        "vented (default) | flared (then combustion_efficiency applies, default 98 %).",
    ),
    # ── T3 STOICHIOMETRY (Carbon Mass Balance) ────────────────────────
    (
        "[T3-Stoich] carbon_content",
        "carbon_content",
        "T3",
        "Fuel carbon mass fraction 0–1 (e.g. 0.85 for natural gas). REQUIRED for stoichiometry.",
    ),
    # ── T3 FUGITIVE ───────────────────────────────────────────────────
    (
        "[T3-Fug] fugitive_method",
        "fugitive_method",
        "T3",
        "Tier 3 leak method: screening (Method 21 ranges) | correlation | ogi | measurement.",
    ),
    (
        "[T3-Fug] component_type",
        "component_type",
        "T3",
        "Component type: valve | connector | flange | open_ended_line | pump_seal | other.",
    ),
    (
        "[T3-Fug] service",
        "service",
        "T3",
        "Service: gas | light_oil | heavy_oil | water_oil.",
    ),
    (
        "[T3-Fug] m21_below_count",
        "m21_below_count",
        "T3",
        "Screening method: number of components screened below 10,000 ppmv.",
    ),
    (
        "[T3-Fug] m21_above_count",
        "m21_above_count",
        "T3",
        "Screening method: number of components screened at or above 10,000 ppmv.",
    ),

    # ── UNCERTAINTY OVERRIDES ─────────────────────────────────────────
    (
        "[Unc] meter_uncertainty_pct",
        "meter_uncertainty_pct",
        "Unc",
        "Flow meter measurement uncertainty % (overrides Tier default). e.g. 2.5",
    ),
    (
        "[Unc] gc_uncertainty_pct",
        "gc_uncertainty_pct",
        "Unc",
        "Gas chromatograph composition uncertainty %. e.g. 1.0",
    ),
    (
        "[Unc] user_unc_co2",
        "user_unc_co2",
        "Unc",
        "Custom CO2 emission factor uncertainty % override.",
    ),
    (
        "[Unc] user_unc_ch4",
        "user_unc_ch4",
        "Unc",
        "Custom CH4 emission factor uncertainty % override.",
    ),
    (
        "[Unc] user_unc_n2o",
        "user_unc_n2o",
        "Unc",
        "Custom N2O emission factor uncertainty % override.",
    ),
]
