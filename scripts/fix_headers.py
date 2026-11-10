with open("RESULTS_vs_REPORT.md", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace("## 4. SANGEA Module Rollup Verification", "## 5. SANGEA Module Rollup Verification")
c = c.replace("## 5. Scope Aggregations, Performance Intensities & JV Equity Breakdown", "## 6. Scope Aggregations, Performance Intensities & JV Equity Breakdown")

with open("RESULTS_vs_REPORT.md", "w", encoding="utf-8") as f:
    f.write(c)

print("Headers renumbered correctly.")
