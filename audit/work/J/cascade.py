import sys; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql, get_app
make_db("agentJ", overwrite=True)
app=get_app("agentJ")
from extensions import db
from sqlalchemy import text
with app.app_context():
    print("fk pragma per session conn:", db.session.execute(text("pragma foreign_keys")).scalar())
    with db.engine.connect() as c: print("fk pragma new conn:", c.execute(text("pragma foreign_keys")).scalar())
a=api_client("agentJ","admin")
it=api_client.__globals__  # noop
# facility with level logs
for fid in (1,4,2,169):
    before={t:sql("agentJ",f"select count(*) n from {t} where facility_id=?",(fid,))[0]["n"] for t in ["emissions","production_data","scope2_emissions","scope3_emissions","level_upgrade_logs","cap_emissions","flaring_details","facility_equity_shares","cbam_product_exports","ogmp_surveys"]}
    r=a.delete(f"/api/facilities/{fid}")
    after={t:sql("agentJ",f"select count(*) n from {t} where facility_id=?",(fid,))[0]["n"] for t in before}
    print(fid, r.status_code, r.get_json(), "\n  before", before, "\n  after ", after)
