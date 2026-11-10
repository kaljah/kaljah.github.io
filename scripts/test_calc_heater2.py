import sys, os
sys.path.insert(0, os.path.abspath('new/server'))

from calculations.combustion_methods import CombustionMethodCalculator
from calculations.constants import GWP_AR4

calc = CombustionMethodCalculator()

res = calc.calculate("carbon_content", {
    "fuel_state": "gas",
    "fuel_volume": 24359006.31,
    "fuel_volume_unit": "m3",
    "carbon_wt_pct": 77.1,
    "mw": 23.01,
    "fuel_type": "natural_gas",
    "hhv_btu_scf": 1362.97,
    "include_trace": True,
}, gwp_dict=GWP_AR4)

print("Heater 2 calculated:")
print("CO2:", res["results"]["co2"]["value"])
print("CH4:", res["results"]["ch4"]["value"])
print("N2O:", res["results"]["n2o"]["value"])
print("CO2e:", res["total_co2e"]["value"])
print("Inter:", res["intermediate"])

print("\nReported Heater 2 values:")
print("CO2: 70,559.22")
print("CH4: 1.237")
print("N2O: 0.346")
print("CO2e: 70,693.33")
