"""Repro (API + source check): EmissionResult shows the 1-sigma band as the 'Confidence Interval' (68%), while the
rest of the app reports 95% with k=2; Scope2/3 forms use k=1.96; page badge levels disagree with the legend and backend."""
import sys, re; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client
C = r"C:/Users/samsung/Desktop/H2/new/client/src/"
DB = "repro_G_ui"; make_db(DB, overwrite=True)
c = api_client(DB, "admin")
e = c.post("/api/emissions/", json={"facility_id": 4, "process_type": "stationary_combustion", "fuel": "Natural Gas",
          "unit": "m3", "factor_source": "default", "year": 2048, "month": 1, "quantity": 1000}).get_json()["emissions"]
v, u = e["co2"], e["uncertainty"]["co2"]
src = open(C + "components/EmissionResult.jsx", encoding="utf8").read()
assert "const margin = value * uncertainty;" in src and "Confidence Interval:" in src
print("CO2 %.4f t, API u(1 sigma)=%.4f" % (v, u))
print("EmissionResult renders ±%.4f t, 'Confidence Interval: %.4f - %.4f' (this is +/-1 sigma, ~68%%)" % (v * u, v - v * u, v + v * u))
print("95%% CI (k=2, as used by backend/CalculationDetails/Uncertainty page): %.4f - %.4f" % (v - 2 * v * u, v + 2 * v * u))
s2 = open(C + "components/Scope2Form.jsx", encoding="utf8").read(); s3 = open(C + "components/Scope3Form.jsx", encoding="utf8").read()
print("Scope2Form uses 1.96:", "* 1.96 * 100" in s2, "| Scope3Form uses 1.96:", "* 1.96 * 100" in s3, "| backend COVERAGE_FACTOR_95 = 2.0")
ua = open(C + "pages/UncertaintyAssessment.jsx", encoding="utf8").read()
print("Badge thresholds <0.1/<0.2 present:", "decimal < 0.2" in ua, "| legend says medium = ±10% to ±30%:", "±10% to ±30%" in ua)
sys.exit(1)
