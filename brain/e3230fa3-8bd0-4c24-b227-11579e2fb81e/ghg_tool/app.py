import streamlit as st
import pandas as pd
from src.calculations import (
    calculate_combustion, calculate_flaring, calculate_venting, 
    calculate_fugitives, calculate_tank_losses, calculate_dehydrator, 
    calculate_loading, calculate_amine, calculate_compressor, calculate_electricity
)
from src.export import to_excel
from src.units import UnitConverter
from src.tools import calculate_gas_properties
from src.translations import get_text

# Page Config
st.set_page_config(page_title="GHG Tool", layout="wide")

# Initialize Session State
if "calculations" not in st.session_state:
    st.session_state.calculations = []
if "facility_info" not in st.session_state:
    st.session_state.facility_info = {}

# --- SIDEBAR ---
st.sidebar.title("GHG Tool 🌍")

# Language Switcher
lang = st.sidebar.selectbox("Language / Langue", ["en", "fr"], index=0)

st.sidebar.header(get_text("global_settings", lang))

# Year and Month Selection
year = st.sidebar.selectbox(get_text("calc_year", lang), range(1800, 2101), index=224) # Default 2024
month = st.sidebar.selectbox(get_text("month", lang), range(1, 13), index=0)

# Sidebar Navigation
module_options = {
    "Facility Info": "facility_info",
    "Combustion": "combustion",
    "Flaring": "flaring",
    "Venting": "venting",
    "Fugitives": "fugitives",
    "Storage Tanks": "tanks",
    "Glycol Dehydrators": "dehydrators",
    "Truck Loading": "loading",
    "Amine Units": "amine",
    "Compressor Seals": "compressors",
    "Scope 2 (Electricity)": "electricity",
    "Tools (Composition)": "tools",
    "View Report": "report",
    "Reference Data": "ref_data"
}

# Reverse mapping for display
display_options = {k: get_text(v, lang) for k, v in module_options.items()}
selected_display = st.sidebar.selectbox(get_text("select_module", lang), list(display_options.values()))

# Find the internal key
module = next(k for k, v in display_options.items() if v == selected_display)

# Helper function to display results
def display_result(result):
    if not result:
        return
    
    st.subheader(get_text("results", lang))
    
    # Main Emissions Table
    res_data = {k: v for k, v in result.items() if k not in ["_meta", "Category", "Description", "ID", "Input", "Scope", "Year", "Month", "Tier"]}
    df_res = pd.DataFrame([res_data])
    st.table(df_res)

def add_calc(result, category, description, input_str, tier, scope="Scope 1"):
    if result:
        # Add metadata
        result["Category"] = category
        result["Description"] = description
        result["Input"] = input_str
        result["ID"] = len(st.session_state.calculations) + 1
        result["Scope"] = scope
        result["Year"] = year
        result["Month"] = month
        result["Tier"] = tier
        
        st.session_state.calculations.append(result)
        st.success(get_text("calc_added", lang))

# Helper for Methodology
def show_methodology(tier, method_desc, formula_latex):
    with st.expander(f"ℹ️ {get_text('methodology', lang)} ({tier})"):
        st.markdown(f"**{get_text('method', lang)}:** {method_desc}")
        st.markdown(f"**{get_text('formula', lang)}:**")
        st.latex(formula_latex)

# --- MAIN CONTENT ---
st.title(get_text("title", lang))
st.markdown(f"*{get_text('subtitle', lang)}*")

# Live Session Table
if st.session_state.calculations:
    with st.expander(get_text("session_calcs", lang), expanded=False):
        df_live = pd.DataFrame([
            {k: v for k, v in c.items() if k != "_meta"} 
            for c in st.session_state.calculations
        ])
        st.dataframe(df_live)

# --- FACILITY INFO MODULE ---
if module == "Facility Info":
    st.header(get_text("facility_info", lang))
    
    with st.form("facility_form"):
        c1, c2 = st.columns(2)
        org_name = c1.text_input(get_text("org_name", lang), value=st.session_state.facility_info.get("org_name", ""))
        fac_name = c2.text_input(get_text("facility_name", lang), value=st.session_state.facility_info.get("facility_name", ""))
        
        c3, c4 = st.columns(2)
        fac_id = c3.text_input(get_text("facility_id", lang), value=st.session_state.facility_info.get("facility_id", ""))
        address = c4.text_input(get_text("address", lang), value=st.session_state.facility_info.get("address", ""))
        
        c5, c6, c7 = st.columns(3)
        city = c5.text_input(get_text("city", lang), value=st.session_state.facility_info.get("city", ""))
        state = c6.text_input(get_text("state", lang), value=st.session_state.facility_info.get("state", ""))
        zip_code = c7.text_input(get_text("zip", lang), value=st.session_state.facility_info.get("zip", ""))
        
        c8, c9 = st.columns(2)
        contact = c8.text_input(get_text("contact_name", lang), value=st.session_state.facility_info.get("contact_name", ""))
        email = c9.text_input(get_text("contact_email", lang), value=st.session_state.facility_info.get("contact_email", ""))
        
        if st.form_submit_button(get_text("save_facility", lang)):
            st.session_state.facility_info = {
                "org_name": org_name, "facility_name": fac_name, "facility_id": fac_id,
                "address": address, "city": city, "state": state, "zip": zip_code,
                "contact_name": contact, "contact_email": email
            }
            st.success("Facility Information Saved!")

# --- COMBUSTION MODULE ---
elif module == "Combustion":
    st.header(get_text("combustion", lang))
    
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2", "Tier 3"])
    
    show_methodology(
        tier, 
        "Emission Factor based on fuel volume/energy" if tier == "Tier 1" else "Fuel Analysis",
        r"E = Q \times EF"
    )
    
    fuel_type = st.selectbox(get_text("fuel_type", lang), ["natural_gas", "diesel", "crude_oil", "coal_bituminous"])
    
    if tier == "Tier 1":
        qty = st.number_input(get_text("quantity", lang), min_value=0.0, value=1000.0)
        unit = st.selectbox(get_text("units", lang), ["scf", "MMBtu", "gal", "bbl", "tons"])
        
        if st.button(get_text("calculate", lang)):
            result = calculate_combustion(fuel_type, qty, unit, tier)
            display_result(result)
            add_calc(result, "Combustion", f"{fuel_type} Combustion", f"{qty} {unit}", tier)
            
    elif tier == "Tier 2":
        qty = st.number_input(get_text("quantity", lang), min_value=0.0, value=1000.0)
        unit = st.selectbox(get_text("units", lang), ["scf", "MMBtu", "gal", "bbl", "tons"])
        hhv = st.number_input("Higher Heating Value (Btu/unit)", value=1026.0)
        
        if st.button(get_text("calculate", lang)):
            result = calculate_combustion(fuel_type, qty, unit, tier, hhv=hhv)
            display_result(result)
            add_calc(result, "Combustion", f"{fuel_type} Combustion (Tier 2)", f"{qty} {unit}", tier)
    
    elif tier == "Tier 3":
        qty = st.number_input(get_text("quantity", lang), min_value=0.0, value=1000.0)
        unit = st.selectbox(get_text("units", lang), ["kg", "tons", "lb"])
        carbon_content = st.number_input("Carbon Content (kg C / kg Fuel)", 0.0, 1.0, 0.75)
        
        if st.button(get_text("calculate", lang)):
            result = calculate_combustion(fuel_type, qty, unit, tier, carbon_content=carbon_content)
            display_result(result)
            add_calc(result, "Combustion", f"{fuel_type} Combustion (Tier 3)", f"{qty} {unit}", tier)

# --- FLARING MODULE ---
elif module == "Flaring":
    st.header(get_text("flaring", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2", "Tier 3"])
    
    show_methodology(tier, "Volume x EF", r"E = V_{flare} \times EF_{flare}")
    
    vol = st.number_input(get_text("volume", lang), min_value=0.0, value=100.0)
    unit = st.selectbox(get_text("units", lang), ["Mscf", "MMscf", "m3"])
    
    # Tier-specific inputs
    gas_comp = None
    carbon_content = None
    
    if tier == "Tier 2":
        st.subheader("Gas Composition (Mole %)")
        c1, c2 = st.columns(2)
        methane = c1.number_input("Methane", 0.0, 100.0, 85.0) / 100
        ethane = c2.number_input("Ethane", 0.0, 100.0, 10.0) / 100
        propane = c1.number_input("Propane", 0.0, 100.0, 3.0) / 100
        co2 = c2.number_input("CO2", 0.0, 100.0, 2.0) / 100
        gas_comp = {"methane": methane, "ethane": ethane, "propane": propane, "co2": co2}
    elif tier == "Tier 3":
        carbon_content = st.number_input("Carbon Content (kg C / kg Gas)", 0.0, 1.0, 0.75)
    
    if st.button(get_text("calculate", lang)):
        result = calculate_flaring(vol, unit, tier, gas_comp=gas_comp, carbon_content=carbon_content)
        display_result(result)
        add_calc(result, "Flaring", "Flaring Event", f"{vol} {unit}", tier)


# --- VENTING MODULE ---
elif module == "Venting":
    st.header(get_text("venting", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2", "Tier 3"])
    
    show_methodology(tier, "Volume x EF", r"E = V_{vent} \times EF_{vent}")
    
    vol = st.number_input(get_text("volume", lang), min_value=0.0, value=50.0)
    unit = st.selectbox(get_text("units", lang), ["Mscf", "MMscf", "m3"])
    
    # Tier-specific inputs
    gas_comp = None
    if tier == "Tier 2":
        st.subheader("Gas Composition (Mole %)")
        c1, c2 = st.columns(2)
        methane = c1.number_input("Methane", 0.0, 100.0, 90.0) / 100
        ethane = c2.number_input("Ethane", 0.0, 100.0, 5.0) / 100
        co2 = c1.number_input("CO2", 0.0, 100.0, 2.0) / 100
        n2 = c2.number_input("N2", 0.0, 100.0, 3.0) / 100
        gas_comp = {"methane": methane, "ethane": ethane, "co2": co2, "nitrogen": n2}
    elif tier == "Tier 3":
        st.info("Tier 3: Use measured emission rates from flow meters or direct measurement.")
    
    if st.button(get_text("calculate", lang)):
        result = calculate_venting(vol, unit, tier, gas_comp=gas_comp)
        display_result(result)
        add_calc(result, "Venting", "Venting Event", f"{vol} {unit}", tier)


# --- FUGITIVES MODULE ---
elif module == "Fugitives":
    st.header(get_text("fugitives", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2", "Tier 3"])
    
    show_methodology(tier, "Component Count x EF", r"E = \sum (Count_i \times EF_i \times Hours)")
    
    if tier in ["Tier 1", "Tier 2"]:
        st.subheader("Component Counts")
        c1, c2, c3 = st.columns(3)
        valves = c1.number_input("Valves", value=0)
        connectors = c2.number_input("Connectors", value=0)
        flanges = c3.number_input("Flanges", value=0)
        oel = c1.number_input("Open-Ended Lines", value=0)
        prv = c2.number_input("Pressure Relief Valves", value=0)
        
        service = st.selectbox(get_text("stream_type", lang), ["gas", "light_oil", "heavy_oil", "water"])
        hours = st.number_input(get_text("hours", lang), value=8760)
        
        counts = {"valves": valves, "connectors": connectors, "flanges": flanges, "open_ended_lines": oel, "prv": prv}
        
        if st.button(get_text("calculate", lang)):
            result = calculate_fugitives(counts, service, hours, tier)
            display_result(result)
            add_calc(result, "Fugitives", f"Equipment Leaks ({service})", f"{sum(counts.values())} components", tier)
    
    elif tier == "Tier 3":
        st.info("Tier 3: Enter total measured leak rate from LDAR survey")
        leak_rate = st.number_input("Total Measured Leak Rate (kg CH4/hr)", value=1.0)
        hours = st.number_input(get_text("hours", lang), value=8760)
        
        if st.button(get_text("calculate", lang)):
            result = calculate_fugitives({}, "measured", hours, tier, measured_rate=leak_rate)
            display_result(result)
            add_calc(result, "Fugitives", "LDAR Measured Leaks", f"{leak_rate} kg/hr", tier)


# --- STORAGE TANKS ---
elif module == "Storage Tanks":
    st.header(get_text("tanks", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2"])
    
    show_methodology(tier, "Throughput x EF (Flashing + Working/Breathing)", r"E = Q_{oil} \times EF_{tank}")
    
    throughput = st.number_input(get_text("throughput", lang), value=1000.0)
    unit = st.selectbox(get_text("units", lang), ["bbl", "m3", "gal"])
    temp = st.number_input(get_text("temp", lang), value=60.0)
    rvp = st.number_input(get_text("rvp", lang), value=5.0)
    
    if st.button(get_text("calculate", lang)):
        result = calculate_tank_losses(throughput, unit, temp, rvp, tier)
        display_result(result)
        add_calc(result, "Tanks", "Storage Tank Losses", f"{throughput} {unit}", tier)

# --- GLYCOL DEHYDRATORS ---
elif module == "Glycol Dehydrators":
    st.header(get_text("dehydrators", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2"])
    
    show_methodology(tier, "Gas Throughput x EF", r"E = Q_{gas} \times EF_{dehy}")
    
    throughput = st.number_input(get_text("throughput", lang), value=100.0)
    unit = st.selectbox(get_text("units", lang), ["MMscf", "Mscf"])
    
    if st.button(get_text("calculate", lang)):
        result = calculate_dehydrator(throughput, unit, tier)
        display_result(result)
        add_calc(result, "Dehydrators", "Glycol Dehydrator", f"{throughput} {unit}", tier)

# --- TRUCK LOADING ---
elif module == "Truck Loading":
    st.header(get_text("loading", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1"])
    
    show_methodology(tier, "Throughput x EF", r"E = Q_{loaded} \times EF_{loading}")
    
    throughput = st.number_input(get_text("throughput", lang), value=5000.0)
    unit = st.selectbox(get_text("units", lang), ["bbl", "gal"])
    mode = st.selectbox(get_text("mode", lang), ["submerged", "splash"])
    
    if st.button(get_text("calculate", lang)):
        result = calculate_loading(throughput, unit, mode, tier)
        display_result(result)
        add_calc(result, "Truck Loading", f"Truck Loading ({mode})", f"{throughput} {unit}", tier)

# --- AMINE UNITS ---
elif module == "Amine Units":
    st.header(get_text("amine", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2"])
    
    show_methodology(tier, "Gas Throughput x EF", r"E = Q_{gas} \times EF_{amine}")
    
    throughput = st.number_input(get_text("throughput", lang), value=100.0)
    unit = st.selectbox(get_text("units", lang), ["MMscf", "Mscf"])
    
    if st.button(get_text("calculate", lang)):
        result = calculate_amine(throughput, unit, tier)
        display_result(result)
        add_calc(result, "Amine Units", "Acid Gas Removal", f"{throughput} {unit}", tier)

# --- COMPRESSOR SEALS ---
elif module == "Compressor Seals":
    st.header(get_text("compressors", lang))
    tier = st.selectbox(get_text("tier", lang), ["Tier 1", "Tier 2"])
    
    show_methodology(tier, "Count x EF x Hours", r"E = N_{seals} \times EF_{seal} \times Hours")
    
    comp_type = st.selectbox("Compressor Type", ["Centrifugal (Wet Seal)", "Centrifugal (Dry Seal)", "Reciprocating"])
    count = st.number_input(get_text("count", lang), value=1)
    hours = st.number_input(get_text("hours", lang), value=8760)
    
    if st.button(get_text("calculate", lang)):
        # Map UI selection to internal key
        type_map = {
            "Centrifugal (Wet Seal)": "Centrifugal Wet",
            "Centrifugal (Dry Seal)": "Centrifugal Dry",
            "Reciprocating": "Reciprocating"
        }
        result = calculate_compressor(type_map[comp_type], count, hours, tier)
        display_result(result)
        add_calc(result, "Compressor Seals", f"{comp_type} Seals", f"{count} units", tier)

# --- SCOPE 2 (ELECTRICITY) ---
elif module == "Scope 2 (Electricity)":
    st.header(get_text("electricity", lang))
    
    show_methodology("Tier 1", "MWh x Grid EF", r"E = MWh \times EF_{grid}")
    
    mwh = st.number_input("Electricity Usage (MWh)", value=1000.0)
    region = st.selectbox(get_text("region", lang), ["US National", "Texas (ERCOT)", "California (CAMX)", "Northeast (NPCC)"])
    
    if st.button(get_text("calculate", lang)):
        result = calculate_electricity(mwh, region)
        display_result(result)
        add_calc(result, "Electricity", f"Purchased Power ({region})", f"{mwh} MWh", "Tier 1", scope="Scope 2")

# --- TOOLS (COMPOSITION) ---
elif module == "Tools (Composition)":
    st.header(get_text("tools", lang))
    
    st.info("Enter gas composition (mole fraction) to calculate properties.")
    
    c1, c2 = st.columns(2)
    methane = c1.number_input("Methane (C1)", 0.0, 1.0, 0.90, key="tools_methane")
    ethane = c2.number_input("Ethane (C2)", 0.0, 1.0, 0.05, key="tools_ethane")
    propane = c1.number_input("Propane (C3)", 0.0, 1.0, 0.02, key="tools_propane")
    butane = c2.number_input("Butane (C4)", 0.0, 1.0, 0.01, key="tools_butane")
    co2 = c1.number_input("CO2", 0.0, 1.0, 0.01, key="tools_co2")
    nitrogen = c2.number_input("Nitrogen (N2)", 0.0, 1.0, 0.01, key="tools_nitrogen")
    
    comp = {
        "methane": methane, "ethane": ethane, "propane": propane, 
        "butane": butane, "co2": co2, "nitrogen": nitrogen
    }
    
    # Normalize
    total = sum(comp.values())
    if total != 1.0:
        st.warning(f"Total mole fraction is {total:.3f}. It will be normalized to 1.0.")
    
    # Calculate button
    if st.button(get_text("calc_props", lang), key="tools_calc_btn"):
        props = calculate_gas_properties(comp)
        
        st.divider()
        st.subheader(get_text("calc_props_header", lang))
        
        c1, c2, c3 = st.columns(3)
        c1.metric(get_text("mw", lang), f"{props['molecular_weight']:.2f} g/mol")
        c2.metric(get_text("hhv", lang), f"{props['hhv_btu_scf']:.1f} Btu/scf")
        c3.metric(get_text("carbon_content", lang), f"{props['carbon_content_wt']*100:.2f} wt%")
        
        st.subheader(get_text("potential_ef", lang))
        
        e1, e2, e3 = st.columns(3)
        e1.metric(get_text("combustion_ox", lang), f"{props['ef_combustion_kg_kg']:.3f}")
        e2.metric(get_text("flaring_de", lang), f"{props['ef_flaring_kg_kg']:.3f}")
        e3.metric(get_text("venting_rel", lang), f"{props['ef_venting_kg_kg']:.3f}")
        
        # Option to save this analysis
        if st.button(get_text("save_analysis", lang), key="tools_save_btn"):
            # Create a dummy result to store in session
            res = {
                "CO2": 0.0, "CH4": 0.0, "N2O": 0.0, "CO2e": 0.0, # No actual emissions, just factors
                "Input": "Gas Analysis",
                "_meta": {"method": "Composition Analysis", "factors": props}
            }
            add_calc(res, "Analysis", "Gas Composition Sample", "1 Mole", "Tier 3", "N/A")


# --- REPORT MODULE ---
elif module == "View Report":
    st.header(f"{get_text('report', lang)} ({year})")
    
    if not st.session_state.calculations:
        st.warning("No calculations yet.")
    else:
        # Filter by Year
        all_data = pd.DataFrame([
            {k: v for k, v in c.items() if k != "_meta"} 
            for c in st.session_state.calculations
        ])
        
        # MASTER TABLE
        st.subheader(get_text("all_data", lang))
        st.dataframe(all_data, use_container_width=True)
        
        # Scope 1 Summary
        st.subheader(get_text("scope1", lang))
        scope1 = all_data[all_data["Scope"] == "Scope 1"]
        if not scope1.empty:
            st.metric(get_text("total_co2e", lang).format("1"), f"{scope1['CO2e'].sum():,.2f}")
            st.dataframe(scope1)
        else:
            st.info(get_text("no_data", lang).format("1"))
            
        # Scope 2 Summary
        st.subheader(get_text("scope2", lang))
        scope2 = all_data[all_data["Scope"] == "Scope 2"]
        if not scope2.empty:
            st.metric(get_text("total_co2e", lang).format("2"), f"{scope2['CO2e'].sum():,.2f}")
            st.dataframe(scope2)
        else:
            st.info(get_text("no_data", lang).format("2"))
            
        # Excel Export
        if st.button(get_text("download_report", lang)):
            # Include facility info in export
            excel_data = to_excel(st.session_state.calculations, st.session_state.facility_info)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=f"ghg_report_{year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- REFERENCE DATA ---
elif module == "Reference Data":
    st.header(get_text("ref_data", lang))
    
    from src.factors import COMBUSTION_FACTORS, FLARING_FACTORS, FUGITIVE_FACTORS, TANK_FACTORS, DEHYDRATOR_FACTORS, LOADING_FACTORS, AMINE_FACTORS, COMPRESSOR_SEAL_FACTORS, ELECTRICITY_FACTORS
    
    st.subheader("Combustion Factors")
    st.dataframe(pd.DataFrame(COMBUSTION_FACTORS).T)
    
    st.subheader("Fugitive Factors")
    st.dataframe(pd.DataFrame(FUGITIVE_FACTORS).T)
    
    st.subheader("Electricity Factors")
    st.dataframe(pd.DataFrame(ELECTRICITY_FACTORS).T)
    
    st.subheader("Other Factors")
    st.json({
        "Flaring": FLARING_FACTORS,
        "Tanks": TANK_FACTORS,
        "Dehydrators": DEHYDRATOR_FACTORS,
        "Loading": LOADING_FACTORS,
        "Amine": AMINE_FACTORS,
        "Compressors": COMPRESSOR_SEAL_FACTORS
    })
