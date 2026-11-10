# Let's sum all sources in Table 15
elm_sources_full = [
    # Page 33:
    ("H01 Dehy Regen", 35528.02, 0.64, 0.18, 35597.55),
    ("H01 NGL Hot Oil Heater", 62315.67, 1.12, 0.31, 62437.60),
    ("H01 OT1 Hot Oil Heater", 37443.76, 0.68, 0.19, 37517.02),
    ("IGC1", 78536.02, 5.53, 1.93, 79249.20),
    ("IGC2", 84297.94, 5.93, 2.07, 85062.56),
    ("IGC3", 87337.07, 6.15, 2.15, 88130.00),
    ("RGC1", 112471.19, 7.92, 2.76, 113492.93),
    ("RGC2", 77822.18, 5.48, 1.91, 78529.19),
    ("Diesel ICE", 5285.14, 1.04, 0.04, 5324.07),
    ("Flare – AP", 26670.68, 125.95, 0.42, 29944.46),
    ("Flare – HP", 145379.18, 610.03, 2.11, 161259.10),
    ("Flare – LP", 30164.64, 142.45, 0.47, 33867.30),
    ("Flare – NGL", 25071.13, 100.68, 0.36, 27694.33),
    ("Flare – OT1", 18637.18, 70.59, 0.26, 20479.21),
    ("Flare – OT2", 7845.14, 29.80, 0.11, 8622.85),
    ("Flare – PHLT", 50618.00, 234.93, 0.79, 56726.50),
    ("Flare-NR - EKT LP", 829.57, 3.89, 0.01, 930.78),
    ("Flare-NR - EME AP", 531.54, 2.50, 0.01, 596.59),
    ("Flare-NR - EMK HP", 1312.64, 6.17, 0.02, 1472.95),
    ("Flare-NR - EMN HPLT", 244.42, 1.15, 0.00, 274.21),
    ("Leak – Gas Production", 14.45, 289.01, 0.00, 7239.71),
    ("Leak – Oil Production", 1.95, 24.17, 0.00, 606.32),
    ("Leak - CPF Gas Processing", 116.24, 2494.61, 0.00, 62481.41),
    ("Aviation", 1233.79, 1.23, 0.13, 1302.95),
    ("On-Road Mobile", 425.84, 0.02, 0.01, 430.27),
    # Page 34:
    ("Fire Suppressant CO2", 1.22, 0.00, 0.00, 1.22),
    ("Flare - AP (DUPLICATE)", 26670.68, 125.95, 0.42, 29944.46),
    ("Non-Routine Venting – CPF", 22.20, 443.89, 0.00, 11119.57),
    ("Non-Routine Venting – Well Production", 0.00, 0.00, 0.00, 0.00),
    ("Tank - Liquid Product", 0.00, 0.00, 0.00, 0.00),
    ("Tank - Produced Water", 0.00, 11.42, 0.00, 285.47),
    ("Electricity – Imported", 141728.84, 2.71, 0.34, 141898.00),
]

tot_rep_co2 = 1032493.53
tot_rep_ch4 = 4629.72
tot_rep_n2o = 16.68
tot_rep_co2e = 1153205.84

# Sum without duplicate Flare - AP:
sources_no_dup = [s for s in elm_sources_full if s[0] != "Flare - AP (DUPLICATE)"]
sum_co2 = sum(s[1] for s in sources_no_dup)
sum_ch4 = sum(s[2] for s in sources_no_dup)
sum_n2o = sum(s[3] for s in sources_no_dup)
sum_co2e = sum(s[4] for s in sources_no_dup)

print("SUM WITHOUT DUPLICATE:")
print(f"CO2: {sum_co2:.2f} (Report Total: {tot_rep_co2}, diff: {sum_co2 - tot_rep_co2:.2f})")
print(f"CH4: {sum_ch4:.2f} (Report Total: {tot_rep_ch4}, diff: {sum_ch4 - tot_rep_ch4:.2f})")
print(f"N2O: {sum_n2o:.2f} (Report Total: {tot_rep_n2o}, diff: {sum_n2o - tot_rep_n2o:.2f})")
print(f"CO2e: {sum_co2e:.2f} (Report Total: {tot_rep_co2e}, diff: {sum_co2e - tot_rep_co2e:.2f})")

# Sum with duplicate Flare - AP:
sum_co2_dup = sum(s[1] for s in elm_sources_full)
print("\nSUM WITH DUPLICATE:")
print(f"CO2: {sum_co2_dup:.2f} (diff: {sum_co2_dup - tot_rep_co2:.2f})")
