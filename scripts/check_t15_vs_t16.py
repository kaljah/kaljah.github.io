# Check Table 16 module totals vs Table 15 source sums

# Table 15 Stationary Combustion sources:
stat_comb_sources = [
    ("H01 Dehy Regen", 35528.02, 0.64, 0.18, 35597.55),
    ("H01 NGL Hot Oil Heater", 62315.67, 1.12, 0.31, 62437.60),
    ("H01 OT1 Hot Oil Heater", 37443.76, 0.68, 0.19, 37517.02),
    ("IGC1", 78536.02, 5.53, 1.93, 79249.20),
    ("IGC2", 84297.94, 5.93, 2.07, 85062.56),
    ("IGC3", 87337.07, 6.15, 2.15, 88130.00),
    ("RGC1", 112471.19, 7.92, 2.76, 113492.93),
    ("RGC2", 77822.18, 5.48, 1.91, 78529.19),
    ("Diesel ICE", 5285.14, 1.04, 0.04, 5324.07),
]

sc_co2 = sum(s[1] for s in stat_comb_sources)
sc_ch4 = sum(s[2] for s in stat_comb_sources)
sc_n2o = sum(s[3] for s in stat_comb_sources)
sc_co2e = sum(s[4] for s in stat_comb_sources)

print(f"Table 15 Stat Comb sum: CO2={sc_co2:.2f}, CH4={sc_ch4:.2f}, N2O={sc_n2o:.2f}, CO2e={sc_co2e:.2f}")
print("Table 16 Stat Comb:     CO2=581,036.99, CH4=34.49, N2O=11.55, CO2e=585,340.12")
print(f"Diff CO2: {sc_co2 - 581036.99:.2f}")

# Table 15 Flare sources:
flare_sources = [
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
]

fl_co2 = sum(s[1] for s in flare_sources)
fl_ch4 = sum(s[2] for s in flare_sources)
fl_n2o = sum(s[3] for s in flare_sources)
fl_co2e = sum(s[4] for s in flare_sources)

print(f"\nTable 15 Flare sum: CO2={fl_co2:.2f}, CH4={fl_ch4:.2f}, N2O={fl_n2o:.2f}, CO2e={fl_co2e:.2f}")
print("Table 16 Flare:     CO2=307,304.13, CH4=1,328.14, N2O=4.57, CO2e=341,868.29")
print(f"Diff CO2: {fl_co2 - 307304.13:.2f}")

# Table 15 Leaks:
leaks_sources = [
    ("Leak – Gas Production", 14.45, 289.01, 0.00, 7239.71),
    ("Leak – Oil Production", 1.95, 24.17, 0.00, 606.32),
    ("Leak - CPF Gas Processing", 116.24, 2494.61, 0.00, 62481.41),
]
lk_co2 = sum(s[1] for s in leaks_sources)
lk_ch4 = sum(s[2] for s in leaks_sources)
lk_co2e = sum(s[4] for s in leaks_sources)
print(f"\nTable 15 Leaks sum: CO2={lk_co2:.2f}, CH4={lk_ch4:.2f}, CO2e={lk_co2e:.2f}")
print("Table 16 Leaks:     CO2=132.65, CH4=2,807.79, CO2e=70,327.44")

# Mobile:
mob_sources = [
    ("Aviation", 1233.79, 1.23, 0.13, 1302.95),
    ("On-Road Mobile", 425.84, 0.02, 0.01, 430.27),
]
mb_co2 = sum(s[1] for s in mob_sources)
mb_ch4 = sum(s[2] for s in mob_sources)
mb_n2o = sum(s[3] for s in mob_sources)
mb_co2e = sum(s[4] for s in mob_sources)
print(f"\nTable 15 Mobile sum: CO2={mb_co2:.2f}, CH4={mb_ch4:.2f}, N2O={mb_n2o:.2f}, CO2e={mb_co2e:.2f}")
print("Table 16 Mobile:     CO2=2,259.22, CH4=1.28, N2O=0.22, CO2e=2,356.07")
print(f"Diff Mobile CO2: {2259.22 - mb_co2:.2f}")
print(f"Diff Mobile CO2e: {2356.07 - mb_co2e:.2f}")
