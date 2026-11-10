hbns_sources = [
    ("Heater 1", 0, 0.00),
    ("Heater 2", 24359006.31, 70559.22),
    ("Heater 3", 23518376.81, 68124.22),
    ("Heater 4", 24069698.74, 69721.20),
    ("Turbine 1", 41138229.73, 119162.55),
    ("Turbine 2", 38215863.77, 110697.52),
    ("Turbine 3", 39804690.90, 115299.77),
    ("Blanket Gas", 7126100.92, 20641.734),
    ("Flare Purging", 7127284.20, 20645.161),
    ("Glycol A/B", 7115448.63, 20610.878),
    ("GEN 1", 30946480.54, 89640.75),
    ("GEN 2", 10792921.61, 31263.19),
    ("SOLAR", 4043500.16, 11712.56),
    ("Flare1 - HP", 41544753.91, 117967.93),
    ("Flare2 - LP", 3627314.69, 10299.90),
    ("Flare3 - AP", 2256416.09, 6407.18),
    ("Flare4 - LT", 11106481.75, 31537.28),
    ("Flare5 - Waterflood", 1859198.63, 5279.27),
    ("Flare6 - Glycol VR", 3099964.67, 8802.47),
    ("Flare - Total of 13 field flares", 1111500.00, 3156.15),
]

print("HBNS CO2 emission factor analysis:")
for name, act, co2 in hbns_sources:
    if act > 0:
        ef = co2 / act
        print(f"{name:30s}: act={act:14.2f}, co2={co2:10.2f} -> EF = {ef:.8f} t/Nm3 ({ef*1000:.6f} kg/Nm3)")
