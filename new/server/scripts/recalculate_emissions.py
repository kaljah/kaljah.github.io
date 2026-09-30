"""Recalculate stored Scope 1 records with the current factors and methods.

Formula and factor fixes apply to new data; stored records keep the values they were saved with.
This tool shows what the current engine gives for each stored record and, only with --apply,
writes the new values through the maker-checker: the record goes back to Pending, and the old
and new values are kept in the audit trail (action RECALCULATE).

It rebuilds each calculation from the stored inputs as an edit does (PUT /api/emissions/<id>),
and also removes the defaults the old bulk import added to every row (CH4 85 %, CO2 2 %).

    python scripts/recalculate_emissions.py                   # report only
    python scripts/recalculate_emissions.py --csv out.csv     # report to a file
    python scripts/recalculate_emissions.py --apply --user admin@example.com --ids 9,12
    python scripts/recalculate_emissions.py --apply --user admin@example.com --all

Use DATABASE_URL to point at another database. Records whose inputs cannot be recalculated
(e.g. drilling entered as a mud volume) are listed with the reason and never changed.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SEED_ADMIN", "false")

RESULT_FIELDS = ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total", "calc_method", "fuel_type",
                 "quantity", "unit", "factor_source", "uncertainty", "uncertainty_ch4", "uncertainty_n2o", "ef_key")
TIERS = ("default", "custom", "specific")


def stored_payload(record):
    """Inputs of the record as an edit rebuilds them, without the old bulk-import defaults."""
    from services.scope1_calc import canonicalize

    try:
        stored = json.loads(record.source_payload or "{}")
    except ValueError:
        stored = {}
    notes = []
    if stored.get("ch4_content") == 85.0 and stored.get("co2_content") == 2.0:
        # added to every row by the old bulk import, not entered by the user
        stored.pop("ch4_content")
        stored.pop("co2_content")
        notes.append("removed the bulk-import defaults CH4 85 % / CO2 2 %")
    tier = str(record.factor_source or "").lower()
    if tier not in TIERS:
        tier = str(stored.get("factor_source") or "default").lower()
        notes.append(f"tier column '{record.factor_source}' -> '{tier}'")
    base = {
        "process_type": record.process_type, "process": record.process_type, "fuel_type": record.fuel_type,
        "fuel": record.fuel_type, "unit": record.unit, "quantity": record.quantity, "amount": record.quantity,
        "factor_source": tier, "custom_factor_id": record.custom_factor_id or stored.get("custom_factor_id"),
    }
    ci = (stored.get("calc_inputs") or {}).get(record.process_type or "") or {}
    if isinstance(ci, dict) and ci.get("amount") not in (None, "") and ci.get("unit"):
        # the activity as the user entered it (the record may hold it converted, e.g. m3 -> scf)
        base.update(amount=ci["amount"], quantity=ci["amount"], unit=ci["unit"])
        stored = {**stored, "amount": ci["amount"], "quantity": ci["amount"], "unit": ci["unit"]}
    payload = canonicalize({**base, **{k: v for k, v in stored.items() if v is not None}})
    payload["factor_source"] = tier
    payload["year"], payload["month"], payload["facility_id"] = record.year, record.month, record.facility_id
    return payload, stored, notes


def recalculate(record, gwp_dict):
    from calculations import compute_emissions
    from calculations.anomaly import plausibility_check
    from models import Emission
    from services.scope1_calc import apply_result, resolve_factor, validate_activity

    payload, stored, notes = stored_payload(record)
    validate_activity(payload, require_unit=payload["factor_source"] in ("default", "custom"))
    factor_data = resolve_factor(payload, stored_payload=stored, allow_archived=True) or {}
    if factor_data.get("hhv") and not payload.get("hhv"):
        payload["hhv"] = factor_data["hhv"]
    em, method = compute_emissions(payload, factor_data, gwp_dict=gwp_dict)
    verdict, qa_msg = plausibility_check(em["totalCo2e"])
    if verdict == "reject":
        raise ValueError(qa_msg)
    scratch = Emission(factor_source=payload["factor_source"])
    apply_result(scratch, payload, em, method, factor_data, record.gwp_version or "AR5")
    return {f: getattr(scratch, f) for f in RESULT_FIELDS} | {"source_payload": scratch.source_payload}, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write the new values (records go back to Pending)")
    ap.add_argument("--user", help="email of the admin the change is recorded under (required with --apply)")
    ap.add_argument("--ids", help="comma-separated record ids to recalculate")
    ap.add_argument("--all", action="store_true", help="with --apply: every record that changes")
    ap.add_argument("--csv", help="write the report to this CSV file")
    ap.add_argument("--tolerance", type=float, default=1e-6, help="relative change reported (default 1e-6)")
    args = ap.parse_args(argv)
    if args.apply and not (args.user and (args.ids or args.all)):
        ap.error("--apply needs --user and --ids or --all")

    from app import app
    from calculations.constants import get_active_gwp
    from extensions import db
    from models import Emission, User
    from utils import log_activity_and_notify

    ids = {int(x) for x in args.ids.split(",")} if args.ids else None
    report = []
    with app.app_context():
        actor = None
        if args.apply:
            actor = User.query.filter(db.func.lower(User.email) == args.user.lower()).first()
            if actor is None or actor.role != "admin":
                ap.error(f"'{args.user}' is not an admin account")
        q = Emission.query.order_by(Emission.id)
        if ids:
            q = q.filter(Emission.id.in_(ids))
        for rec in q.all():
            gwp = get_active_gwp(standard=rec.gwp_version or "AR5")
            row = {"id": rec.id, "period": f"{rec.year}-{rec.month:02d}" if rec.year and rec.month else "",
                   "process": rec.process_type, "fuel": rec.fuel_type, "status": rec.status,
                   "old_co2e": rec.co2e_total, "new_co2e": None, "change_pct": None, "result": "", "notes": ""}
            try:
                new, notes = recalculate(rec, gwp)
            except Exception as err:  # the stored inputs are not enough for the current methods
                row["result"] = "cannot recalculate"
                row["notes"] = getattr(err, "message", None) or str(err)
                report.append(row)
                continue
            old = float(rec.co2e_total or 0)
            row["new_co2e"] = new["co2e_total"]
            row["change_pct"] = (new["co2e_total"] - old) / old * 100 if old else None
            changed = abs(new["co2e_total"] - old) > args.tolerance * max(abs(old), 1e-12) or any(
                n.startswith("tier column") for n in notes)
            row["result"] = "changes" if changed else "unchanged"
            row["notes"] = "; ".join(notes)
            if changed and args.apply:
                before = {f: getattr(rec, f) for f in RESULT_FIELDS}
                for f, v in new.items():
                    setattr(rec, f, v)
                rec.status, rec.approved_by, rec.approved_at = "Pending", None, None
                if hasattr(rec, "approved_by_name"):
                    rec.approved_by_name = None
                rec.updated_by = actor.id
                log_activity_and_notify(
                    action="RECALCULATE", record_id=str(rec.id), user=actor, entity="Emission", entity_id=rec.id,
                    facility_id=rec.facility_id, old_values=before, new_values={f: new[f] for f in RESULT_FIELDS},
                    details=f"Record {rec.id} recalculated with the current factors and methods ({row['notes'] or 'no input change'})",
                )
                row["result"] = "recalculated (Pending)"
            report.append(row)
        if args.apply:
            db.session.commit()

    cols = list(report[0].keys()) if report else []
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(report)
    for r in report:
        chg = f"{r['change_pct']:+.1f} %" if isinstance(r["change_pct"], float) else ""
        new = f"{r['new_co2e']:.4g}" if isinstance(r["new_co2e"], float) else "-"
        print(f"{r['id']:>6} {r['period']:<8} {str(r['process'])[:18]:<18} {str(r['fuel'])[:34]:<34} "
              f"{float(r['old_co2e'] or 0):>12.4g} -> {new:>10} {chg:>9}  {r['result']}  {r['notes']}")
    n = {k: sum(1 for r in report if r["result"].startswith(k)) for k in ("changes", "recalculated", "unchanged", "cannot")}
    print(f"\n{len(report)} records: {n['changes'] + n['recalculated']} change, {n['unchanged']} unchanged, "
          f"{n['cannot']} cannot be recalculated" + ("" if args.apply else " (report only; nothing written)"))


if __name__ == "__main__":
    main()
