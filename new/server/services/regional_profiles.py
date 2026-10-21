"""
Sonatrach Regional Operational & Environmental Profiles Registry
================================================================
Provides authentic technical, geological, operational, and institutional
profiles for Sonatrach's major hydrocarbon basins, gas processing complexes,
refineries, and export hubs across Algeria.

Used by the Universal Master Report publication engine to generate asset-specific
and corporate-level environmental statements, compliance analyses, and decarbonization
scorecards.
"""

from typing import Any, Dict, List, Optional

SONATRACH_CORPORATE_PROFILE: Dict[str, Any] = {
    "key": "national",
    "name": "Sonatrach Corporate Group (Consolidated National)",
    "arabic_name": "الشركة الوطنية سوناطراك",
    "basin": "National Hydrocarbon Estate (Sahara Platform & Coastal Hubs)",
    "operator": "Société Nationale pour la Recherche, la Production, le Transport, la Transformation, et la Commercialisation des Hydrocarbures (SONATRACH)",
    "segment": "integrated",
    "established": 1963,
    "headquarters": "Hydra, Algiers, Algeria",
    "geology": (
        "Algeria's national hydrocarbon portfolio spans the vast intracratonic Paleozoic and Mesozoic "
        "sedimentary basins of the Saharan Platform (Berkine, Oued Mya, Illizi, Ahnet, Reggane, Timimoun) "
        "down to Mediterranean coastal refining corridors. Sedimentary thicknesses range from 3,000 to "
        "over 5,000 meters, comprising world-class Silurian and Devonian organic-rich radioactive black "
        "shale source rocks, paired with high-deliverability Triassic (TAGI), Ordovician, and Cambrian "
        "fluvio-deltaic sandstone reservoirs capped by extensive Triassic evaporitic regional seals."
    ),
    "infrastructure": (
        "Fully integrated value chain encompassing over 20,000 km of transportation pipelines (RTO, RTE, "
        "RTC networks), 5 central crude treatment hubs, 6 world-scale natural gas and LPG processing centers "
        "(Hassi R'Mel, Rhourde Nouss, Alrar, In Amenas, In Salah, Gassi Touil), 5 domestic refineries "
        "(Skikda, Arzew, Algiers, Hassi Messaoud, Adrar), and 4 coastal LNG liquefaction complexes (GL1Z, "
        "GL2Z, GL3Z at Arzew; GL1K at Skikda) with combined export capacity exceeding 60 billion m³/year."
    ),
    "flaring_profile": (
        "National flaring reduction roadmap aligned with the World Bank Zero Routine Flaring (ZRF) by 2030 "
        "initiative and Algerian Executive Decree 21-330 Article 9 (mandating a statutory flaring intensity cap "
        "of <= 1.00% of gross gas produced). Aggressive flare gas recovery (FGR) compressors, vapor recovery units "
        "(VRU), and real-time optical/ultrasonic telemetry have driven national flaring volumes down from historic "
        "peaks toward world-class international benchmarks."
    ),
    "gas_composition": {
        "ch4_mol_pct": 82.5,
        "c2h6_mol_pct": 8.5,
        "c3h8_mol_pct": 3.2,
        "ic4_mol_pct": 0.8,
        "nc4_mol_pct": 1.1,
        "ic5_mol_pct": 0.4,
        "nc5_mol_pct": 0.4,
        "c6_plus_mol_pct": 0.3,
        "co2_mol_pct": 1.5,
        "n2_mol_pct": 1.3,
        "h2s_ppm": 15.0,
    },
    "decarbonization_projects": [
        {"title": "National Flare Gas Recovery (FGR) Expansion", "reduction_tco2e": 450000, "status": "Executing"},
        {"title": "Solar Photovoltaic Hybridization of Remote Desert CPFs (500 MW)", "reduction_tco2e": 320000, "status": "Executing"},
        {"title": "In Salah Industrial Carbon Capture & Saline Aquifer Storage (CCUS)", "reduction_tco2e": 850000, "status": "Active"},
        {"title": "OGMP 2.0 Level 4/5 Top-Down Aerial Methane Quantification & Reconciliation", "reduction_tco2e": 180000, "status": "Executing"},
        {"title": "Hassi R'Mel Boosting Phase III Compression Backpressure Optimization", "reduction_tco2e": 290000, "status": "Completed"},
    ],
    "statutory_compliance": "Executive Decree 21-330, Executive Decree 06-138, Algerian NDC 2030, OGMP 2.0 Gold Standard",
}

REGIONAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "hmd": {
        "key": "hmd",
        "name": "Hassi Messaoud Oil Complex (HMD)",
        "aliases": ["ouargla / hmd", "hassi messaoud", "hmd", "hmd-south", "hmd-north", "rez"],
        "basin": "Triassic / Hassi Messaoud-Berkine Basin (Ouargla Province)",
        "operator": "Sonatrach Exploration & Production (100% Operated)",
        "segment": "upstream",
        "established": 1956,
        "geology": (
            "Supergiant paleohigh anticlinal structure extending over 1,600 km². Hydrocarbons are trapped in "
            "deep Cambro-Ordovician sandstone formations (Zone Ra, R2, R1 reservoirs) situated between 3,300 "
            "and 3,500 meters subsea. The sandstone exhibits heterogeneous diagenesis with intense quartz "
            "overgrowths and secondary porosity variations. Unconformably overlain by Triassic argillaceous "
            "evaporites acting as an impermeable seal. Maintained via high-pressure gas injection and peripheral "
            "waterflooding to counter reservoir pressure depletion and sustain crude delivery."
        ),
        "infrastructure": (
            "Multi-facility network centered around HMD-South CPF and HMD-North CPF, interconnected with 14 "
            "satellite oil gathering centers, two major gas lift compression facilities, high-pressure crude "
            "stabilization trains, and the REZ separation units with nominal throughput of ~350,000 bpd crude."
        ),
        "flaring_profile": (
            "Historically challenged by elevated Gas-to-Oil Ratios (GOR ~ 200-250 m³/m³). Modernized under the "
            "Hassi Messaoud Zero-Flaring Masterplan through multi-stage high-pressure flare gas recovery units (FGR), "
            "ultrasonic flare header flow measurement, and gas compression loops diverting off-gases into secondary "
            "reservoir reinjection."
        ),
        "gas_composition": {
            "ch4_mol_pct": 74.2,
            "c2h6_mol_pct": 11.8,
            "c3h8_mol_pct": 6.5,
            "ic4_mol_pct": 1.4,
            "nc4_mol_pct": 2.3,
            "ic5_mol_pct": 0.8,
            "nc5_mol_pct": 0.9,
            "c6_plus_mol_pct": 0.6,
            "co2_mol_pct": 1.0,
            "n2_mol_pct": 0.5,
            "h2s_ppm": 0.0,
        },
        "decarbonization_projects": [
            {"title": "HMD South Satellite Low-Pressure Flare Gas Recovery", "reduction_tco2e": 140000, "status": "Executing"},
            {"title": "Optical Gas Imaging (OGI) LDAR Campaign on 28,000 Components", "reduction_tco2e": 65000, "status": "Active"},
            {"title": "10 MW Hybrid Solar Photovoltaic Plant at HMD Peripheral Center", "reduction_tco2e": 22000, "status": "Executing"},
            {"title": "High-Efficiency Turbo-Compressor Retrofits (Low NOx Burners)", "reduction_tco2e": 48000, "status": "Planned"},
        ],
        "statutory_compliance": "Executive Decree 21-330 Art. 9 Compliant (Target <= 1.00% gross gas)",
    },
    "hrm": {
        "key": "hrm",
        "name": "Hassi R'Mel Gas Heartland (HRM)",
        "aliases": ["laghouat / hrm", "hassi r'mel", "hrm", "hassi rmel"],
        "basin": "Oued Mya Basin / Central Sahara Platform (Laghouat Province)",
        "operator": "Sonatrach Gas Division (100% Operated)",
        "segment": "upstream",
        "established": 1956,
        "geology": (
            "World's fourth largest gas field, spanning a massive structural dome over 3,500 km². The primary "
            "hydrocarbon reservoir is the Triassic Argilo-Gréseux Inférieur (TAGI) sandstone at depths of 2,100 to "
            "2,300 meters, comprising three main sand members (A, B, C) sealed by Triassic salts. Gas is wet, rich "
            "in condensate and natural gas liquids (LPG). Decades of depletion have led to pressure declines, "
            "managed by state-of-the-art multi-stage boosting compression."
        ),
        "infrastructure": (
            "Algeria's core natural gas processing hub. Comprises Central, North, and South gas processing complexes, "
            "the Mega-Pumping Plant (MPP), and the newly commissioned Boosting Phase III Stage II compression "
            "trains featuring 20 high-capacity centrifugal turbo-compressor units engineered by Baker Hughes and "
            "Tecnimont. Sustains plateau delivery of ~188 million m³/day (~60 BCM/year) with mercury-removal units."
        ),
        "flaring_profile": (
            "Extremely low routine flaring due to integrated closed-loop wet-gas processing. Flaring events are "
            "strictly non-routine (operational startups and compressor trip depressurization). Modernized with "
            "fast-response inter-stage spillback loops and ultrasonic flare monitors."
        ),
        "gas_composition": {
            "ch4_mol_pct": 84.1,
            "c2h6_mol_pct": 7.9,
            "c3h8_mol_pct": 2.4,
            "ic4_mol_pct": 0.6,
            "nc4_mol_pct": 0.8,
            "ic5_mol_pct": 0.3,
            "nc5_mol_pct": 0.3,
            "c6_plus_mol_pct": 0.2,
            "co2_mol_pct": 0.3,
            "n2_mol_pct": 3.1,
            "h2s_ppm": 0.0,
        },
        "decarbonization_projects": [
            {"title": "Boosting Phase III Multi-Stage Compression Optimization", "reduction_tco2e": 210000, "status": "Completed"},
            {"title": "Vapor Recovery Installation on Condensate Storage Spheres", "reduction_tco2e": 85000, "status": "Active"},
            {"title": "Methane Leak Detection & Ultrasonic Sensor Array at Central Plant", "reduction_tco2e": 38000, "status": "Executing"},
        ],
        "statutory_compliance": "Executive Decree 21-330 Art. 9 Benchmark Compliant (< 0.50% Flaring Intensity)",
    },
    "rns": {
        "key": "rns",
        "name": "Rhourde Nouss Gas Processing Complex (RNS)",
        "aliases": ["illizi / rns", "rhourde nouss", "rns", "rns facility"],
        "basin": "Illizi-Grand Erg Oriental Basin",
        "operator": "Sonatrach Exploration & Production (100% Operated)",
        "segment": "upstream",
        "established": 1980,
        "geology": (
            "High-pressure Ordovician sandstone and Devonian carbonate reservoirs characterized by high condensate "
            "content and mixed sweet/sour gas streams. Deep reservoirs (3,800 to 4,200 meters) with reservoir "
            "pressures exceeding 450 bar, demanding specialized metallurgical casings and high-pressure sweetening."
        ),
        "infrastructure": (
            "RNS Central Treatment Complex featuring 4 parallel high-pressure gas processing trains, high-capacity "
            "Diethanolamine (DEA/MDEA) sweetening units for H2S and CO2 absorption, dedicated Claus sulfur recovery "
            "units (SRU), and high-pressure gas reinjection compressors with aggregate processing capacity of ~48 MMSm³/day."
        ),
        "flaring_profile": (
            "Focuses on acid gas abatement and zero-flare processing during sulfur stripping. Off-gases from "
            "stabilizers are recovered through low-pressure booster compressors. Flare tips utilize high-kinetic "
            "sonic nozzles ensuring >= 99.5% combustion efficiency."
        ),
        "gas_composition": {
            "ch4_mol_pct": 79.5,
            "c2h6_mol_pct": 9.2,
            "c3h8_mol_pct": 4.1,
            "ic4_mol_pct": 0.9,
            "nc4_mol_pct": 1.2,
            "ic5_mol_pct": 0.4,
            "nc5_mol_pct": 0.5,
            "c6_plus_mol_pct": 0.4,
            "co2_mol_pct": 2.5,
            "n2_mol_pct": 1.3,
            "h2s_ppm": 120.0,
        },
        "decarbonization_projects": [
            {"title": "Amine Flash Gas Re-Routing to Sales Pipeline Header", "reduction_tco2e": 95000, "status": "Completed"},
            {"title": "LDAR Thermal Optical Imaging Across Sour Gas Trains", "reduction_tco2e": 42000, "status": "Active"},
            {"title": "Claus Tail Gas Treatment Incinerator Low-NOx Burner Upgrade", "reduction_tco2e": 31000, "status": "Executing"},
        ],
        "statutory_compliance": "Executive Decree 21-330 & Decree 06-138 Sour Gas Environmental Thresholds Compliant",
    },
    "in_amenas": {
        "key": "in_amenas",
        "name": "In Amenas Wet Gas Asset (Tiguentourine)",
        "aliases": ["in amenas", "tiguentourine", "in akamil", "illizi / in amenas"],
        "basin": "Illizi Basin (Near Libyan Border)",
        "operator": "Sonatrach Association (with Eni & Equinor)",
        "segment": "upstream",
        "established": 2006,
        "geology": (
            "Multi-field wet gas gathering complex draining the Tiguentourine, Hassi Farida, Ohanet, and In Akamil "
            "accumulations. Reservoirs span Devonian sandstones (F4, F6 members) and Ordovician quartzites at "
            "depths of 2,200 to 2,900 meters. Structural fault blocks with moderate permeability requiring "
            "infill horizontal drilling."
        ),
        "infrastructure": (
            "Tiguentourine Central Gas Facility with 3 processing trains, turbo-expanders for deep NGL recovery, "
            "dehydration, mercury removal, and export pumping stations with design capacity of 30 MMSm³/day dry gas "
            "plus 50,000 bpd condensate/LPG."
        ),
        "flaring_profile": (
            "Operated under international joint venture environmental standards. Features continuous optical flare "
            "monitoring, purge gas reduction using nitrogen seals, and automated blowdown flare segregation."
        ),
        "gas_composition": {
            "ch4_mol_pct": 81.2,
            "c2h6_mol_pct": 9.8,
            "c3h8_mol_pct": 4.6,
            "ic4_mol_pct": 0.8,
            "nc4_mol_pct": 1.0,
            "ic5_mol_pct": 0.3,
            "nc5_mol_pct": 0.4,
            "c6_plus_mol_pct": 0.3,
            "co2_mol_pct": 0.8,
            "n2_mol_pct": 0.8,
            "h2s_ppm": 5.0,
        },
        "decarbonization_projects": [
            {"title": "Nitrogen Flare Purge Conversion (Fuel Gas Savings)", "reduction_tco2e": 52000, "status": "Completed"},
            {"title": "Automated LDAR Valve Stem Repacking & Packing Replacement", "reduction_tco2e": 28000, "status": "Active"},
            {"title": "Waste Heat Recovery Units (WHRU) on Turbo-Compressors", "reduction_tco2e": 44000, "status": "Executing"},
        ],
        "statutory_compliance": "Executive Decree 21-330 Compliant (Flaring Intensity < 0.85%)",
    },
    "in_salah": {
        "key": "in_salah",
        "name": "In Salah Gas & Pioneering CCUS (ISG)",
        "aliases": ["in salah", "in salah gas", "krechba", "reg", "teg"],
        "basin": "Ahnet-Timimoun Basin (Central Algerian Sahara)",
        "operator": "Sonatrach (in historical partnership with Eni & Equinor)",
        "segment": "upstream",
        "established": 2004,
        "geology": (
            "Seven dry gas fields in central Algeria (Krechba, Teguentour, Reg, Hassi Moumene, Gour Mahmoud, "
            "In Salah). Reservoirs are Carboniferous and Devonian sandstones with high structural maturity. "
            "Raw gas contains up to 10% naturally occurring carbon dioxide (CO2)."
        ),
        "infrastructure": (
            "Krechba Central Processing Facility equipped with high-pressure MDEA CO2 removal units, coupled with "
            "one of the world's first industrial-scale Carbon Capture and Storage (CCUS) projects, featuring "
            "three horizontal injection wells storing extracted CO2 in the deep saline Krechba aquifer at 1,800m depth."
        ),
        "flaring_profile": (
            "Zero routine flaring design. Atmospheric CO2 venting is mitigated through deep aquifer sequestration. "
            "Features automated emergency depressurization with high-destruction steam/air-assisted flares."
        ),
        "gas_composition": {
            "ch4_mol_pct": 86.4,
            "c2h6_mol_pct": 3.8,
            "c3h8_mol_pct": 0.8,
            "ic4_mol_pct": 0.2,
            "nc4_mol_pct": 0.3,
            "ic5_mol_pct": 0.1,
            "nc5_mol_pct": 0.1,
            "c6_plus_mol_pct": 0.1,
            "co2_mol_pct": 7.5,
            "n2_mol_pct": 0.7,
            "h2s_ppm": 0.0,
        },
        "decarbonization_projects": [
            {"title": "Krechba Deep Saline Aquifer CO2 Sequestration (CCUS)", "reduction_tco2e": 620000, "status": "Active"},
            {"title": "Solar Photovoltaic Microgrid for Wellhead Remote RTUs", "reduction_tco2e": 12000, "status": "Completed"},
            {"title": "Pneumatic Controller Methane Elimination (Instrument Air)", "reduction_tco2e": 34000, "status": "Executing"},
        ],
        "statutory_compliance": "Pioneering International Benchmark for CCUS; Decree 21-330 Compliant",
    },
    "tft": {
        "key": "tft",
        "name": "Tin Fouyé Tabankort Field (TFT)",
        "aliases": ["illizi / tft", "tin fouye tabankort", "tft"],
        "basin": "Illizi Basin (North-Central Sector)",
        "operator": "Sonatrach, TotalEnergies & Repsol Joint Venture",
        "segment": "upstream",
        "established": 1999,
        "geology": (
            "Extensive stratiform gas and condensate accumulation in Lower Devonian (Siegenian/Gedinnian) sandstones "
            "and Ordovician quartzites at an average depth of 2,000 meters. Moderate permeability formations "
            "supported by deep multi-well manifold gathering clusters."
        ),
        "infrastructure": (
            "TFT Central Gas Plant with twin turbo-expander cryogenic processing lines, fractionation towers, and "
            "recent low-pressure booster compression stations sustaining delivery into the main Algerian gas pipeline network."
        ),
        "flaring_profile": (
            "Flaring intensity rigorously monitored under JV ESG audits. Flare systems feature dedicated low-pressure "
            "header recovery compressors and flare gas measurement conforming to international ISO standards."
        ),
        "gas_composition": {
            "ch4_mol_pct": 82.8,
            "c2h6_mol_pct": 8.7,
            "c3h8_mol_pct": 3.8,
            "ic4_mol_pct": 0.7,
            "nc4_mol_pct": 1.1,
            "ic5_mol_pct": 0.3,
            "nc5_mol_pct": 0.4,
            "c6_plus_mol_pct": 0.3,
            "co2_mol_pct": 0.9,
            "n2_mol_pct": 1.0,
            "h2s_ppm": 2.0,
        },
        "decarbonization_projects": [
            {"title": "TFT Low-Pressure Compressor Gas Recovery Project", "reduction_tco2e": 78000, "status": "Completed"},
            {"title": "Electrification of Remote Well Site Pumps", "reduction_tco2e": 26000, "status": "Active"},
            {"title": "Continuous LDAR Detection & Acoustic Leak Survey", "reduction_tco2e": 19000, "status": "Executing"},
        ],
        "statutory_compliance": "Executive Decree 21-330 Compliant (Flaring Intensity < 0.90%)",
    },
    "berkine": {
        "key": "berkine",
        "name": "Groupement Berkine (HBNS & El Merk)",
        "aliases": ["berkine / hbns", "berkine", "groupement berkine", "hbns", "el merk", "elm"],
        "basin": "Berkine Basin (Blocks 404a & 208)",
        "operator": "Groupement Berkine (Sonatrach, Occidental, Eni, TotalEnergies, Pertamina, Repsol)",
        "segment": "upstream",
        "established": 1996,
        "geology": (
            "World-class prolific hydrocarbon province comprising Block 404a (HBNS, HBN, BSF, BKNE) and Block 208 "
            "(El Merk, EME, EMN, EMK). Reservoirs are stacked Triassic (TAGI) fluvial sandstones and Devonian/Strunian "
            "sandstones sealed by comprehensive Triassic evaporites."
        ),
        "infrastructure": (
            "Two mega-complexes: HBNS CPF (Block 404a) and El Merk CPF (Block 208). Facilities feature high-pressure "
            "gas reinjection (up to 400 bar) for miscible gas flooding, crude stabilization, and cryogenic NGL extraction."
        ),
        "flaring_profile": (
            "Pioneered high-precision VISR camera optical flare monitoring establishing 99.89% (HBNS) and 99.85% (ELM) "
            "destruction efficiencies. Operational source category quantification per API Compendium with certified LDAR EPA Method 21 campaigns."
        ),
        "gas_composition": {
            "ch4_mol_pct": 74.4,
            "c2h6_mol_pct": 12.8,
            "c3h8_mol_pct": 5.6,
            "ic4_mol_pct": 1.2,
            "nc4_mol_pct": 2.0,
            "ic5_mol_pct": 0.7,
            "nc5_mol_pct": 0.8,
            "c6_plus_mol_pct": 0.6,
            "co2_mol_pct": 1.0,
            "n2_mol_pct": 0.9,
            "h2s_ppm": 0.0,
        },
        "decarbonization_projects": [
            {"title": "VISR Real-Time Flare Destruction Efficiency Optimization", "reduction_tco2e": 115000, "status": "Active"},
            {"title": "LDAR EPA Method 21 Comprehensive Component Inventory", "reduction_tco2e": 82000, "status": "Active"},
            {"title": "HBNS Flare Gas Recovery Stage II", "reduction_tco2e": 64000, "status": "Completed"},
        ],
        "statutory_compliance": "Executive Decree 21-330 Art. 9 Compliant (HBNS 0.93% Flaring Intensity)",
    },
    "skikda": {
        "key": "skikda",
        "name": "Skikda Industrial Refining & LNG Hub (RA1K / GL1K)",
        "aliases": ["skikda", "ra1k", "gl1k", "skikda refining"],
        "basin": "Eastern Mediterranean Coastal Industrial Corridor",
        "operator": "Sonatrach Refining & Petrochemicals / Liquefaction Divisions",
        "segment": "downstream",
        "established": 1972,
        "geology": (
            "Coastal marine terminal and coastal industrial zone acting as the Mediterranean maritime export terminus "
            "for crude oil, condensate, and natural gas conveyed via long-distance pipelines (RTE corridor) from Saharan fields."
        ),
        "infrastructure": (
            "Algeria's largest refining and petrochemical complex. Houses the RA1K mega-refinery (processing capacity "
            "16.5 million tonnes/year of Saharan Blend crude), catalytic reforming units, aromatics plant, and the "
            "GL1K mega-LNG liquefaction train with single-train capacity of 4.5 million tonnes/year LNG."
        ),
        "flaring_profile": (
            "Downstream continuous refinery and cryogenic liquefaction flare systems. Equipped with Flare Gas Recovery "
            "Units (FGRU), steam-assist smokeless flare burners, and boil-off gas (BOG) reliquefaction compressors."
        ),
        "gas_composition": {
            "ch4_mol_pct": 92.5,
            "c2h6_mol_pct": 5.4,
            "c3h8_mol_pct": 1.2,
            "ic4_mol_pct": 0.1,
            "nc4_mol_pct": 0.1,
            "ic5_mol_pct": 0.05,
            "nc5_mol_pct": 0.05,
            "c6_plus_mol_pct": 0.05,
            "co2_mol_pct": 0.05,
            "n2_mol_pct": 0.5,
            "h2s_ppm": 0.0,
        },
        "decarbonization_projects": [
            {"title": "Refinery Furnace Air Preheater Thermal Efficiency Upgrade", "reduction_tco2e": 130000, "status": "Completed"},
            {"title": "Boil-off Gas (BOG) Modern Cryogenic Re-injection", "reduction_tco2e": 92000, "status": "Active"},
            {"title": "EU CBAM Embedded Carbon Direct Verification Program", "reduction_tco2e": 75000, "status": "Active"},
        ],
        "statutory_compliance": "Executive Decree 06-138 (Industrial Air Emissions) & EU CBAM Reg (EU) 2023/956 Compliant",
    },
    "arzew": {
        "key": "arzew",
        "name": "Arzew Petrochemical & LNG Export Pole (GL1Z / GL2Z / RA1Z)",
        "aliases": ["oran / arzew", "arzew", "gl1z", "gl2z", "ra1z", "bethioua"],
        "basin": "Western Mediterranean Coastal Industrial Hub (Oran Province)",
        "operator": "Sonatrach Liquefaction, Petrochemicals & Refining Divisions",
        "segment": "downstream",
        "established": 1964,
        "geology": (
            "Strategic maritime export gateway on the Gulf of Arzew, terminal of the major RTO pipeline corridor "
            "originating from Hassi R'Mel and Hassi Messaoud."
        ),
        "infrastructure": (
            "Historic cradle of global LNG. Home to the legendary GL1Z and GL2Z liquefaction complexes, the "
            "modernized RA1Z refinery, world-scale ammonia and urea synthesis complexes (Fertial / Sorfert), and deep-water "
            "hydrocarbon berths loading LNG tankers for European and global markets."
        ),
        "flaring_profile": (
            "Downstream cryogenic boil-off gas management with closed-loop return headers, flare knock-out drums, and "
            "thermal oxidizers for petrochemical off-gas treatment."
        ),
        "gas_composition": {
            "ch4_mol_pct": 91.8,
            "c2h6_mol_pct": 6.1,
            "c3h8_mol_pct": 1.4,
            "ic4_mol_pct": 0.1,
            "nc4_mol_pct": 0.15,
            "ic5_mol_pct": 0.05,
            "nc5_mol_pct": 0.05,
            "c6_plus_mol_pct": 0.05,
            "co2_mol_pct": 0.1,
            "n2_mol_pct": 0.2,
            "h2s_ppm": 0.0,
        },
        "decarbonization_projects": [
            {"title": "GL1Z LNG Train Turbo-Compressor Heat Recovery", "reduction_tco2e": 145000, "status": "Executing"},
            {"title": "Arzew Industrial Harbor Methane BOG Flare Minimization", "reduction_tco2e": 88000, "status": "Completed"},
            {"title": "Ammonia Synthesis Hydrogen Tail Gas Energy Recovery", "reduction_tco2e": 62000, "status": "Active"},
        ],
        "statutory_compliance": "Executive Decree 06-138 & ISO 14001/50001 Energy Management Certified",
    },
}


def get_regional_profile(region_identifier: Optional[str]) -> Dict[str, Any]:
    """
    Retrieves the authentic operational and geological profile for a Sonatrach region,
    facility, or corporate entity using case-insensitive matching across keys and aliases.
    Defaults to the corporate consolidated profile if unmatched.
    """
    if not region_identifier or str(region_identifier).strip().lower() in ("all", "national", "global", "sonatrach"):
        return SONATRACH_CORPORATE_PROFILE

    needle = str(region_identifier).strip().lower()

    # Exact key match
    if needle in REGIONAL_PROFILES:
        return REGIONAL_PROFILES[needle]

    # Alias / substring match
    for prof in REGIONAL_PROFILES.values():
        if needle == prof["key"] or needle in prof["name"].lower():
            return prof
        for alias in prof.get("aliases", []):
            if needle == alias or alias in needle or needle in alias:
                return prof

    # Fallback to dynamic asset profile if custom region, or corporate
    clean_title = str(region_identifier).replace("_", " ").title()
    dyn_prof = dict(SONATRACH_CORPORATE_PROFILE)
    dyn_prof["key"] = needle
    dyn_prof["name"] = f"Sonatrach {clean_title} Asset"
    dyn_prof["basin"] = f"{clean_title} Operational Basin"
    return dyn_prof


def list_available_regions() -> List[Dict[str, str]]:
    """Returns a clean list of regional assets for UI selectors and dropdowns."""
    out = [{"key": "national", "name": "Sonatrach Corporate Group (Consolidated National)", "segment": "Corporate"}]
    for k, p in REGIONAL_PROFILES.items():
        out.append({"key": k, "name": p["name"], "segment": p["segment"].capitalize()})
    return out
