import sys
import os
sys.path.insert(0, os.path.abspath('new/server'))

from app import app
from models import db, Facility, OgmpSurvey, Emission, FlaringDetail
from services.intensity import intensity_rows
from routes.dashboard_flaring import _build_flaring_data

with app.app_context():
    print("=== 1. FLARING COMPARISON ===")
    flare_data = _build_flaring_data(year="all", facility_id="all")
    print(f"Dashboard flaring volume: {flare_data.get('total_flared_volume_ksm3')} kSm3")
    print(f"Dashboard flaring emissions: {flare_data.get('total_emissions_t')} tCO2e")

    ci = intensity_rows(year=None)
    # Print flaring m3 in intensity
    print(f"Intensity corporate roll-up keys: {list(ci.get('corporate', {}).keys())}")
    print(f"Intensity corporate flaring_m3: {ci.get('corporate', {}).get('flaring_m3')}")
    print(f"Intensity corporate flaring_emissions_t: {ci.get('corporate', {}).get('flaring_emissions_t')}")
    for row in ci.get('rows', []):
        if row.get('flaring_m3'):
            print(f"  Facility {row.get('facility_name')}: flaring_m3={row.get('flaring_m3')}, flaring_emissions_t={row.get('flaring_emissions_t')}")

    # Reconciled FlaringDetail total
    flaring_details = FlaringDetail.query.all()
    fd_vol = sum(fd.flared_gas_volume_ksm3 or 0.0 for fd in flaring_details)
    print(f"FlaringDetail total flared_gas_volume_ksm3: {fd_vol} kSm3")

    em_flaring = Emission.query.filter(Emission.category == 'flaring', Emission.is_test == False).all()
    em_flare_vol = sum(e.gas_volume_m3 or 0.0 for e in em_flaring)
    em_flare_t = sum(e.co2e_total or 0.0 for e in em_flaring)
    print(f"Emission table flaring (non-test): count={len(em_flaring)}, vol_m3={em_flare_vol}, tCO2e={em_flare_t}")

    print("\n=== 2. METHANE COMPARISON (Map vs Dashboard) ===")
    total_ch4_all = db.session.query(db.func.sum(Emission.ch4_emissions)).scalar() or 0.0
    total_ch4_nontest = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(Emission.is_test == False).scalar() or 0.0
    print(f"Dashboard CH4 total (all): {total_ch4_all} tCH4 ({total_ch4_all/1000.0:.2f} kt)")
    print(f"Dashboard CH4 non-test: {total_ch4_nontest} tCH4 ({total_ch4_nontest/1000.0:.2f} kt)")

    facilities = Facility.query.filter(Facility.is_test == False).all()
    print("Facilities coordinates & CH4:")
    map_ch4_sum = 0.0
    for f in facilities:
        fac_ch4 = db.session.query(db.func.sum(Emission.ch4_emissions)).filter(Emission.facility_id == f.id, Emission.is_test == False).scalar() or 0.0
        has_coords = bool(f.latitude and f.longitude)
        print(f"  Facility {f.id} ({f.name}): coords=({f.latitude}, {f.longitude}) has_coords={has_coords}, CH4={fac_ch4:.1f} t ({fac_ch4/1000.0:.2f} kt)")
        if has_coords:
            map_ch4_sum += fac_ch4
    print(f"Sum of CH4 for facilities with coordinates: {map_ch4_sum:.1f} t ({map_ch4_sum/1000.0:.2f} kt)")
