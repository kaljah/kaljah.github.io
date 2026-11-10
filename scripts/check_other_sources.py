# Let's inspect diesel, aviation, tanks, STP, electricity, fugitives, venting

# HBNS Diesel ICE: 399.90 m3 = 399,900 L
# CO2: 1073.33, CH4: 0.211, N2O: 0.009, CO2e: 1081.24
# EF CO2 = 1073.33 / 399.90 = 2.683996 t/m3 = 2.684 kg/L
print(f"HBNS Diesel ICE CO2 EF: {1073.33 / 399.90:.6f} t/m3")
print(f"HBNS Diesel ICE CH4 EF: {0.211 / 399.90:.6f} t/m3")
print(f"HBNS Diesel ICE N2O EF: {0.009 / 399.90:.6f} t/m3")

# El Merk Diesel ICE: 1,969,122.00 L = 1969.122 m3
# CO2: 5285.14, CH4: 1.04, N2O: 0.04, CO2e: 5324.07
print(f"ELM Diesel ICE CO2 EF: {5285.14 / 1969.122:.6f} t/m3")
print(f"ELM Diesel ICE CH4 EF: {1.04 / 1969.122:.6f} t/m3")
print(f"ELM Diesel ICE N2O EF: {0.04 / 1969.122:.6f} t/m3")

# Scope 2 Electricity:
# HBNS: 136,270.00 MWh -> CO2: 57097.13, CH4: 1.09, N2O: 0.14, CO2e: 57165.28
print(f"HBNS Scope 2 CO2 EF: {57097.13 / 136270:.6f} t/MWh = {57097.13 / 136270 * 1000:.4f} g/kWh")
print(f"HBNS Scope 2 CO2e EF: {57165.28 / 136270:.6f} t/MWh = {57165.28 / 136270 * 1000:.4f} g/kWh")

# El Merk Scope 2: 338,255.00 MWh -> CO2: 141728.84, CH4: 2.71, N2O: 0.34, CO2e: 141898.00
print(f"ELM Scope 2 CO2 EF: {141728.84 / 338255:.6f} t/MWh = {141728.84 / 338255 * 1000:.4f} g/kWh")
print(f"ELM Scope 2 CO2e EF: {141898.00 / 338255:.6f} t/MWh = {141898.00 / 338255 * 1000:.4f} g/kWh")

# Tanks Produced Water:
# HBNS: 43,355,278.00 bbl -> CH4 = 63.311 t, CO2e = 1582.79 t
print(f"HBNS Produced Water CH4 EF: {63.311 / 43355278:.10f} t CH4/bbl")
print(f"HBNS Produced Water CO2e = 63.311 * 25 = {63.311 * 25:.2f} vs {1582.79}")

# ELM: 1,243,186.72 m3 -> CH4 = 11.42 t, CO2e = 285.47 t
# 1 m3 = 6.28981 bbl -> 1243186.72 m3 = 7,819,409 bbl
bbl_elm = 1243186.72 * 6.28981077
print(f"ELM Produced water bbl: {bbl_elm:.2f} -> CH4 EF: {11.42 / bbl_elm:.10f} t CH4/bbl")
print(f"ELM Produced Water CO2e = 11.42 * 25 = {11.42 * 25:.2f} vs {285.47}")

# Fire Suppressant:
# HBNS: 619 kg -> CO2 = 0.619 t, CO2e = 0.62 t (pure CO2)
# ELM: 1219.92 kg -> CO2 = 1.22 t, CO2e = 1.22 t (pure CO2)

# STP:
# HBNS: 231,696.00 m3 -> CO2 = 11.378, N2O = 0.024, CO2e = 18.43
# Note: 11.378 + 298 * 0.024 = 11.378 + 7.152 = 18.53 (or rounding of N2O)
print(f"HBNS STP CO2 EF: {11.378 / 231696:.8f} t/m3")
print(f"HBNS STP N2O EF: {0.024 / 231696:.8f} t/m3")
