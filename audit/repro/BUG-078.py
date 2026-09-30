"""Executive Brief PDF prints fixed performance claims (15.9 % reduction, 65.9 % CH4 reduction, -38.0 % flaring,
'VISR camera verified' DRE) that are not computed from data. Exits 1 while the literals are in the generator."""
import sys, re
src = open(r"C:/Users/samsung/Desktop/H2/new/client/src/utils/ModernReportGenerator.js", encoding="utf-8").read()
lits = ["15.9% reduction achieved", "65.9% reduction from baseline", "Lowest annual flaring on record (-38.0% vs baseline)",
        "Multi-spectral VISR camera verified", "|| 117898", "|| 99.85", "VERIFIED EFFICIENT"]
found = [l for l in lits if l in src]
print("hard-coded claims present in ModernReportGenerator.js:", found)
pdf = open(r"C:/Users/samsung/Desktop/H2/audit/work/F/brief.txt", encoding="utf-8", errors="ignore").read()
print("captured PDF contains '15.9% reduction':", "15.9% reduction" in pdf, "| '98% Measured':", "98% Measured" in pdf, "| DRE method from API: Standard 98% Default")
print("independent (Verified, repro_F): S1+S2 2025 vs avg(2021-23) = -99.89 %; CH4 = -99.96 %; flaring 2026 vs 2025 = -99.92 %")
sys.exit(1 if found else 0)
