import sys
import os
sys.path.insert(0, os.path.abspath('new/server'))

from app import app
from models import db, Emission, Facility, FlaringDetail
from services.dashboard_filters import source_category, gas_volume_m3

with app.app_context():
    em_flares = [e for e in Emission.query.filter(Emission.is_test == False).all() if source_category(e.process_type) == 'flaring']
    print(f"Total non-test flaring emissions: {len(em_flares)}")
    
    fac_em_vol = {}
    fac_em_t = {}
    for e in em_flares:
        vol = gas_volume_m3(e.quantity, e.unit, e.year, e.month) or 0.0
        fac_em_vol[e.facility_id] = fac_em_vol.get(e.facility_id, 0.0) + vol
        fac_em_t[e.facility_id] = fac_em_t.get(e.facility_id, 0.0) + float(e.co2e_total or 0.0)
    
    print("\nBottom-Up Emission records:")
    for fid, vol in sorted(fac_em_vol.items()):
        f = Facility.query.get(fid)
        fname = f.name if f else f"ID-{fid}"
        print(f"  Facility {fid} ({fname}): vol={vol:,.0f} m3, emissions={fac_em_t[fid]:,.2f} tCO2e, ratio={(fac_em_t[fid]*1000/vol if vol else 0):.3f} kg/m3")
    print(f"Total Bottom-Up Flaring: vol={sum(fac_em_vol.values()):,.0f} m3, emissions={sum(fac_em_t.values()):,.2f} tCO2e")

    fds = FlaringDetail.query.all()
    fac_fd_vol = {}
    for f in fds:
        vol = ((f.routine_knm3 or 0) + (f.non_routine_knm3 or 0) + (f.safety_knm3 or 0)) * 1000.0
        fac_fd_vol[f.facility_id] = fac_fd_vol.get(f.facility_id, 0.0) + vol

    print("\nFlaringDetail (Decree 21-330 Stream Volumes):")
    for fid, vol in sorted(fac_fd_vol.items()):
        f = Facility.query.get(fid)
        fname = f.name if f else f"ID-{fid}"
        print(f"  Facility {fid} ({fname}): reported stream vol={vol:,.0f} m3")
    print(f"Total FlaringDetail stream vol={sum(fac_fd_vol.values()):,.0f} m3 ({sum(fac_fd_vol.values())/1000:,.0f} kSm3)")
