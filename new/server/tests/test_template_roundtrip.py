"""The Scope 1 template's own example rows, re-dated and uploaded, are all accepted and no column that
holds a value is dropped on the way to the calculation (the stored source payload keeps it)."""
import csv
import io
import json
import logging

import pytest

from services import scope1_template as T
from tests.test_bulk_uploaders import emissions, env, reasons, upload  # noqa: F401

# template columns the importer renames or consumes when it builds the payload
RENAMED = {"date": {"year", "month"}, "facility": {"facility_id"}, "facility_name": {"facility_id"},
           "process": {"process_type"}, "process_type": {"process_type"}, "quantity": {"amount"},
           "fuel": {"fuel", "activity_key"}, "tier": {"factor_source"}, "factor_type": {"factor_source"},
           "equipment_id": {"equipment_id"}, "source_ref": {"data_source_ref"}}
# stored on the record itself rather than in the calculation payload
RECORD_FIELDS = {"equipment_id", "source_ref", "meter_id", "data_source_ref", "region", "group", "activity",
                 "division", "field", "notes"}


@pytest.mark.parametrize("tier", ["1", "2", "3", "auto"])
def test_template_examples_round_trip(app, client, env, tier):  # noqa: F811
    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    cols = T.columns_for(tier, (), True)
    keys = [c.key for c in cols]
    examples = T.example_rows(tier, (), fac)
    assert examples, "template has no examples"
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(keys)
    sent = []
    for i, ex in enumerate(examples):
        row = dict(ex, date="2025-01", equipment_id=f"TPL{i}")
        sent.append(row)
        w.writerow([row.get(k, "") for k in keys])
    st = upload(client, 1, buf.getvalue(), gft="auto")
    accepted = {e.equipment_id: e for e in emissions(app, fid, year=2025, month=1)}
    problems = [f"row {i}: {r}" for i, r in enumerate(reasons(st))]
    dropped = []
    for i, row in enumerate(sent):
        rec = accepted.get(f"TPL{i}")
        if rec is None:
            continue
        payload = json.loads(rec.source_payload or "{}")
        for k, v in row.items():
            if v in (None, "") or k in RECORD_FIELDS or k == "facility":
                continue
            if not (k in payload or RENAMED.get(k, set()) & set(payload)):
                dropped.append(f"{row.get('process')}/{row.get('tier')}: column '{k}' = {v!r} not in payload")
    print(f"\ntier {tier}: {len(accepted)}/{len(sent)} accepted, {len(problems)} skipped")
    assert not problems, "\n".join(problems[:20])
    assert not dropped, "\n".join(dropped[:20])


def test_xlsx_template_matches_csv_template(app, client, env):  # noqa: F811
    """The Excel template filled from its Examples sheet calculates exactly what the CSV does."""
    import openpyxl

    logging.disable(logging.CRITICAL)
    fid, fac = env["fid"], env["fac"]
    built = T.build_xlsx("auto", (), True, (fac,))
    wb = openpyxl.load_workbook(io.BytesIO(built if isinstance(built, bytes) else built.getvalue()))
    keys = [c.value for c in wb["Data Entry"][1] if c.value]
    ex = [[c.value for c in r][:len(keys)] for r in wb["Examples"].iter_rows(min_row=3) if r[0].value]
    assert ex
    ws = wb["Data Entry"]
    csv_buf = io.StringIO()
    w = csv.writer(csv_buf)
    w.writerow(keys)
    for i, row in enumerate(ex):
        row = list(row)
        row[keys.index("date")] = "2025-02"
        row[keys.index("equipment_id")] = f"X{i}"
        ws.append(row)
        w.writerow(row)
    out = io.BytesIO()
    wb.save(out)
    st = upload(client, 1, out.getvalue(), filename="t.xlsx", gft="auto")
    assert st["skipped_count"] == 0, reasons(st)
    xl = {e.equipment_id: e for e in emissions(app, fid, year=2025, month=2)}
    assert len(xl) == len(ex)
    csv_text = csv_buf.getvalue().replace("2025-02", "2025-03")
    st = upload(client, 1, csv_text)
    assert st["skipped_count"] == 0, reasons(st)
    cs = {e.equipment_id: e for e in emissions(app, fid, year=2025, month=3)}
    for k, a in xl.items():
        b = cs[k]
        for col in ("co2e_total", "co2_emissions", "ch4_emissions", "n2o_emissions", "quantity", "unit", "fuel_type"):
            assert getattr(a, col) == pytest.approx(getattr(b, col), rel=1e-12) if isinstance(getattr(a, col), float) \
                else getattr(a, col) == getattr(b, col), (k, col)
