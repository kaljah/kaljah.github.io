import sys
import os
sys.path.insert(0, os.path.abspath('new/server'))

from app import app
from models import Facility
from services.intensity import intensity_rows

with app.app_context():
    rows = intensity_rows(year=None)
    row_map = {r['facility_id']: r for r in rows}
    
    facs_with_coords = Facility.query.filter(Facility.latitude.isnot(None), Facility.longitude.isnot(None), Facility.is_test == False).all()
    facs_with_coords = [f for f in facs_with_coords if float(f.latitude or 0) != 0 and float(f.longitude or 0) != 0]
    
    print(f"Geolocated non-test facilities: {len(facs_with_coords)}")
    for f in facs_with_coords:
        r = row_map.get(f.id, {})
        ch4 = r.get('total_ch4', 0.0)
        co2e = r.get('total_co2e', 0.0)
        print(f"  Fac {f.id:2d}: {f.name:35s} ch4={ch4:,.1f} t, co2e={co2e:,.1f} t, super_ch4(>=2500)={ch4>=2500}, super_ch4(>=500)={ch4>=500}")
