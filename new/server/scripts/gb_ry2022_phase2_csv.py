"""Phase 2 of the GB HBNS / El Merk RY 2022 validation: everything a user does to get the report's data into the
platform, through the CSV imports (POST /api/emissions/upload/start, the same endpoint the import wizard uses).

    cd new/server && python scripts/gb_ry2022_phase2_csv.py --db <empty sqlite path> --out <folder>

The script starts the app on a throw-away SQLite database (never point --db at a database you care about), seeds
two admin accounts the way an installer does (seed_admin.py: one uploads, the other approves the custom factors),
then signs in and works only through the HTTP API with CSRF tokens:
  settings -> facilities CSV -> emission sources CSV -> production CSV -> custom factors CSV (+ approval)
  -> Scope 1 CSV -> Scope 2 CSV -> read back the records, dashboard summary and intensity.
Every request and response is logged to <out>/phase2_log.json; the CSV files written are kept in <out>/csv/.
"""
import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)

ap = argparse.ArgumentParser()
ap.add_argument("--db", required=True)
ap.add_argument("--out", required=True)
args = ap.parse_args()
if os.path.exists(args.db):
    sys.exit(f"{args.db} exists: give the path of a new, empty database")
os.makedirs(os.path.join(args.out, "csv"), exist_ok=True)

ADMIN = ("gb.admin@example.org", "GbAdmin!2026-validation")
APPROVER = ("gb.approver@example.org", "GbApprove!2026-validation")
os.environ.update({
    "FLASK_ENV": "development", "DATABASE_URL": "sqlite:///" + os.path.abspath(args.db).replace("\\", "/"),
    "SECRET_KEY": "gb-phase2-validation-only", "SEED_ADMIN": "false", "LOGIN_RATE_LIMIT": "1000 per minute",
    "UPLOAD_CHECK_RATE_LIMIT": "1000 per minute",
})
# installer step: python seed_admin.py (creates the schema and the admin); a second run with another email adds
# the approving admin (a client admin cannot create accounts through the API: /api/auth/users is IT-only)
for email, pw in (ADMIN, APPROVER):
    env = dict(os.environ, ADMIN_EMAIL=email, ADMIN_PASSWORD=pw, IT_ADMIN_EMAIL="it." + email,
               IT_ADMIN_PASSWORD=pw + "-it")
    r = subprocess.run([sys.executable, "seed_admin.py"], cwd=SERVER, env=env, capture_output=True, text=True)
    if r.returncode:
        sys.exit("seed_admin.py failed: " + r.stderr[-2000:])

sys.path.insert(0, SERVER)
sys.path.insert(0, os.path.join(SERVER, "tests"))
from app import app  # noqa: E402
from calculations.constants import GWP_AR4  # noqa: E402
import gb_ry2022_cases as C  # noqa: E402

LOG = []


class Client:
    def __init__(self):
        self.c = app.test_client()
        self.token = None

    def csrf(self):
        self.token = self.c.get("/api/csrf-token").get_json()["csrf_token"]

    def call(self, method, url, step, **kw):
        if method != "GET":
            self.csrf()
            kw.setdefault("headers", {})["X-CSRFToken"] = self.token
        r = getattr(self.c, method.lower())(url, **kw)
        try:
            body = r.get_json()
        except Exception:
            body = None
        LOG.append({"step": step, "method": method, "url": url, "status": r.status_code,
                    "response": body if body is not None else r.data[:500].decode("utf-8", "replace")})
        return r.status_code, body

    def login(self, who):
        self.c = app.test_client()
        return self.call("POST", "/api/auth/login", f"login {who[0]}", json={"email": who[0], "password": who[1]})

    def upload(self, step, scope, rows, check_first=True, check_only=False, **form):
        """Write the CSV, run the file check (dry run), then import it; returns the final job status."""
        path = os.path.join(args.out, "csv", f"{step}.csv")
        cols = []
        for r in rows:
            cols += [k for k in r if k not in cols]
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)
        data = {"scope": scope, "decimal_mark": "point", **form}
        check = None
        if check_first:
            with open(path, "rb") as fh:
                st, check = self.call("POST", "/api/emissions/upload/check", f"{step} (check)",
                                      data={**data, "file": (fh, os.path.basename(path))},
                                      content_type="multipart/form-data")
        if check_only:
            return {"status": "checked only", "check": check}
        with open(path, "rb") as fh:
            st, body = self.call("POST", "/api/emissions/upload/start", step,
                                 data={**data, "file": (fh, os.path.basename(path))},
                                 content_type="multipart/form-data")
        if st != 200:
            return {"status": "refused", "http": st, "body": body, "check": check}
        job = body["job_id"]
        for _ in range(600):
            st, status = self.call("GET", f"/api/emissions/upload/status/{job}", f"{step} (status)")
            if status and status.get("status") in ("completed", "failed", "error"):
                LOG[-1]["final"] = True
                return {**status, "check": check}
            time.sleep(0.2)
        return {"status": "timeout", "check": check}


def fmt(v):
    return "" if v is None else (f"{v:.10g}" if isinstance(v, float) else str(v))


# ---------------------------------------------------------------- CSV rows built from the report
FAC = {"HBNS": {"code": "HBNS", "field": "Hassi Berkine Sud"}, "El Merk": {"code": "EMK", "field": "El Merk"}}
DATE = "2022-12"  # the report gives annual activity data: one annual row per source, booked in December


def facility_rows():
    return [{"name": n, "code": v["code"], "region": "Berkine Basin", "country": "Algeria", "location": "Illizi",
             "segment": "Upstream", "activity": "Oil and gas production", "division": "Groupement Berkine",
             "field": v["field"], "boundary_type": "Operational Control", "operator_status": "operated",
             "equity_share": 100} for n, v in FAC.items()]


SOURCE_TYPE = {"Stationary Combustion": "combustion", "Flare": "flaring", "Equipment Leaks": "fugitive",
               "Oil & Gas Venting": "non_routine_venting", "Mobile & Transportation": "mobile",
               "Miscellaneous": "other", "Storage Tank": "tank_flashing", "Indirect (Scope 2)": "electricity"}


def source_rows():
    out = []
    for s in C.SOURCES:
        tag = s["name"]
        out.append({"facility_name": s["site"], "name": tag, "equipment_id": f"{FAC[s['site']]['code']}-{tag}",
                    "type": SOURCE_TYPE[s["module"]], "status": "Active", "description": s["module"]})
    return out


def production_rows(with_total=True):
    rows = []
    for site, p in C.PRODUCTION.items():
        r = {"facility_name": site, "date": DATE, "oil_volume": p["liquids_boe"], "oil_unit": "bbl",
             "gas_volume": p["gas_sm3"], "gas_unit": "Sm3", "gross_gas_mmsm3": p["gas_sm3"] / 1e6,
             "injected_gas_mmsm3": (p["gas_sm3"] - p["gas_no_inj_sm3"]) / 1e6,
             "gas_without_injected_mmsm3": p["gas_no_inj_sm3"] / 1e6,
             "total_production_no_injected_mmboe": p["total_no_inj_boe"] / 1e6,
             "saleable_production_mmboe": p["saleable_mmboe"], "flared_gas_mmsm3": p["flare_mmsm3"]}
        if with_total:
            r["total_production_mmboe"] = p["total_boe"] / 1e6
        rows.append(r)
    return rows


CUSTOM = [  # name, co2, ch4, n2o, unit, hhv, usage, parent
    {"name": "Aviation Gasoline (Table C-1)", "co2_factor": 69.25, "ch4_factor": 0.003, "n2o_factor": 0.0006,
     "unit": "kg/MMBtu", "hhv_factor": 120000, "usage": "mobile", "parent_fuel": "Motor Gasoline",
     "source": "API Compendium 2021 Table 4-5 / EPA Part 98 Table C-1"},
]


def s1_row(s):
    """One Scope 1 CSV row for a reproduced source, with the columns of the Scope 1 template."""
    p, factor = s["payload"]
    tag = f"{FAC[s['site']]['code']}-{s['name']}"
    row = {"date": DATE, "facility_name": s["site"], "process_type": p["process_type"], "quantity": p["amount"],
           "unit": {"l": "L"}.get(p["unit"], p["unit"]), "equipment_id": tag, "group": s["module"]}
    pt = p["process_type"]
    if pt in ("combustion", "flaring") and "c1" in p:
        row["tier"] = "3"
        heater = factor is C.HEATER
        row["fuel"] = ("Natural Gas - Heater/Boiler" if heater else "Natural Gas - Turbine") if pt == "combustion" \
            else "Natural Gas"
        for k in ("c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "co2_mol", "n2_mol", "hhv", "hhv_unit"):
            row[k] = p[k]
        if pt == "flaring":
            row["destruction_efficiency"], row["combustion_efficiency"] = 98, 98
        else:  # the equipment CH4 / N2O factors next to the analysis (template columns since GB-017 / GB-031)
            row.update(ch4_factor=factor["ch4"], n2o_factor=factor["n2o"], ch4_factor_unit="kg/MMBtu",
                       n2o_factor_unit="kg/MMBtu")
    elif pt == "combustion":  # diesel engine: equipment method columns (not in the template)
        row.update(tier="1", fuel="Diesel (No. 2 Fuel Oil)", combustion_method="equipment", equipment_type="ic_diesel")
    elif pt == "mobile":
        avgas = factor is C.AVGAS
        row.update(tier="2" if avgas else "1", vehicle_type=p["vehicle_type"],
                   fuel=CUSTOM[0]["name"] if avgas else p["fuel_type"])
    elif pt == "non_routine_venting":
        row.update(tier="1", activity_key=p["activity_key"], ch4_content=p["ch4_content"], co2_content=p["co2_content"])
    elif pt == "fire_suppression":
        row.update(tier="1", agent_type="co2")
    return row


def scope2_rows():
    return [{"date": DATE, "facility_name": s["site"], "source_type": "electricity", "consumption": s["payload"][1],
             "unit": "MWh", "grid_region": "Algerian National Grid", "meter": f"{FAC[s['site']]['code']}-grid",
             "market_instrument_type": "supplier_specific", "market_emission_factor": C.REPORT_GRID["co2"]}
            for s in C.SOURCES if s["payload"] and s["payload"][0] == "scope2"]


# method probes on the dry-run check only (the report does not print these inputs; nothing is saved)
PROBES = [
    {"date": DATE, "facility_name": "HBNS", "process_type": "tank_flashing", "tier": "3", "quantity": 43_355_278,
     "unit": "bbl", "tank_method": "produced_water", "separator_pressure_psig": 50, "salt_content": "20%",
     "equipment_id": "probe-tank"},
    {"date": DATE, "facility_name": "HBNS", "process_type": "tank_flashing", "tier": "3", "quantity": 43_355_278,
     "unit": "bbl", "tank_method": "produced_water", "separator_pressure_psig": 50, "salt_content": "20",
     "equipment_id": "probe-tank-20"},
    {"date": DATE, "facility_name": "HBNS", "process_type": "wastewater", "tier": "1", "quantity": 231_696,
     "unit": "m3", "wastewater_method": "aerobic", "bod5_mg_l": 25, "equipment_id": "probe-stp"},
    {"date": DATE, "facility_name": "HBNS", "process_type": "fugitive", "tier": "1", "fuel": "Wellhead - Gas",
     "quantity": 10, "unit": "components", "operating_hours": 8760, "equipment_id": "probe-leak-equipment"},
    {"date": DATE, "facility_name": "HBNS", "process_type": "fugitive_facility", "tier": "1", "quantity": 194_132.66,
     "unit": "MMscf", "facility_type": "gas_processing", "equipment_id": "probe-leak-facility"},
    {"date": DATE, "facility_name": "HBNS", "process_type": "mobile", "tier": "1", "fuel": "Motor Gasoline",
     "quantity": 1000, "unit": "liters", "vehicle_type": "ldgv_tier1", "equipment_id": "probe-liters"},
    {"date": DATE, "facility_name": "HBNS", "process_type": "flaring", "tier": "3", "fuel": "Natural Gas",
     "quantity": 41_544_753.91, "unit": "Nm3", "destruction_efficiency": 98, "combustion_efficiency": 98,
     **{k: v for k, v in C.gas_inputs(C.HBNS_GAS).items() if k != "composition_basis"},
     "n2o_factor": 3.716e-5, "equipment_id": "probe-flare-n2o"},
]


def main():
    res = {}
    cl = Client()
    res["login"] = cl.login(ADMIN)[0]
    res["settings"] = cl.call("PUT", "/api/auth/settings", "settings AR4 + operational control",
                              json={"gwp_standard": "AR4", "consolidation_approach": "operational_control"})
    res["facilities"] = cl.upload("01_facilities", "facilities", facility_rows())
    res["sources"] = cl.upload("02_sources", "sources", source_rows())
    res["production_with_total"] = cl.upload("03a_production_with_total", "production", production_rows(True))
    res["production"] = cl.upload("03b_production", "production", production_rows(False),
                                  overwrite_duplicates="true", duplicate_action="overwrite")
    res["custom_factors"] = cl.upload("04_custom_factors", "custom_factors", CUSTOM)
    st, factors = cl.call("GET", "/api/custom-factors", "list custom factors")
    ids = [f["id"] for f in (factors if isinstance(factors, list) else factors.get("factors", []))
           if f.get("name") in {c["name"] for c in CUSTOM}]
    res["self_approval"] = [cl.call("POST", f"/api/custom-factors/{i}/approve", "self approval (must be refused)")[0]
                            for i in ids]
    ap_cl = Client()
    ap_cl.login(APPROVER)
    res["approval"] = [ap_cl.call("POST", f"/api/custom-factors/{i}/approve", "approve by second admin")[0] for i in ids]
    s1 = [s1_row(s) for s in C.SOURCES if s["kind"] == "reproduce" and s["payload"][0] != "scope2"]
    res["scope1"] = cl.upload("05_scope1", "1", s1, global_factor_type="auto")
    res["scope2"] = cl.upload("06_scope2", "2", scope2_rows())
    res["probes"] = cl.upload("07_method_probes", "1", PROBES, check_only=True)  # dry run: nothing is saved

    # read back
    st, em = cl.call("GET", "/api/emissions/?scope=1&year=2022&limit=all", "read Scope 1 records")
    st, s2 = cl.call("GET", "/api/scope2?year=2022", "read Scope 2 records")
    st, summ = cl.call("GET", "/api/dashboard/summary?year=2022", "dashboard summary")
    st, summ_mkt = cl.call("GET", "/api/dashboard/summary?year=2022&scope2_method=market", "dashboard summary market")
    st, inten = cl.call("GET", "/api/dashboard/intensity-stats?year=2022", "intensity stats")
    res["readback"] = {"scope1": em, "scope2": s2, "summary": summ, "summary_market": summ_mkt, "intensity": inten}
    with open(os.path.join(args.out, "phase2_log.json"), "w", encoding="utf-8") as fh:
        json.dump(LOG, fh, indent=1, default=str)
    with open(os.path.join(args.out, "phase2_results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print(json.dumps({k: (v.get("status"), v.get("imported_count") or v.get("success_count") or v.get("processed"),
                          len(v.get("errors") or [])) if isinstance(v, dict) and "status" in v else v
                      for k, v in res.items() if k != "readback"}, indent=1, default=str))


if __name__ == "__main__":
    main()
