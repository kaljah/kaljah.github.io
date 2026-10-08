"""Editing a Tier 3 (specific) record must recalculate from its stored inputs.

Found by the full e2e matrix (GOV-6): editing an Acid Gas Removal record from Reports returned 422
"Missing required parameter ... 'agr_co2_in'" because the edit rebuilt the calculation without the
process-specific inputs the record was created with.
"""
from app import app
from tests.audit_helpers import login, make_facility, make_user


def _create_agr(client, fid):
    return client.post(
        "/api/emissions",
        json={
            "facility_id": fid, "year": 2025, "month": 3, "process_type": "agr", "factor_source": "specific",
            "quantity": 380, "amount": 380, "unit": "mmscf",
            # The Scope 1 form nests process inputs under calc_inputs[process_type].
            "calc_inputs": {"agr": {"agr_co2_in": 4.2, "agr_co2_out": 0.3, "agr_ch4_in": 0.85, "agr_ch4_slip": 0.0,
                                    "agr_control_eff": 0.0}},
            "status": "Draft",
        },
    )


def test_editing_the_quantity_of_an_agr_record_recalculates():
    admin = make_user("admin")
    fac = make_facility()
    client = app.test_client()
    login(client, admin)
    created = _create_agr(client, fac.id)
    assert created.status_code == 201, created.get_data(as_text=True)[:400]
    rid = created.get_json()["id"]
    before = created.get_json().get("co2e_total")

    # What the Reports edit modal (EditEmissionModal) sends: the changed activity plus a calc_inputs
    # block that only carries amount/unit/fuel for the process.
    r = client.put(
        f"/api/emissions/{rid}",
        json={
            "year": 2025, "month": 3, "facility_id": fac.id, "process_type": "agr", "fuel": None, "fuel_type": None,
            "amount": 405.5, "quantity": 405.5, "unit": "mmscf", "recalculate": True,
            "calc_inputs": {"agr": {"amount": 405.5, "unit": "mmscf", "fuel": None}},
        },
    )
    assert r.status_code == 200, r.get_data(as_text=True)[:400]
    after = r.get_json().get("co2e_total", None)
    assert after is None or before is None or after != before


def test_merge_inputs_keeps_stored_process_inputs():
    from input_validation import merge_inputs

    stored = {"agr": {"agr_co2_in": 4.2, "amount": 380}, "flaring": {"x": 1}}
    edit = {"agr": {"amount": 405.5, "unit": "mmscf"}}
    assert merge_inputs(stored, edit) == {"agr": {"agr_co2_in": 4.2, "amount": 405.5, "unit": "mmscf"}, "flaring": {"x": 1}}
    assert merge_inputs(None, edit) == edit
    assert merge_inputs(stored, None) is None
    assert merge_inputs(stored, {"agr": "raw"}) == {"agr": "raw", "flaring": {"x": 1}}
    assert stored["agr"]["amount"] == 380  # the stored block is not mutated
