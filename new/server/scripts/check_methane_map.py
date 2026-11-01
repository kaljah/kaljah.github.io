import sys
import os
sys.path.insert(0, os.path.abspath('new/server'))

from app import app
from models import db, Facility, Emission
from sqlalchemy import func

with app.app_context():
    facs = Facility.query.all()
    print(f"Total facilities count: {len(facs)}")
    
    total_db_ch4 = db.session.query(func.sum(Emission.ch4_emissions)).scalar() or 0.0
    nontest_db_ch4 = db.session.query(func.sum(Emission.ch4_emissions)).filter(Emission.is_test == False).scalar() or 0.0
    verified_db_ch4 = db.session.query(func.sum(Emission.ch4_emissions)).filter(Emission.status == 'Verified').scalar() or 0.0
    verified_nontest_ch4 = db.session.query(func.sum(Emission.ch4_emissions)).filter(Emission.status == 'Verified', Emission.is_test == False).scalar() or 0.0

    print(f"Total DB CH4 (all): {total_db_ch4:,.1f} t ({total_db_ch4/1000:,.1f} kt)")
    print(f"Total DB CH4 (non-test): {nontest_db_ch4:,.1f} t ({nontest_db_ch4/1000:,.1f} kt)")
    print(f"Verified CH4 (all): {verified_db_ch4:,.1f} t ({verified_db_ch4/1000:,.1f} kt)")
    print(f"Verified CH4 (non-test): {verified_nontest_ch4:,.1f} t ({verified_nontest_ch4/1000:,.1f} kt)")

    coords_ch4 = 0.0
    nocoords_ch4 = 0.0
    coords_verified_ch4 = 0.0
    coords_facs = []
    nocoords_facs = []

    for f in facs:
        ch4 = db.session.query(func.sum(Emission.ch4_emissions)).filter(Emission.facility_id == f.id).scalar() or 0.0
        v_ch4 = db.session.query(func.sum(Emission.ch4_emissions)).filter(Emission.facility_id == f.id, Emission.status == 'Verified', Emission.is_test == False).scalar() or 0.0
        lat = float(f.latitude) if f.latitude else 0
        lon = float(f.longitude) if f.longitude else 0
        has_coords = bool(lat != 0 and lon != 0)
        
        if has_coords and not f.is_test:
            coords_ch4 += ch4
            coords_verified_ch4 += v_ch4
            coords_facs.append((f.id, f.name, lat, lon, ch4, v_ch4))
        else:
            nocoords_ch4 += ch4
            nocoords_facs.append((f.id, f.name, lat, lon, f.is_test, ch4, v_ch4))

    print(f"\nFacilities WITH coordinates (non-test) count={len(coords_facs)}:")
    for item in coords_facs:
        print(f"  Fac {item[0]:2d}: {item[1]:35s} coords=({item[2]:.2f}, {item[3]:.2f}) all_ch4={item[4]:,.1f} t, verified_ch4={item[5]:,.1f} t")
    print(f"Sum CH4 with coordinates: all={coords_ch4:,.1f} t ({coords_ch4/1000:,.1f} kt), verified={coords_verified_ch4:,.1f} t ({coords_verified_ch4/1000:,.1f} kt)")

    print(f"\nFacilities WITHOUT coordinates or IS_TEST count={len(nocoords_facs)}:")
    for item in nocoords_facs:
        print(f"  Fac {item[0]:2d}: {item[1]:35s} is_test={item[4]} coords=({item[2]:.2f}, {item[3]:.2f}) all_ch4={item[5]:,.1f} t, verified_ch4={item[6]:,.1f} t")
