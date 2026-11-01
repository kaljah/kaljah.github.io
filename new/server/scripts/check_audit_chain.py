import sys
import os
import time

sys.path.insert(0, os.path.abspath('new/server'))

from app import app
from extensions import db
from models import ActivityLog
from services.audit_chain import verify_chain

with app.app_context():
    count = ActivityLog.query.count()
    print(f"Total ActivityLog count: {count}")
    
    t0 = time.time()
    query = ActivityLog.query.order_by(ActivityLog.id.asc()).yield_per(1000)
    total_records, head_hash, issues, issue_count = verify_chain(query)
    dt = time.time() - t0
    print(f"verify_chain finished in {dt:.3f}s: total={total_records}, head={head_hash[:12] if head_hash else 'None'}..., issues={issue_count}")
    if issues:
        print("First 3 issues:", issues[:3])
