"""services/gwp_recalculation.py beyond tests/test_full_audit_2026_09_30.py (grid electricity, default-boiler
steam, Scope 1 round trip): the invariant the service relies on for every stored Scope 1 record, each Scope 2
branch (market instruments, supplier factors, other boilers, cooling, CHP), and failure handling.
"""
import uuid

import pytest

from tests.test_recalculate_script import _login, _upload

AR = {}


@pytest.fixture(scope="module")
def gworld():
    from app import app as flask_app
    from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6
    from extensions import db
    from models import Facility, User

    AR.update(AR4=GWP_AR4, AR5=GWP_AR5, AR6=GWP_AR6)
    tag = uuid.uuid4().hex[:6]
    with flask_app.app_context():
        f = Facility(name=f"Gwp {tag}", region=f"GwR{tag}", activity="EP", division="D", field="F",
                     segment="Upstream", code=f"GW{tag}")
        u = User(email=f"gw_{tag}@test.com", fullName="Gw Admin", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        u.set_password("GwpPass123!")
        db.session.add_all([f, u])
        db.session.commit()
        return {"fid": f.id, "fname": f.name, "uid": u.id}


def _switch(app, standard, previous):
    from services.gwp_recalculation import recalculate_all_emissions_gwp

    with app.app_context():
        recalculate_all_emissions_gwp(standard, previous=previous)


def test_every_scope1_total_is_its_gases_at_the_gwp(app, client, gworld):
    """A switch rebuilds co2e_total from the three gas masses: a calculator that put anything else in the
    total would lose it. Checked on every catalog fuel / unit and every template example, and across a
    round trip AR5 -> AR6 -> AR4 -> AR5."""
    import logging

    from models import Emission
    from services import scope1_template as T

    logging.disable(logging.CRITICAL)
    try:
        _login(client, gworld["uid"])
        rows = []
        for proc, units in T.PROCESS_UNITS.items():
            for unit in units:
                for fuel in T.fuels_by_process().get(proc, []):
                    rows.append(dict(date="2025-04", facility_name=gworld["fname"], process_type=proc, fuel=fuel,
                                     quantity="10", unit=unit, equipment_id=f"G{len(rows):05d}", tier="1",
                                     operating_hours="720", activity_days="30"))
        for proc, tier, cells in T.examples(gworld["fname"]):
            rows.append(dict(cells, date="2025-04", tier=tier, equipment_id=f"GX{len(rows):05d}"))
        assert _upload(client, rows)["status"] == "completed"
    finally:
        logging.disable(logging.NOTSET)

    def check(std):
        g = AR[std]
        with app.app_context():
            recs = Emission.query.filter_by(facility_id=gworld["fid"]).all()
            assert len(recs) > 300
            bad = [(r.equipment_id, r.process_type, r.fuel_type, r.co2e_total)
                   for r in recs
                   if abs((r.co2_emissions or 0) + (r.ch4_emissions or 0) * g["CH4"] + (r.n2o_emissions or 0) * g["N2O"]
                          - (r.co2e_total or 0)) > 1e-9 * max(abs(r.co2e_total or 0), 1e-12)]
            assert not bad, f"{std}: totals that are not CO2 + CH4 x GWP + N2O x GWP: {bad[:20]}"
            return {r.id: r.co2e_total for r in recs}

    start = check("AR5")
    try:
        for std, prev in (("AR6", "AR5"), ("AR4", "AR6")):
            _switch(app, std, prev)
            check(std)
    finally:
        _switch(app, "AR5", "AR4")
    end = check("AR5")
    assert all(end[k] == pytest.approx(v, rel=1e-12) for k, v in start.items())


def _s2(app, fid, **kw):
    from extensions import db
    from models import Scope2Emission

    with app.app_context():
        e = Scope2Emission(facility_id=fid, year=2013, month=kw.pop("month", 1), status="Verified", **kw)
        db.session.add(e)
        db.session.commit()
        return e.id


def _s2get(app, rid):
    from extensions import db
    from models import Scope2Emission

    with app.app_context():
        db.session.expire_all()
        e = db.session.get(Scope2Emission, rid)
        return {k: getattr(e, k) for k in ("co2e", "co2e_location_based", "co2e_market_based", "emission_factor")}


def test_scope2_branches(app, gworld):
    from electricity_factors import grid_entry, grid_factor_kg_co2e_per_kwh
    from routes.scope2 import _DEFAULT_BOILER_EF_KG_PER_MMBTU as NG

    grid = "Algerian National Grid"
    entry = grid_entry(grid)[1]
    loc = lambda std: 1e6 * grid_factor_kg_co2e_per_kwh(entry, gwp=AR[std]) / 1000.0
    fid = gworld["fid"]
    base = dict(source_type="electricity", electricity_kwh=1e6, grid_region=grid, co2e=loc("AR5"),
                co2e_location_based=loc("AR5"), emission_factor=loc("AR5") / 1000)
    ids = {
        "plain": _s2(app, fid, **base, co2e_market_based=loc("AR5")),
        "residual": _s2(app, fid, **base, market_instrument_type="Grid Average / Residual Mix", co2e_market_based=loc("AR5")),
        "none_text": _s2(app, fid, **base, market_instrument_type="None", co2e_market_based=loc("AR5")),
        "ppa": _s2(app, fid, **base, market_instrument_type="PPA", market_emission_factor=0.1, co2e_market_based=100.0),
        "rec_no_factor": _s2(app, fid, **base, market_instrument_type="REC", co2e_market_based=12.5),
        "supplier": _s2(app, fid, source_type="electricity", electricity_kwh=1e6, grid_region="Supplier X", co2e=300.0,
                        co2e_location_based=300.0, co2e_market_based=300.0, emission_factor=0.3),
        "no_kwh": _s2(app, fid, source_type="electricity", electricity_kwh=0, grid_region=grid, co2e=5.0,
                      co2e_location_based=5.0, co2e_market_based=5.0),
        "steam_other": _s2(app, fid, source_type="indirect_steam", heat_mmbtu=1000, co2e=93.0, emission_factor=74.0,
                           co2e_location_based=93.0, co2e_market_based=93.0),
        "cooling": _s2(app, fid, source_type="cooling", cooling_ton=1000, co2e=0.5, emission_factor=0.5),
        "chp": _s2(app, fid, source_type="cogen_allocation", heat_mmbtu=100, co2e=7.0),
        "steam_ng": _s2(app, fid, source_type="indirect_steam", heat_mmbtu=4000, emission_factor=NG,
                        co2e=5000 * (NG + 0.001 * 28 + 0.0001 * 265) / 1000, co2e_location_based=None, co2e_market_based=None),
    }
    before = {k: _s2get(app, v) for k, v in ids.items()}
    try:
        _switch(app, "AR6", "AR5")
        after = {k: _s2get(app, v) for k, v in ids.items()}
    finally:
        _switch(app, "AR5", "AR6")
    for k in ("plain", "residual", "none_text"):
        assert after[k]["co2e"] == pytest.approx(loc("AR6")) and after[k]["co2e_market_based"] == pytest.approx(loc("AR6")), k
        assert after[k]["emission_factor"] == pytest.approx(grid_factor_kg_co2e_per_kwh(entry, gwp=AR["AR6"]))
    assert after["ppa"]["co2e_market_based"] == pytest.approx(1e6 * 0.1 / 1000)       # the contract factor, not the grid
    assert after["ppa"]["co2e"] == pytest.approx(loc("AR6"))
    assert after["rec_no_factor"]["co2e_market_based"] == 12.5                          # nothing to recalculate it from
    for k in ("supplier", "no_kwh", "steam_other", "cooling", "chp"):
        assert after[k] == before[k], k                                                  # not GWP-weighted by the platform
    k6 = (NG + 0.001 * AR["AR6"]["CH4"] + 0.0001 * AR["AR6"]["N2O"]) / (NG + 0.001 * 28 + 0.0001 * 265)
    assert after["steam_ng"]["co2e"] == pytest.approx(before["steam_ng"]["co2e"] * k6)
    assert after["steam_ng"]["co2e_location_based"] is None and after["steam_ng"]["co2e_market_based"] is None
    back = {k: _s2get(app, v) for k, v in ids.items()}
    for k in ids:
        for f in ("co2e", "co2e_market_based"):
            if before[k][f] is not None:
                assert back[k][f] == pytest.approx(before[k][f], rel=1e-9), (k, f)


def test_steam_without_the_previous_standard_is_left_alone(app, gworld):
    from routes.scope2 import _DEFAULT_BOILER_EF_KG_PER_MMBTU as NG

    rid = _s2(app, gworld["fid"], month=6, source_type="indirect_steam", heat_mmbtu=10, emission_factor=NG, co2e=1.0)
    try:
        _switch(app, "AR6", None)
        assert _s2get(app, rid)["co2e"] == 1.0
    finally:
        _switch(app, "AR5", None)


def test_failed_commit_rolls_back_and_raises(app, gworld, monkeypatch):
    from extensions import db
    from models import ActivityLog, Emission

    with app.app_context():
        e = Emission(facility_id=gworld["fid"], year=2012, month=1, process_type="combustion", co2_emissions=1.0,
                     ch4_emissions=1.0, n2o_emissions=0.0, co2e_total=29.0, status="Verified", gwp_version="AR5")
        db.session.add(e)
        db.session.commit()
        eid = e.id
        logs = ActivityLog.query.filter_by(action="GWP_RECALCULATION").count()

        def boom():
            raise RuntimeError("disk full")

        monkeypatch.setattr(db.session, "commit", boom)
        from services.gwp_recalculation import recalculate_all_emissions_gwp

        with pytest.raises(RuntimeError, match="disk full"):
            recalculate_all_emissions_gwp("AR6", previous="AR5")
        monkeypatch.undo()
        db.session.expire_all()
        assert db.session.get(Emission, eid).co2e_total == 29.0
        assert ActivityLog.query.filter_by(action="GWP_RECALCULATION").count() == logs


def test_dashboard_cache_failure_does_not_undo_the_switch(app, gworld, monkeypatch):
    import routes.dashboard as dash

    from extensions import db
    from models import Emission

    def broken():
        raise RuntimeError("cache down")

    monkeypatch.setattr(dash, "clear_dashboard_cache", broken)
    with app.app_context():
        e = Emission(facility_id=gworld["fid"], year=2012, month=2, process_type="combustion", co2_emissions=1.0,
                     ch4_emissions=1.0, n2o_emissions=0.0, co2e_total=29.0, status="Verified", gwp_version="AR5")
        db.session.add(e)
        db.session.commit()
        eid = e.id
    try:
        _switch(app, "AR6", "AR5")
        with app.app_context():
            assert db.session.get(Emission, eid).co2e_total == pytest.approx(1.0 + AR["AR6"]["CH4"])
    finally:
        _switch(app, "AR5", "AR6")
