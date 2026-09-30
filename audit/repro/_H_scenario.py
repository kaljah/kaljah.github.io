"""Agent H (SBTi) controlled scenario, used by BUG repro scripts. Audit harness only."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, sql

def build(db, target=True):
    """Clean emissions, insert hand-controlled Verified rows, return nothing.
    Facility 1 = region West, facility 3 = region Center.
      2020: S1 West 400, S1 Center 300, S2 West 100, S3 Center 200 -> total 1000, S1+S2 800, West 500
      2023: S1 West 350, S1 Center 300, S2 West 100, S3 Center 200 -> total 950,  S1+S2 750, West 450
    """
    make_db(db, overwrite=True)
    for t in ["emissions", "scope2_emissions", "scope3_emissions", "sbti_targets", "base_year_recalculations", "goals"]:
        sql(db, f"delete from {t}")
    def s1(fid, y, m, v): sql(db, "insert into emissions(year,month,facility_id,co2e_total,co2_emissions,status) values(?,?,?,?,?,'Verified')", (y, m, fid, v, v))
    def s2(fid, y, m, v): sql(db, "insert into scope2_emissions(year,month,facility_id,co2e,status) values(?,?,?,?,'Verified')", (y, m, fid, v))
    def s3(fid, y, m, v): sql(db, "insert into scope3_emissions(year,month,facility_id,co2e,status) values(?,?,?,?,'Verified')", (y, m, fid, v))
    s1(1, 2020, 6, 400); s1(3, 2020, 6, 300); s2(1, 2020, 6, 100); s3(3, 2020, 6, 200)
    s1(1, 2023, 6, 350); s1(3, 2023, 6, 300); s2(1, 2023, 6, 100); s3(3, 2023, 6, 200)
    return s1, s2, s3

TARGET = {"base_year": 2020, "base_year_emissions": 1000, "target_year": 2030, "reduction_rate_pct": 4.2, "pathway_type": "1.5C"}
