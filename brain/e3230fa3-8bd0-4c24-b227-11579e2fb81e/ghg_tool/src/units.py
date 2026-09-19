"""
Unit Conversion Logic
Handles conversion between Metric (SI) and Imperial (US) units.
"""

class UnitConverter:
    def __init__(self, system="Imperial"):
        self.system = system # "Imperial" or "Metric"

    def convert(self, value, unit_type, from_unit, to_unit):
        """
        General conversion function.
        """
        if from_unit == to_unit:
            return value
            
        # Mass
        if unit_type == "mass":
            # Base unit: kg
            to_kg = {
                "kg": 1.0,
                "lb": 0.453592,
                "ton (metric)": 1000.0,
                "ton (short)": 907.185
            }
            kg_val = value * to_kg[from_unit]
            return kg_val / to_kg[to_unit]

        # Volume
        elif unit_type == "volume":
            # Base unit: m3
            to_m3 = {
                "m3": 1.0,
                "scf": 0.0283168, # Standard cubic foot
                "Mscf": 28.3168,
                "MMscf": 28316.8,
                "gal": 0.00378541,
                "bbl": 0.158987,
                "L": 0.001
            }
            m3_val = value * to_m3[from_unit]
            return m3_val / to_m3[to_unit]

        # Energy
        elif unit_type == "energy":
            # Base unit: GJ
            to_gj = {
                "GJ": 1.0,
                "MMBtu": 1.05506,
                "kWh": 0.0036
            }
            gj_val = value * to_gj[from_unit]
            return gj_val / to_gj[to_unit]
            
        # Pressure
        elif unit_type == "pressure":
            # Base unit: kPa
            to_kpa = {
                "kPa": 1.0,
                "psi": 6.89476,
                "psia": 6.89476,
                "bar": 100.0,
                "atm": 101.325
            }
            kpa_val = value * to_kpa[from_unit]
            return kpa_val / to_kpa[to_unit]

        # Temperature
        elif unit_type == "temperature":
            # Handle separately due to offset
            if from_unit == "F" and to_unit == "C":
                return (value - 32) * 5/9
            elif from_unit == "C" and to_unit == "F":
                return (value * 9/5) + 32
            elif from_unit == "F" and to_unit == "R":
                return value + 459.67
            elif from_unit == "C" and to_unit == "K":
                return value + 273.15
            return value

        return value
